#nullable enable
using System;
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
    /// Builder for split buttons.
    /// </summary>
    public class SplitButtonBuilder : ButtonBuilderBase
    {
        private readonly LinkButtonBuilder _linkButtonBuilder;
        private readonly SmartButtonScriptInitializer? _smartButtonScriptInitializer;

        /// <inheritdoc/>
        public override CommandComponentType[] SupportedTypes => new[]
        {
            CommandComponentType.SplitButton,
            CommandComponentType.SplitPushButton
        };

        /// <summary>
        /// Initializes a new instance of the <see cref="SplitButtonBuilder"/> class.
        /// </summary>
        /// <param name="logger">The logger instance.</param>
        /// <param name="buttonPostProcessor">The button post-processor.</param>
        /// <param name="linkButtonBuilder">The link button builder for child link buttons.</param>
        /// <param name="smartButtonScriptInitializer">Optional SmartButton script initializer.</param>
        public SplitButtonBuilder(
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
                Logger.Warning($"Cannot create split button '{component.DisplayName}': parent panel is null.");
                return;
            }

            // Check if split button already exists - if so, update it instead of creating new
            var existingSplitBtn = GetExistingSplitButton(parentPanel, component.DisplayName);
            if (existingSplitBtn != null)
            {
                Logger.Debug($"Split button '{component.DisplayName}' already exists - updating.");
                UpdateExistingSplitButton(existingSplitBtn, component, assemblyInfo);
                return;
            }

            try
            {
                // Use Title from bundle.yaml if available, with config script indicator if applicable
                var splitButtonText = ButtonPostProcessor.GetButtonText(component);
                var splitData = new SplitButtonData(component.DisplayName, splitButtonText);
                var splitBtn = parentPanel.AddItem(splitData) as SplitButton;

                if (splitBtn != null)
                {
                    // Apply post-processing to split button
                    ButtonPostProcessor.Process(splitBtn, component);

                    // Add children
                    AddChildrenToSplitButton(splitBtn, component, assemblyInfo);

                    Logger.Debug($"Created split button '{splitButtonText}' with {component.Children?.Count ?? 0} children.");
                }
            }
            catch (Exception ex)
            {
                Logger.Error($"Failed to create split button '{component.DisplayName}'. Exception: {ex.Message}");
            }
        }

        /// <summary>
        /// Gets an existing split button from the panel by name.
        /// </summary>
        private SplitButton? GetExistingSplitButton(RibbonPanel panel, string buttonName)
        {
            try
            {
                var items = panel.GetItems();
                foreach (var item in items)
                {
                    if (item.Name == buttonName && item is SplitButton sb)
                        return sb;
                }
            }
            catch (Exception ex)
            {
                Logger.Debug($"Error getting existing split button '{buttonName}': {ex.Message}");
            }
            return null;
        }

        /// <summary>
        /// Updates an existing split button with new configuration.
        /// </summary>
        private void UpdateExistingSplitButton(SplitButton splitBtn, ParsedComponent component, ExtensionAssemblyInfo assemblyInfo)
        {
            try
            {
                // Update display text
                var splitButtonText = ButtonPostProcessor.GetButtonText(component);
                splitBtn.ItemText = splitButtonText;

                // Re-apply post-processing (icon, tooltip, etc.)
                ButtonPostProcessor.Process(splitBtn, component);

                splitBtn.Enabled = true;
                splitBtn.Visible = true;

                // Update children
                AddChildrenToSplitButton(splitBtn, component, assemblyInfo);

                Logger.Debug($"Updated existing split button '{component.DisplayName}'.");
            }
            catch (Exception ex)
            {
                Logger.Error($"Failed to update split button '{component.DisplayName}': {ex.Message}");
            }
        }

        /// <summary>
        /// Adds child buttons to an existing split button.
        /// </summary>
        public void AddChildrenToSplitButton(SplitButton splitBtn, ParsedComponent component, ExtensionAssemblyInfo assemblyInfo)
        {
            if (splitBtn == null)
            {
                Logger.Warning($"Cannot add children to split button '{component.DisplayName}': splitBtn is null.");
                return;
            }

            // Set synchronization mode BEFORE adding children (required by Revit API for proper initialization)
            // SplitButton: IsSynchronizedWithCurrentItem = true (user's last click determines active button)
            // SplitPushButton: IsSynchronizedWithCurrentItem = false (first button always shows)
            try
            {
                bool shouldSync = component.Type == CommandComponentType.SplitButton;
                splitBtn.IsSynchronizedWithCurrentItem = shouldSync;
                Logger.Debug($"Set IsSynchronizedWithCurrentItem={shouldSync} for split button '{component.DisplayName}' before adding children.");
            }
            catch (Exception ex)
            {
                Logger.Debug($"Failed to set IsSynchronizedWithCurrentItem for split button '{component.DisplayName}'. Exception: {ex.Message}");
            }

            // Check if children already exist (reload scenario)
            var existingItems = GetExistingChildButtons(splitBtn);
            if (existingItems.Count > 0)
            {
                Logger.Debug($"Split button '{component.DisplayName}' already has {existingItems.Count} children - updating existing buttons.");
                UpdateExistingChildren(splitBtn, component, existingItems, assemblyInfo);
                return;
            }

            PushButton? firstButton = null;
            int childCount = 0;

            foreach (var sub in component.Children ?? Enumerable.Empty<ParsedComponent>())
            {
                if (sub.Type == CommandComponentType.Separator)
                {
                    // Skip adding separators during reload - they persist in the UI
                    if (assemblyInfo?.IsReloading == true)
                    {
                        Logger.Debug($"Skipping separator during reload for split button '{component.DisplayName}'.");
                        continue;
                    }
                    try
                    {
                        splitBtn.AddSeparator();
                    }
                    catch (Exception ex)
                    {
                        Logger.Debug($"Failed to add separator to split button. Exception: {ex.Message}");
                    }
                }
                else if (sub.Type == CommandComponentType.SmartButton)
                {
                    try
                    {
                        var pushButtonData = CreatePushButtonData(sub, assemblyInfo!);
                        var subBtn = splitBtn.AddPushButton(pushButtonData);
                        if (subBtn != null)
                        {
                            ButtonPostProcessor.Process(subBtn, sub, component);

                            // Execute __selfinit__ for SmartButton in split button
                            if (_smartButtonScriptInitializer != null)
                            {
                                var shouldActivate = _smartButtonScriptInitializer.ExecuteSelfInit(sub, subBtn);
                                if (!shouldActivate)
                                {
                                    subBtn.Enabled = false;
                                    Logger.Debug($"SmartButton '{sub.DisplayName}' in split button deactivated by __selfinit__.");
                                }
                            }

                            // Track first button to set as current
                            firstButton ??= subBtn;
                            childCount++;
                            Logger.Debug($"Added SmartButton '{sub.DisplayName}' to split button '{component.DisplayName}' (child #{childCount}).");
                        }
                        else
                        {
                            Logger.Warning($"AddPushButton returned null for SmartButton '{sub.DisplayName}' in split button '{component.DisplayName}'.");
                        }
                    }
                    catch (Exception ex)
                    {
                        Logger.Error($"Failed to add SmartButton '{sub.DisplayName}' to split button '{component.DisplayName}'. Exception: {ex.Message}");
                    }
                }
                else if (sub.Type == CommandComponentType.PushButton ||
                         sub.Type == CommandComponentType.UrlButton ||
                         sub.Type == CommandComponentType.InvokeButton ||
                         sub.Type == CommandComponentType.ContentButton)
                {
                    try
                    {
                        var pushButtonData = CreatePushButtonData(sub, assemblyInfo!);
                        var subBtn = splitBtn.AddPushButton(pushButtonData);
                        if (subBtn != null)
                        {
                            ButtonPostProcessor.Process(subBtn, sub, component);
                            // Track first button to set as current
                            firstButton ??= subBtn;
                            childCount++;
                            Logger.Debug($"Added child button '{sub.DisplayName}' to split button '{component.DisplayName}' (child #{childCount}).");
                        }
                        else
                        {
                            Logger.Warning($"AddPushButton returned null for child '{sub.DisplayName}' in split button '{component.DisplayName}'.");
                        }
                    }
                    catch (Exception ex)
                    {
                        Logger.Error($"Failed to add child button '{sub.DisplayName}' to split button '{component.DisplayName}'. Exception: {ex.Message}");
                    }
                }
                else if (sub.Type == CommandComponentType.LinkButton)
                {
                    try
                    {
                        var subLinkData = _linkButtonBuilder.CreateLinkButtonData(sub);
                        if (subLinkData != null)
                        {
                            var linkSubBtn = splitBtn.AddPushButton(subLinkData);
                            if (linkSubBtn != null)
                            {
                                ButtonPostProcessor.Process(linkSubBtn, sub, component);
                                // Track first button to set as current
                                firstButton ??= linkSubBtn;
                                childCount++;
                                Logger.Debug($"Added link button '{sub.DisplayName}' to split button '{component.DisplayName}' (child #{childCount}).");
                            }
                            else
                            {
                                Logger.Warning($"AddPushButton returned null for link button '{sub.DisplayName}' in split button '{component.DisplayName}'.");
                            }
                        }
                    }
                    catch (Exception ex)
                    {
                        Logger.Error($"Failed to add link button '{sub.DisplayName}' to split button '{component.DisplayName}'. Exception: {ex.Message}");
                    }
                }
            }
            
            Logger.Debug($"Split button '{component.DisplayName}' has {childCount} children added.");
            
            // Set the first child button as the current button to activate the split button
            // Without a current button set, the split button appears inactive/grayed out
            if (firstButton != null)
            {
                try
                {
                    splitBtn.CurrentButton = firstButton;
                    Logger.Debug($"Set current button for split button '{component.DisplayName}'.");
                }
                catch (Exception ex)
                {
                    Logger.Debug($"Failed to set current button for split button '{component.DisplayName}'. Exception: {ex.Message}");
                }
            }
        }

        /// <summary>
        /// Gets existing child buttons from a split button.
        /// </summary>
        private System.Collections.Generic.List<RibbonItem> GetExistingChildButtons(SplitButton splitBtn)
        {
            var result = new System.Collections.Generic.List<RibbonItem>();
            try
            {
                var items = splitBtn.GetItems();
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
                Logger.Debug($"Error getting existing children from split button: {ex.Message}");
            }
            return result;
        }

        /// <summary>
        /// Updates existing child buttons in a split button during reload.
        /// Matches Python's behavior where existing buttons are updated with new properties.
        /// </summary>
        private void UpdateExistingChildren(SplitButton splitBtn, ParsedComponent component, System.Collections.Generic.List<RibbonItem> existingItems, ExtensionAssemblyInfo assemblyInfo)
        {
            // Build a dictionary of existing items by name for quick lookup
            var existingByName = new System.Collections.Generic.Dictionary<string, PushButton>(StringComparer.OrdinalIgnoreCase);
            foreach (var item in existingItems)
            {
                if (item is PushButton pb && !string.IsNullOrEmpty(pb.Name))
                {
                    existingByName[pb.Name] = pb;
                    Logger.Debug($"Found existing child in split button: Name='{pb.Name}', ItemText='{pb.ItemText}'");
                }
            }

            Logger.Debug($"Updating {component.Children?.Count ?? 0} children in split button '{component.DisplayName}'. Found {existingByName.Count} existing buttons.");

            foreach (var sub in component.Children ?? Enumerable.Empty<ParsedComponent>())
            {
                if (sub.Type == CommandComponentType.Separator)
                    continue;

                Logger.Debug($"Looking for child '{sub.DisplayName}' in split button '{component.DisplayName}'...");

                // Try to find existing button by name
                if (existingByName.TryGetValue(sub.DisplayName, out var existingBtn))
                {
                    // Update existing button properties
                    try
                    {
                        if (sub.Type == CommandComponentType.LinkButton)
                        {
                            _linkButtonBuilder.UpdateExistingLinkButton(existingBtn, sub);
                            Logger.Debug($"Updated existing link button '{sub.DisplayName}' in split button '{component.DisplayName}'.");
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
                        ButtonPostProcessor.Process(existingBtn, sub, component);

                        // Ensure button is active
                        existingBtn.Enabled = true;
                        existingBtn.Visible = true;

                        Logger.Debug($"Updated existing child button '{sub.DisplayName}' in split button '{component.DisplayName}'. New text: '{buttonText}'");
                    }
                    catch (Exception ex)
                    {
                        Logger.Error($"Failed to update child button '{sub.DisplayName}' in split button: {ex.Message}");
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
