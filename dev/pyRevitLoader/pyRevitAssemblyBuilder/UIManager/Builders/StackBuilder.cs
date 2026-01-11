#nullable enable
using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitAssemblyBuilder.SessionManager;
using pyRevitAssemblyBuilder.UIManager.Buttons;
using pyRevitAssemblyBuilder.UIManager.Icons;
using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager.Builders
{
    /// <summary>
    /// Handles the creation of stacked button groups.
    /// </summary>
    public class StackBuilder : IStackBuilder
    {
        private readonly ILogger _logger;
        private readonly IButtonPostProcessor _buttonPostProcessor;
        private readonly Buttons.LinkButtonBuilder _linkButtonBuilder;
        private readonly Buttons.PulldownButtonBuilder _pulldownButtonBuilder;
        private readonly SmartButtonScriptInitializer? _smartButtonScriptInitializer;

        /// <summary>
        /// Initializes a new instance of the <see cref="StackBuilder"/> class.
        /// </summary>
        /// <param name="logger">The logger instance.</param>
        /// <param name="buttonPostProcessor">The button post-processor.</param>
        /// <param name="linkButtonBuilder">The link button builder.</param>
        /// <param name="pulldownButtonBuilder">The pulldown button builder.</param>
        /// <param name="smartButtonScriptInitializer">Optional SmartButton script initializer.</param>
        public StackBuilder(
            ILogger logger,
            IButtonPostProcessor buttonPostProcessor,
            Buttons.LinkButtonBuilder linkButtonBuilder,
            Buttons.PulldownButtonBuilder pulldownButtonBuilder,
            SmartButtonScriptInitializer? smartButtonScriptInitializer = null)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _buttonPostProcessor = buttonPostProcessor ?? throw new ArgumentNullException(nameof(buttonPostProcessor));
            _linkButtonBuilder = linkButtonBuilder ?? throw new ArgumentNullException(nameof(linkButtonBuilder));
            _pulldownButtonBuilder = pulldownButtonBuilder ?? throw new ArgumentNullException(nameof(pulldownButtonBuilder));
            _smartButtonScriptInitializer = smartButtonScriptInitializer;
        }

        /// <inheritdoc/>
        public void BuildStack(ParsedComponent component, RibbonPanel parentPanel, ExtensionAssemblyInfo assemblyInfo)
        {
            if (parentPanel == null)
            {
                _logger.Warning($"Cannot build stack '{component.DisplayName}': parent panel is null.");
                return;
            }

            var itemDataList = new List<RibbonItemData>();
            var originalItems = new List<ParsedComponent>();

            foreach (var child in component.Children ?? Enumerable.Empty<ParsedComponent>())
            {
                // Skip if this item already exists in the panel (e.g., during reload)
                // Check by DisplayName since that's what's used for the button's internal Name property
                if (ItemExistsInPanel(parentPanel, child.DisplayName))
                {
                    _logger.Debug($"Skipping stack item '{child.DisplayName}' - already exists in panel.");
                    return; // If any item exists, the whole stack was already added
                }

                if (child.Type == CommandComponentType.PushButton ||
                    child.Type == CommandComponentType.SmartButton ||
                    child.Type == CommandComponentType.UrlButton ||
                    child.Type == CommandComponentType.InvokeButton ||
                    child.Type == CommandComponentType.ContentButton)
                {
                    itemDataList.Add(CreatePushButtonData(child, assemblyInfo));
                    originalItems.Add(child);
                }
                else if (child.Type == CommandComponentType.LinkButton)
                {
                    var linkData = _linkButtonBuilder.CreateLinkButtonData(child);
                    if (linkData != null)
                    {
                        itemDataList.Add(linkData);
                        originalItems.Add(child);
                    }
                }
                else if (child.Type == CommandComponentType.PullDown)
                {
                    // Use localized title which handles fallback to DisplayName
                    var pulldownText = ExtensionParser.GetComponentTitle(child);
                    // Use DisplayName for the button's internal name to match control ID format
                    var pdData = new PulldownButtonData(child.DisplayName, pulldownText);
                    itemDataList.Add(pdData);
                    originalItems.Add(child);
                }
            }

            if (itemDataList.Count >= 2)
            {
                IList<RibbonItem>? stackedItems = null;
                if (itemDataList.Count == 2)
                    stackedItems = parentPanel.AddStackedItems(itemDataList[0], itemDataList[1]);
                else
                    stackedItems = parentPanel.AddStackedItems(itemDataList[0], itemDataList[1], itemDataList[2]);

                if (stackedItems != null)
                {
                    ProcessStackedItems(stackedItems, originalItems, assemblyInfo);
                }
            }
            else
            {
                _logger.Debug($"Stack '{component.DisplayName}' has fewer than 2 items, skipping.");
            }
        }

        /// <summary>
        /// Processes stacked items after they are added to the panel.
        /// </summary>
        private void ProcessStackedItems(IList<RibbonItem> stackedItems, List<ParsedComponent> originalItems, ExtensionAssemblyInfo assemblyInfo)
        {
            for (int i = 0; i < stackedItems.Count; i++)
            {
                var ribbonItem = stackedItems[i];
                var origComponent = originalItems[i];

                // Apply post-processing to push buttons in stack
                if (ribbonItem is PushButton pushBtn)
                {
                    _buttonPostProcessor.Process(pushBtn, origComponent);

                    // Execute __selfinit__ for SmartButtons in stack
                    if (origComponent.Type == CommandComponentType.SmartButton && _smartButtonScriptInitializer != null)
                    {
                        var shouldActivate = _smartButtonScriptInitializer.ExecuteSelfInit(origComponent, pushBtn);
                        if (!shouldActivate)
                        {
                            pushBtn.Enabled = false;
                            _logger.Debug($"SmartButton '{origComponent.DisplayName}' in stack deactivated by __selfinit__.");
                        }
                    }
                }

                if (ribbonItem is PulldownButton pdBtn)
                {
                    // Apply post-processing to the pulldown button itself in stack
                    _buttonPostProcessor.Process(pdBtn, origComponent);

                    // Add children to pulldown
                    _pulldownButtonBuilder.AddChildrenToPulldown(pdBtn, origComponent, assemblyInfo);
                }
            }
        }

        /// <summary>
        /// Creates a PushButtonData for a standard push button.
        /// </summary>
        private PushButtonData CreatePushButtonData(ParsedComponent component, ExtensionAssemblyInfo assemblyInfo)
        {
            // Use Title from bundle.yaml if available, otherwise fall back to DisplayName
            var buttonText = _buttonPostProcessor.GetButtonText(component);

            // Ensure the class name matches what the CommandTypeGenerator creates
            var className = SanitizeClassName(component.UniqueId);

            var pushButtonData = new PushButtonData(
                component.DisplayName,
                buttonText,
                assemblyInfo.Location,
                className);

            // Set availability class if context is defined
            if (!string.IsNullOrEmpty(component.Context))
            {
                var availabilityClassName = className + "_avail";
                pushButtonData.AvailabilityClassName = availabilityClassName;
            }

            return pushButtonData;
        }

        /// <summary>
        /// Sanitizes a class name to match the CommandTypeGenerator logic.
        /// </summary>
        private static string SanitizeClassName(string name)
        {
            var sb = new System.Text.StringBuilder();
            foreach (char c in name)
                sb.Append(char.IsLetterOrDigit(c) ? c : '_');
            return sb.ToString();
        }

        /// <summary>
        /// Checks if a ribbon item with the specified name already exists in the panel.
        /// </summary>
        private bool ItemExistsInPanel(RibbonPanel? panel, string itemName)
        {
            if (panel == null || string.IsNullOrEmpty(itemName))
                return false;

            try
            {
                var existingItems = panel.GetItems();
                return existingItems.Any(item => item.Name == itemName);
            }
            catch (Exception ex)
            {
                _logger.Debug($"Error checking if item '{itemName}' exists in panel. Exception: {ex.Message}");
                return false;
            }
        }
    }
}
