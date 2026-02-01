#nullable enable
using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitAssemblyBuilder.SessionManager;
using pyRevitAssemblyBuilder.UIManager.Icons;
using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager.Buttons
{
    /// <summary>
    /// Builder for pulldown buttons.
    /// </summary>
    public class PulldownButtonBuilder : ButtonBuilderBase
    {
        private readonly SmartButtonScriptInitializer? _smartButtonScriptInitializer;
        private readonly LinkButtonBuilder _linkButtonBuilder;

        /// <inheritdoc/>
        public override CommandComponentType[] SupportedTypes => new[]
        {
            CommandComponentType.PullDown
        };

        /// <summary>
        /// Initializes a new instance of the <see cref="PulldownButtonBuilder"/> class.
        /// </summary>
        /// <param name="logger">The logger instance.</param>
        /// <param name="buttonPostProcessor">The button post-processor.</param>
        /// <param name="linkButtonBuilder">The link button builder for child link buttons.</param>
        /// <param name="smartButtonScriptInitializer">Optional SmartButton script initializer.</param>
        public PulldownButtonBuilder(
            ILogger logger,
            IButtonPostProcessor buttonPostProcessor,
            LinkButtonBuilder linkButtonBuilder,
            SmartButtonScriptInitializer? smartButtonScriptInitializer = null)
            : base(logger, buttonPostProcessor)
        {
            _linkButtonBuilder = linkButtonBuilder ?? throw new ArgumentNullException(nameof(linkButtonBuilder));
            _smartButtonScriptInitializer = smartButtonScriptInitializer;
        }

        /// <inheritdoc/>
        public override void Build(ParsedComponent component, RibbonPanel parentPanel, string tabName, ExtensionAssemblyInfo assemblyInfo)
        {
            if (parentPanel == null)
            {
                Logger.Warning($"Cannot create pulldown button '{component.DisplayName}': parent panel is null.");
                return;
            }

            // Check if pulldown button already exists - if so, update it instead of creating new
            var existingPdBtn = GetExistingPulldownButton(parentPanel, component.DisplayName);
            if (existingPdBtn != null)
            {
                Logger.Debug($"Pulldown button '{component.DisplayName}' already exists - updating.");
                UpdateExistingPulldownButton(existingPdBtn, component, assemblyInfo);
                return;
            }

            CreatePulldown(component, parentPanel, tabName, assemblyInfo, addToPanel: true);
        }

        /// <summary>
        /// Gets an existing pulldown button from the panel by name.
        /// </summary>
        private PulldownButton? GetExistingPulldownButton(RibbonPanel panel, string buttonName)
        {
            try
            {
                var items = panel.GetItems();
                foreach (var item in items)
                {
                    if (item.Name == buttonName && item is PulldownButton pb)
                        return pb;
                }
            }
            catch (Exception ex)
            {
                Logger.Debug($"Error getting existing pulldown button '{buttonName}': {ex.Message}");
            }
            return null;
        }

        /// <summary>
        /// Updates an existing pulldown button with new configuration.
        /// </summary>
        private void UpdateExistingPulldownButton(PulldownButton pdBtn, ParsedComponent component, ExtensionAssemblyInfo assemblyInfo)
        {
            try
            {
                // Update display text
                var pulldownText = ExtensionParser.GetComponentTitle(component);
                pdBtn.ItemText = pulldownText;

                // Re-apply post-processing (icon, tooltip, etc.)
                ButtonPostProcessor.Process(pdBtn, component);

                pdBtn.Enabled = true;
                pdBtn.Visible = true;

                // Update children
                AddChildrenToPulldown(pdBtn, component, assemblyInfo);

                Logger.Debug($"Updated existing pulldown button '{component.DisplayName}'.");
            }
            catch (Exception ex)
            {
                Logger.Error($"Failed to update pulldown button '{component.DisplayName}': {ex.Message}");
            }
        }

        /// <summary>
        /// Creates a pulldown button and optionally adds it to a panel.
        /// </summary>
        /// <returns>The PulldownButtonData for use in stacks, or null if failed.</returns>
        public PulldownButtonData? CreatePulldown(
            ParsedComponent component,
            RibbonPanel parentPanel,
            string tabName,
            ExtensionAssemblyInfo assemblyInfo,
            bool addToPanel)
        {
            // Use localized title which handles fallback to DisplayName
            var pulldownText = ExtensionParser.GetComponentTitle(component);
            // Use DisplayName for the button's internal name to match control ID format
            var pdData = new PulldownButtonData(component.DisplayName, pulldownText);

            if (!addToPanel)
                return pdData;

            var pdBtn = parentPanel.AddItem(pdData) as PulldownButton;
            if (pdBtn == null)
            {
                Logger.Warning($"Failed to add pulldown button '{pulldownText}' to panel.");
                return null;
            }

            // Apply post-processing to the pulldown button itself
            ButtonPostProcessor.Process(pdBtn, component);

            // Add children
            AddChildrenToPulldown(pdBtn, component, assemblyInfo);

            Logger.Debug($"Created pulldown button '{pulldownText}' with {component.Children?.Count ?? 0} children.");
            return pdData;
        }

        /// <summary>
        /// Adds child buttons to an existing pulldown button.
        /// </summary>
        public void AddChildrenToPulldown(PulldownButton pdBtn, ParsedComponent component, ExtensionAssemblyInfo assemblyInfo)
        {
            // Check if children already exist (reload scenario)
            var existingItems = GetExistingChildButtons(pdBtn);
            if (existingItems.Count > 0)
            {
                Logger.Debug($"Pulldown button '{component.DisplayName}' already has {existingItems.Count} children - updating existing buttons.");
                UpdateExistingChildren(pdBtn, component, existingItems, assemblyInfo);
                return;
            }

            foreach (var sub in component.Children ?? Enumerable.Empty<ParsedComponent>())
            {
                if (sub.Type == CommandComponentType.Separator)
                {
                    // Skip adding separators during reload - they persist in the UI
                    if (assemblyInfo?.IsReloading == true)
                    {
                        Logger.Debug($"Skipping separator during reload for pulldown button '{component.DisplayName}'.");
                        continue;
                    }
                    try
                    {
                        pdBtn.AddSeparator();
                    }
                    catch (Exception ex)
                    {
                        Logger.Debug($"Failed to add separator to pulldown button. Exception: {ex.Message}");
                    }
                }
                else if (sub.Type == CommandComponentType.PushButton ||
                         sub.Type == CommandComponentType.UrlButton ||
                         sub.Type == CommandComponentType.InvokeButton ||
                         sub.Type == CommandComponentType.ContentButton)
                {
                    var subBtn = pdBtn.AddPushButton(CreatePushButtonData(sub, assemblyInfo!));
                    if (subBtn != null)
                    {
                        ButtonPostProcessor.Process(subBtn, sub, component, IconMode.SmallToBoth);
                    }
                }
                else if (sub.Type == CommandComponentType.SmartButton)
                {
                    var smartSubBtn = pdBtn.AddPushButton(CreatePushButtonData(sub, assemblyInfo!));
                    if (smartSubBtn != null)
                    {
                        ButtonPostProcessor.Process(smartSubBtn, sub, component, IconMode.SmallToBoth);

                        // Execute __selfinit__ for SmartButton in pulldown
                        if (_smartButtonScriptInitializer != null)
                        {
                            var shouldActivate = _smartButtonScriptInitializer.ExecuteSelfInit(sub, smartSubBtn);
                            if (!shouldActivate)
                            {
                                smartSubBtn.Enabled = false;
                                Logger.Debug($"SmartButton '{sub.DisplayName}' in pulldown deactivated by __selfinit__.");
                            }
                        }
                    }
                }
                else if (sub.Type == CommandComponentType.LinkButton)
                {
                    var linkData = _linkButtonBuilder.CreateLinkButtonData(sub);
                    if (linkData != null)
                    {
                        var linkSubBtn = pdBtn.AddPushButton(linkData);
                        if (linkSubBtn != null)
                        {
                            ButtonPostProcessor.Process(linkSubBtn, sub, component, IconMode.SmallToBoth);
                        }
                    }
                }
            }
        }

        /// <summary>
        /// Gets existing child buttons from a pulldown button.
        /// </summary>
        private List<RibbonItem> GetExistingChildButtons(PulldownButton pdBtn)
        {
            var result = new List<RibbonItem>();
            try
            {
                var items = pdBtn.GetItems();
                if (items != null)
                {
                    foreach (var item in items)
                    {
                        if (item != null)
                            result.Add(item);
                    }
                }
            }
            catch (Exception ex)
            {
                Logger.Debug($"Error getting existing children from pulldown button: {ex.Message}");
            }
            return result;
        }

        /// <summary>
        /// Updates existing child buttons in a pulldown button during reload.
        /// </summary>
        private void UpdateExistingChildren(PulldownButton pdBtn, ParsedComponent component, List<RibbonItem> existingItems, ExtensionAssemblyInfo assemblyInfo)
        {
            // Build a dictionary of existing items by name for quick lookup
            var existingByName = new Dictionary<string, PushButton>(StringComparer.OrdinalIgnoreCase);
            foreach (var item in existingItems)
            {
                if (item is PushButton pb && !string.IsNullOrEmpty(pb.Name))
                {
                    existingByName[pb.Name] = pb;
                    Logger.Debug($"Found existing child in pulldown: Name='{pb.Name}', ItemText='{pb.ItemText}'");
                }
            }

            Logger.Debug($"Updating {component.Children?.Count ?? 0} children in pulldown '{component.DisplayName}'. Found {existingByName.Count} existing buttons.");

            foreach (var sub in component.Children ?? Enumerable.Empty<ParsedComponent>())
            {
                if (sub.Type == CommandComponentType.Separator)
                    continue;

                Logger.Debug($"Looking for child '{sub.DisplayName}' in pulldown '{component.DisplayName}'...");

                // Try to find existing button by name
                if (existingByName.TryGetValue(sub.DisplayName, out var existingBtn))
                {
                    // Update existing button properties
                    try
                    {
                        if (sub.Type == CommandComponentType.LinkButton)
                        {
                            _linkButtonBuilder.UpdateExistingLinkButton(existingBtn, sub);
                            Logger.Debug($"Updated existing link button '{sub.DisplayName}' in pulldown '{component.DisplayName}'.");
                            continue;
                        }
                        else
                        {
                            UpdatePushButtonCommandBinding(existingBtn, sub, assemblyInfo);
                        }

                        // Update display text
                        var buttonText = ButtonPostProcessor.GetButtonText(sub);
                        existingBtn.ItemText = buttonText;

                        // Re-apply all post-processing (icon, tooltip, highlight)
                        // This ensures changes to bundle.yaml are reflected
                        ButtonPostProcessor.Process(existingBtn, sub, component, IconMode.SmallToBoth);

                        // Ensure button is active
                        existingBtn.Enabled = true;
                        existingBtn.Visible = true;

                        Logger.Debug($"Updated existing child button '{sub.DisplayName}' in pulldown '{component.DisplayName}'. New text: '{buttonText}'");
                    }
                    catch (Exception ex)
                    {
                        Logger.Error($"Failed to update child button '{sub.DisplayName}' in pulldown: {ex.Message}");
                    }
                }
                else
                {
                    Logger.Debug($"Child '{sub.DisplayName}' not found in existing buttons. Available: [{string.Join(", ", existingByName.Keys)}]");
                }
            }
        }
    }
}
