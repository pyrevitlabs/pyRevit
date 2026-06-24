#nullable enable
using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitAssemblyBuilder.SessionManager;
using pyRevitAssemblyBuilder.UIManager;
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
        private readonly BuildContext _buildContext;
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
        /// <param name="buildContext">Shared build context that carries the current per-build settings.</param>
        /// <param name="logger">The logger instance.</param>
        /// <param name="buttonPostProcessor">The button post-processor.</param>
        /// <param name="linkButtonBuilder">The link button builder for child link buttons.</param>
        /// <param name="smartButtonScriptInitializer">Optional SmartButton script initializer.</param>
        public PulldownButtonBuilder(
            BuildContext buildContext,
            ILogger logger,
            IButtonPostProcessor buttonPostProcessor,
            LinkButtonBuilder linkButtonBuilder,
            SmartButtonScriptInitializer? smartButtonScriptInitializer = null)
            : base(logger, buttonPostProcessor)
        {
            _buildContext = buildContext ?? throw new ArgumentNullException(nameof(buildContext));
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

            var existingPdBtn = GetExistingPulldownButton(parentPanel, component.DisplayName);
            if (!TryGetVisibleChildren(component, existingPdBtn, out var visibleChildren))
                return;

            if (existingPdBtn != null)
            {
                Logger.Debug($"Pulldown button '{component.DisplayName}' already exists - updating.");
                UpdateExistingPulldownButton(existingPdBtn, component, visibleChildren, assemblyInfo);
                return;
            }

            CreatePulldown(component, parentPanel, tabName, assemblyInfo, visibleChildren, addToPanel: true);
        }

        /// <summary>
        /// Filters <paramref name="component"/>'s children using the current <see cref="BuildContext"/>.
        /// When the result is empty, deactivates <paramref name="existingRibbonItem"/> (if any) and
        /// returns false so the caller can short-circuit.
        /// </summary>
        private bool TryGetVisibleChildren(
            ParsedComponent component,
            RibbonItem? existingRibbonItem,
            out IReadOnlyList<ParsedComponent> visibleChildren)
        {
            var settings = _buildContext.CurrentSettings;
            visibleChildren = ComponentSupportUtils.GetVisibleButtonGroupChildren(
                component.Children,
                settings.CurrentVersion,
                settings.LoadBeta,
                Logger);

            if (visibleChildren.Count == 0)
            {
                Logger.Debug($"Pulldown button '{component.DisplayName}' has no visible children after filtering. Hiding it.");
                DeactivateRibbonItem(existingRibbonItem, component.DisplayName);
                return false;
            }

            return true;
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
        private void UpdateExistingPulldownButton(
            PulldownButton pdBtn,
            ParsedComponent component,
            IReadOnlyList<ParsedComponent> visibleChildren,
            ExtensionAssemblyInfo assemblyInfo)
        {
            try
            {
                // Update display text
                var pulldownText = ExtensionParser.GetComponentTitle(component);
                pdBtn.ItemText = pulldownText;

                // Re-apply post-processing (icon, tooltip, etc.)
                ButtonPostProcessor.Process(
                    pdBtn,
                    component,
                    null,
                    IconMode.LargeAndSmall);

                pdBtn.Enabled = true;
                pdBtn.Visible = true;

                // Update children
                AddChildrenToPulldown(pdBtn, component, assemblyInfo, visibleChildren);

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
            IReadOnlyList<ParsedComponent> visibleChildren,
            bool addToPanel)
        {
            // Use localized title which handles fallback to DisplayName
            var pulldownText = ExtensionParser.GetComponentTitle(component);
            // Use DisplayName for the button's internal name to match control ID format
            var pdData = new PulldownButtonData(component.DisplayName, pulldownText);

            if (!addToPanel)
                return pdData;

            var pdBtn = TimedAddItem(() => parentPanel.AddItem(pdData) as PulldownButton);
            if (pdBtn == null)
            {
                Logger.Warning($"Failed to add pulldown button '{pulldownText}' to panel.");
                return null;
            }

            // Apply post-processing to the pulldown button itself
            ButtonPostProcessor.Process(
                pdBtn,
                component,
                null,
                IconMode.LargeAndSmall);

            // Add children
            AddChildrenToPulldown(pdBtn, component, assemblyInfo, visibleChildren);

            Logger.Debug($"Created pulldown button '{pulldownText}' with {visibleChildren.Count} visible children.");
            return pdData;
        }

        /// <summary>
        /// Adds child buttons to an existing pulldown button. Filters the component's
        /// children against the current <see cref="BuildContext"/> and deactivates the
        /// pulldown if nothing remains visible.
        /// </summary>
        public void AddChildrenToPulldown(PulldownButton pdBtn, ParsedComponent component, ExtensionAssemblyInfo assemblyInfo)
        {
            if (!TryGetVisibleChildren(component, pdBtn, out var visibleChildren))
                return;

            AddChildrenToPulldown(pdBtn, component, assemblyInfo, visibleChildren);
        }

        private void AddChildrenToPulldown(
            PulldownButton pdBtn,
            ParsedComponent component,
            ExtensionAssemblyInfo assemblyInfo,
            IReadOnlyList<ParsedComponent> visibleChildren)
        {
            // Check if children already exist (reload scenario)
            var existingItems = GetExistingChildButtons(pdBtn);
            if (existingItems.Count > 0)
            {
                Logger.Debug($"Pulldown button '{component.DisplayName}' already has {existingItems.Count} children - updating existing buttons.");
                UpdateExistingChildren(pdBtn, component, visibleChildren, existingItems, assemblyInfo);
                return;
            }

            foreach (var sub in visibleChildren)
            {
                AddSingleChildToPulldown(pdBtn, sub, component, assemblyInfo);
            }
        }

        private void AddSingleChildToPulldown(
            PulldownButton pdBtn,
            ParsedComponent sub,
            ParsedComponent component,
            ExtensionAssemblyInfo assemblyInfo)
        {
            if (sub.Type == CommandComponentType.Separator)
            {
                // Skip adding separators during reload - they persist in the UI
                if (assemblyInfo?.IsReloading == true)
                {
                    Logger.Debug($"Skipping separator during reload for pulldown button '{component.DisplayName}'.");
                    return;
                }
                try
                {
                    pdBtn.AddSeparator();
                }
                catch (Exception ex)
                {
                    Logger.Debug($"Failed to add separator to pulldown button. Exception: {ex.Message}");
                }
                return;
            }

            if (sub.Type == CommandComponentType.PushButton ||
                sub.Type == CommandComponentType.UrlButton ||
                sub.Type == CommandComponentType.InvokeButton ||
                sub.Type == CommandComponentType.ContentButton)
            {
                var subBtn = TimedAddItem(() => pdBtn.AddPushButton(CreatePushButtonData(sub, assemblyInfo!)));
                if (subBtn != null)
                {
                    ButtonPostProcessor.Process(subBtn, sub, component, GetCompactIconMode(sub));
                }
                return;
            }

            if (sub.Type == CommandComponentType.SmartButton)
            {
                var smartSubBtn = TimedAddItem(() => pdBtn.AddPushButton(CreatePushButtonData(sub, assemblyInfo!)));
                if (smartSubBtn != null)
                {
                    ButtonPostProcessor.Process(smartSubBtn, sub, component, GetCompactIconMode(sub));

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
                return;
            }

            if (sub.Type == CommandComponentType.LinkButton)
            {
                var linkData = _linkButtonBuilder.CreateLinkButtonData(sub);
                if (linkData != null)
                {
                    var linkSubBtn = TimedAddItem(() => pdBtn.AddPushButton(linkData));
                    if (linkSubBtn != null)
                    {
                        ButtonPostProcessor.Process(linkSubBtn, sub, component, GetCompactIconMode(sub));
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
        private void UpdateExistingChildren(
            PulldownButton pdBtn,
            ParsedComponent component,
            IReadOnlyList<ParsedComponent> visibleChildren,
            List<RibbonItem> existingItems,
            ExtensionAssemblyInfo assemblyInfo)
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

            Logger.Debug($"Updating {visibleChildren.Count} visible children in pulldown '{component.DisplayName}'. Found {existingByName.Count} existing buttons.");

            var touchedNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            foreach (var sub in visibleChildren)
            {
                if (sub.Type == CommandComponentType.Separator)
                    continue;

                touchedNames.Add(sub.DisplayName);

                Logger.Debug($"Looking for child '{sub.DisplayName}' in pulldown '{component.DisplayName}'...");

                // Try to find existing button by name
                if (existingByName.TryGetValue(sub.DisplayName, out var existingBtn))
                {
                    // Update existing button properties
                    try
                    {
                        if (sub.Type == CommandComponentType.LinkButton)
                        {
                            _linkButtonBuilder.UpdateExistingLinkButton(existingBtn, sub, component, GetCompactIconMode(sub));
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
                        ButtonPostProcessor.Process(existingBtn, sub, component, GetCompactIconMode(sub));

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
                    Logger.Debug($"Creating previously-hidden child '{sub.DisplayName}' in pulldown '{component.DisplayName}'.");
                    try
                    {
                        AddSingleChildToPulldown(pdBtn, sub, component, assemblyInfo);
                    }
                    catch (Exception ex)
                    {
                        Logger.Error($"Failed to create child '{sub.DisplayName}' in pulldown '{component.DisplayName}': {ex.Message}");
                    }
                }
            }

            foreach (var existingByNamePair in existingByName)
            {
                if (!touchedNames.Contains(existingByNamePair.Key))
                {
                    Logger.Debug($"Hiding stale pulldown child '{existingByNamePair.Key}' in '{component.DisplayName}'.");
                    DeactivateRibbonItem(existingByNamePair.Value, existingByNamePair.Key);
                }
            }
        }
    }
}
