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
        private readonly Buttons.SplitButtonBuilder _splitButtonBuilder;
        private readonly SmartButtonScriptInitializer? _smartButtonScriptInitializer;

        /// <summary>
        /// Initializes a new instance of the <see cref="StackBuilder"/> class.
        /// </summary>
        /// <param name="logger">The logger instance.</param>
        /// <param name="buttonPostProcessor">The button post-processor.</param>
        /// <param name="linkButtonBuilder">The link button builder.</param>
        /// <param name="pulldownButtonBuilder">The pulldown button builder.</param>
        /// <param name="splitButtonBuilder">The split button builder.</param>
        /// <param name="smartButtonScriptInitializer">Optional SmartButton script initializer.</param>
        public StackBuilder(
            ILogger logger,
            IButtonPostProcessor buttonPostProcessor,
            Buttons.LinkButtonBuilder linkButtonBuilder,
            Buttons.PulldownButtonBuilder pulldownButtonBuilder,
            Buttons.SplitButtonBuilder splitButtonBuilder,
            SmartButtonScriptInitializer? smartButtonScriptInitializer = null)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _buttonPostProcessor = buttonPostProcessor ?? throw new ArgumentNullException(nameof(buttonPostProcessor));
            _linkButtonBuilder = linkButtonBuilder ?? throw new ArgumentNullException(nameof(linkButtonBuilder));
            _pulldownButtonBuilder = pulldownButtonBuilder ?? throw new ArgumentNullException(nameof(pulldownButtonBuilder));
            _splitButtonBuilder = splitButtonBuilder ?? throw new ArgumentNullException(nameof(splitButtonBuilder));
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

            var children = (component.Children ?? Enumerable.Empty<ParsedComponent>()).ToList();
            if (children.Count < 2)
            {
                _logger.Debug($"Stack '{component.DisplayName}' has fewer than 2 items, skipping.");
                return;
            }

            // Check if the stack already exists by looking for the first child's DisplayName
            // This matches Python's behavior where button name = folder basename
            var firstChildDisplayName = children[0].DisplayName;
            var existingItems = TryGetExistingStackItems(parentPanel, firstChildDisplayName, children.Count);

            if (existingItems != null && existingItems.Count > 0)
            {
                // Stack already exists - update the existing items instead of creating new ones
                // This handles the reload case where the stack was already created
                _logger.Debug($"Stack '{component.DisplayName}' already exists. Updating {existingItems.Count} existing items.");
                UpdateExistingStackItems(existingItems, children, assemblyInfo);
                return;
            }

            // Create new stack items
            var itemDataList = new List<RibbonItemData>();
            var originalItems = new List<ParsedComponent>();

            foreach (var child in children)
            {
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
                else if (child.Type == CommandComponentType.SplitButton ||
                         child.Type == CommandComponentType.SplitPushButton)
                {
                    // Use localized title which handles fallback to DisplayName
                    var splitButtonText = ExtensionParser.GetComponentTitle(child);
                    // Use DisplayName for the button's internal name to match control ID format
                    var splitData = new SplitButtonData(child.DisplayName, splitButtonText);
                    itemDataList.Add(splitData);
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
                _logger.Debug($"Stack '{component.DisplayName}' has fewer than 2 items after filtering, skipping.");
            }
        }

        /// <summary>
        /// Tries to find existing stack items in the panel by looking for buttons with matching DisplayName.
        /// </summary>
        private List<RibbonItem>? TryGetExistingStackItems(RibbonPanel panel, string firstItemDisplayName, int expectedCount)
        {
            try
            {
                var existingItems = panel.GetItems();

                // Look for a button with the DisplayName of the first child
                // This indicates the stack was already created in this session
                var matchingItem = existingItems.FirstOrDefault(item => item.Name == firstItemDisplayName);

                if (matchingItem == null)
                    return null;

                // Found the first item - now find adjacent items that form the stack
                // Stack items are added together and should be adjacent in the panel
                var itemIndex = existingItems.IndexOf(matchingItem);
                var stackItems = new List<RibbonItem>();

                // Collect items that appear to be part of this stack
                // We look for items added right after the first one
                for (int i = itemIndex; i < Math.Min(itemIndex + expectedCount, existingItems.Count); i++)
                {
                    stackItems.Add(existingItems[i]);
                }

                return stackItems.Count >= 2 ? stackItems : null;
            }
            catch (Exception ex)
            {
                _logger.Debug($"Error finding existing stack items: {ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// Updates existing stack items with new configuration (title, icon, tooltip, etc.)
        /// This is called when a stack already exists and we need to update it during reload.
        /// </summary>
        private void UpdateExistingStackItems(List<RibbonItem> existingItems, List<ParsedComponent> children, ExtensionAssemblyInfo assemblyInfo)
        {
            var minCount = Math.Min(existingItems.Count, children.Count);

            for (int i = 0; i < minCount; i++)
            {
                var ribbonItem = existingItems[i];
                var childComponent = children[i];

                try
                {
                    // Update the display text (ItemText) in case Title changed
                    var newTitle = ExtensionParser.GetComponentTitle(childComponent);
                    ribbonItem.ItemText = newTitle;

                    // Update visibility and enabled state
                    ribbonItem.Visible = true;
                    ribbonItem.Enabled = true;

                    // Apply post-processing (icon, tooltip, etc.)
                    if (ribbonItem is PushButton pushBtn)
                    {
                        if (childComponent.Type == CommandComponentType.LinkButton)
                        {
                            _linkButtonBuilder.UpdateExistingLinkButton(pushBtn, childComponent);
                        }
                        else
                        {
                            UpdatePushButtonCommandBinding(pushBtn, childComponent, assemblyInfo);
                        }

                        _buttonPostProcessor.Process(pushBtn, childComponent);

                        // Execute __selfinit__ for SmartButtons
                        if (childComponent.Type == CommandComponentType.SmartButton && _smartButtonScriptInitializer != null)
                        {
                            var shouldActivate = _smartButtonScriptInitializer.ExecuteSelfInit(childComponent, pushBtn);
                            if (!shouldActivate)
                            {
                                pushBtn.Enabled = false;
                                _logger.Debug($"SmartButton '{childComponent.DisplayName}' in stack deactivated by __selfinit__.");
                            }
                        }
                    }
                    else if (ribbonItem is PulldownButton pdBtn)
                    {
                        _buttonPostProcessor.Process(pdBtn, childComponent);
                        _pulldownButtonBuilder.AddChildrenToPulldown(pdBtn, childComponent, assemblyInfo);
                    }
                    else if (ribbonItem is SplitButton splitBtn)
                    {
                        _buttonPostProcessor.Process(splitBtn, childComponent);
                        _splitButtonBuilder.AddChildrenToSplitButton(splitBtn, childComponent, assemblyInfo);
                    }

                    _logger.Debug($"Updated existing stack item '{childComponent.DisplayName}' (index {i}).");
                }
                catch (Exception ex)
                {
                    _logger.Error($"Error updating stack item '{childComponent.DisplayName}': {ex.Message}");
                }
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

                if (ribbonItem is SplitButton splitBtn)
                {
                    try
                    {
                        // Apply post-processing to the split button itself in stack
                        _buttonPostProcessor.Process(splitBtn, origComponent);

                        // Add children to split button
                        _splitButtonBuilder.AddChildrenToSplitButton(splitBtn, origComponent, assemblyInfo);
                        
                        _logger.Debug($"Successfully processed split button '{origComponent.DisplayName}' in stack (index {i}).");
                    }
                    catch (Exception ex)
                    {
                        _logger.Error($"Failed to process split button '{origComponent.DisplayName}' in stack (index {i}). Exception: {ex.Message}");
                    }
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
        /// Updates command binding for an existing push button in a stack.
        /// </summary>
        private void UpdatePushButtonCommandBinding(PushButton? button, ParsedComponent component, ExtensionAssemblyInfo assemblyInfo)
        {
            if (button == null || component == null || assemblyInfo == null)
                return;

            try
            {
                var className = SanitizeClassName(component.UniqueId);
                button.AssemblyName = assemblyInfo.Location;
                button.ClassName = className;

                if (!string.IsNullOrEmpty(component.Context))
                {
                    button.AvailabilityClassName = className + "_avail";
                }
            }
            catch (Exception ex)
            {
                _logger.Debug($"Failed to update command binding for '{component.DisplayName}'. Exception: {ex.Message}");
            }
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
