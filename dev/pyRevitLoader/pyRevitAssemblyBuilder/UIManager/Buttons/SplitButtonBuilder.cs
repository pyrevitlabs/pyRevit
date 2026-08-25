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
    /// Builder for split buttons.
    /// </summary>
    public class SplitButtonBuilder : ButtonBuilderBase
    {
        private readonly BuildContext _buildContext;
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
        /// <param name="buildContext">Shared build context that carries the current per-build settings.</param>
        /// <param name="logger">The logger instance.</param>
        /// <param name="buttonPostProcessor">The button post-processor.</param>
        /// <param name="linkButtonBuilder">The link button builder for child link buttons.</param>
        /// <param name="smartButtonScriptInitializer">Optional SmartButton script initializer.</param>
        public SplitButtonBuilder(
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
                Logger.Warning($"Cannot create split button '{component.DisplayName}': parent panel is null.");
                return;
            }

            var existingSplitBtn = GetExistingSplitButton(parentPanel, component.DisplayName);
            if (!TryGetVisibleChildren(component, existingSplitBtn, out var visibleChildren))
                return;

            if (existingSplitBtn != null)
            {
                Logger.Debug($"Split button '{component.DisplayName}' already exists - updating.");
                UpdateExistingSplitButton(existingSplitBtn, component, visibleChildren, assemblyInfo);
                return;
            }

            try
            {
                // Use Title from bundle.yaml if available, with config script indicator if applicable
                var splitButtonText = ButtonPostProcessor.GetButtonText(component);
                var splitData = new SplitButtonData(component.DisplayName, splitButtonText);
                var splitBtn = TimedAddItem(() => parentPanel.AddItem(splitData) as SplitButton);

                if (splitBtn != null)
                {
                    // Apply post-processing to split button
                    ButtonPostProcessor.Process(splitBtn, component, null, IconMode.LargeAndSmall);

                    // Add children
                    AddChildrenToSplitButton(splitBtn, component, assemblyInfo, visibleChildren);

                    Logger.Debug($"Created split button '{splitButtonText}' with {visibleChildren.Count} visible children.");
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
        private void UpdateExistingSplitButton(
            SplitButton splitBtn,
            ParsedComponent component,
            IReadOnlyList<ParsedComponent> visibleChildren,
            ExtensionAssemblyInfo assemblyInfo)
        {
            try
            {
                // Update display text
                var splitButtonText = ButtonPostProcessor.GetButtonText(component);
                splitBtn.ItemText = splitButtonText;

                // Re-apply post-processing (icon, tooltip, etc.)
                ButtonPostProcessor.Process(splitBtn, component, null, IconMode.LargeAndSmall);

                splitBtn.Enabled = true;
                splitBtn.Visible = true;

                // Update children
                AddChildrenToSplitButton(splitBtn, component, assemblyInfo, visibleChildren);

                Logger.Debug($"Updated existing split button '{component.DisplayName}'.");
            }
            catch (Exception ex)
            {
                Logger.Error($"Failed to update split button '{component.DisplayName}': {ex.Message}");
            }
        }

        /// <summary>
        /// Adds child buttons to an existing split button. Filters the component's
        /// children against the current <see cref="BuildContext"/> and deactivates the
        /// split button if nothing remains visible.
        /// </summary>
        public void AddChildrenToSplitButton(SplitButton splitBtn, ParsedComponent component, ExtensionAssemblyInfo assemblyInfo)
        {
            if (!TryGetVisibleChildren(component, splitBtn, out var visibleChildren))
                return;

            AddChildrenToSplitButton(splitBtn, component, assemblyInfo, visibleChildren);
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
                Logger.Debug($"Split button '{component.DisplayName}' has no visible children after filtering. Hiding it.");
                DeactivateRibbonItem(existingRibbonItem, component.DisplayName);
                return false;
            }

            return true;
        }

        private void AddChildrenToSplitButton(
            SplitButton splitBtn,
            ParsedComponent component,
            ExtensionAssemblyInfo assemblyInfo,
            IReadOnlyList<ParsedComponent> visibleChildren)
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
                UpdateExistingChildren(splitBtn, component, visibleChildren, existingItems, assemblyInfo);
                return;
            }

            PushButton? firstButton = null;
            int childCount = 0;

            foreach (var sub in visibleChildren)
            {
                var added = AddSingleChildToSplitButton(splitBtn, sub, component, assemblyInfo);
                if (added != null)
                {
                    firstButton ??= added;
                    childCount++;
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

        private PushButton? AddSingleChildToSplitButton(
            SplitButton splitBtn,
            ParsedComponent sub,
            ParsedComponent component,
            ExtensionAssemblyInfo assemblyInfo)
        {
            if (sub.Type == CommandComponentType.Separator)
            {
                // Skip adding separators during reload - they persist in the UI
                if (assemblyInfo?.IsReloading == true)
                {
                    Logger.Debug($"Skipping separator during reload for split button '{component.DisplayName}'.");
                    return null;
                }
                try
                {
                    splitBtn.AddSeparator();
                }
                catch (Exception ex)
                {
                    Logger.Debug($"Failed to add separator to split button. Exception: {ex.Message}");
                }
                return null;
            }

            if (sub.Type == CommandComponentType.SmartButton)
            {
                try
                {
                    var pushButtonData = CreatePushButtonData(sub, assemblyInfo!);
                    var subBtn = TimedAddItem(() => splitBtn.AddPushButton(pushButtonData));
                    if (subBtn != null)
                    {
                        ButtonPostProcessor.Process(subBtn, sub, component, GetCompactIconMode(sub));

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

                        Logger.Debug($"Added SmartButton '{sub.DisplayName}' to split button '{component.DisplayName}'.");
                        return subBtn;
                    }

                    Logger.Warning($"AddPushButton returned null for SmartButton '{sub.DisplayName}' in split button '{component.DisplayName}'.");
                }
                catch (Exception ex)
                {
                    Logger.Error($"Failed to add SmartButton '{sub.DisplayName}' to split button '{component.DisplayName}'. Exception: {ex.Message}");
                }
                return null;
            }

            if (sub.Type == CommandComponentType.PushButton ||
                sub.Type == CommandComponentType.UrlButton ||
                sub.Type == CommandComponentType.InvokeButton ||
                sub.Type == CommandComponentType.ContentButton)
            {
                try
                {
                    var pushButtonData = CreatePushButtonData(sub, assemblyInfo!);
                    var subBtn = TimedAddItem(() => splitBtn.AddPushButton(pushButtonData));
                    if (subBtn != null)
                    {
                        ButtonPostProcessor.Process(subBtn, sub, component, GetCompactIconMode(sub));
                        Logger.Debug($"Added child button '{sub.DisplayName}' to split button '{component.DisplayName}'.");
                        return subBtn;
                    }

                    Logger.Warning($"AddPushButton returned null for child '{sub.DisplayName}' in split button '{component.DisplayName}'.");
                }
                catch (Exception ex)
                {
                    Logger.Error($"Failed to add child button '{sub.DisplayName}' to split button '{component.DisplayName}'. Exception: {ex.Message}");
                }
                return null;
            }

            if (sub.Type == CommandComponentType.LinkButton)
            {
                try
                {
                    var subLinkData = _linkButtonBuilder.CreateLinkButtonData(sub);
                    if (subLinkData != null)
                    {
                        var linkSubBtn = TimedAddItem(() => splitBtn.AddPushButton(subLinkData));
                        if (linkSubBtn != null)
                        {
                            ButtonPostProcessor.Process(linkSubBtn, sub, component, GetCompactIconMode(sub));
                            Logger.Debug($"Added link button '{sub.DisplayName}' to split button '{component.DisplayName}'.");
                            return linkSubBtn;
                        }

                        Logger.Warning($"AddPushButton returned null for link button '{sub.DisplayName}' in split button '{component.DisplayName}'.");
                    }
                }
                catch (Exception ex)
                {
                    Logger.Error($"Failed to add link button '{sub.DisplayName}' to split button '{component.DisplayName}'. Exception: {ex.Message}");
                }
            }

            return null;
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

        private static bool IsRibbonItemVisible(RibbonItem item, bool fallbackVisible)
        {
            try { return item.Visible; }
            catch { return fallbackVisible; }
        }

        /// <summary>
        /// Updates existing child buttons in a split button during reload.
        /// Matches Python's behavior where existing buttons are updated with new properties.
        /// </summary>
        private void UpdateExistingChildren(
            SplitButton splitBtn,
            ParsedComponent component,
            IReadOnlyList<ParsedComponent> visibleChildren,
            System.Collections.Generic.List<RibbonItem> existingItems,
            ExtensionAssemblyInfo assemblyInfo)
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

            Logger.Debug($"Updating {visibleChildren.Count} visible children in split button '{component.DisplayName}'. Found {existingByName.Count} existing buttons.");

            var touchedNames = new System.Collections.Generic.HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var newlyVisibleNames = new System.Collections.Generic.HashSet<string>(StringComparer.OrdinalIgnoreCase);

            foreach (var sub in visibleChildren)
            {
                if (sub.Type == CommandComponentType.Separator)
                    continue;

                touchedNames.Add(sub.DisplayName);

                Logger.Debug($"Looking for child '{sub.DisplayName}' in split button '{component.DisplayName}'...");

                // Try to find existing button by name
                if (existingByName.TryGetValue(sub.DisplayName, out var existingBtn))
                {
                    // Update existing button properties
                    try
                    {
                        var wasVisible = IsRibbonItemVisible(existingBtn, fallbackVisible: true);

                        if (sub.Type == CommandComponentType.LinkButton)
                        {
                            _linkButtonBuilder.UpdateExistingLinkButton(existingBtn, sub, component, GetCompactIconMode(sub));
                            if (!wasVisible && IsRibbonItemVisible(existingBtn, fallbackVisible: false))
                                newlyVisibleNames.Add(sub.DisplayName);
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
                        ButtonPostProcessor.Process(existingBtn, sub, component, GetCompactIconMode(sub));

                        // Ensure button is active
                        existingBtn.Enabled = true;
                        existingBtn.Visible = true;
                        if (!wasVisible && IsRibbonItemVisible(existingBtn, fallbackVisible: false))
                            newlyVisibleNames.Add(sub.DisplayName);

                        Logger.Debug($"Updated existing child button '{sub.DisplayName}' in split button '{component.DisplayName}'. New text: '{buttonText}'");
                    }
                    catch (Exception ex)
                    {
                        Logger.Error($"Failed to update child button '{sub.DisplayName}' in split button: {ex.Message}");
                    }
                }
                else
                {
                    Logger.Debug($"Creating previously-hidden child '{sub.DisplayName}' in split button '{component.DisplayName}'.");
                    try
                    {
                        var added = AddSingleChildToSplitButton(splitBtn, sub, component, assemblyInfo);
                        if (added != null)
                        {
                            existingByName[sub.DisplayName] = added;
                            newlyVisibleNames.Add(sub.DisplayName);

                            if (splitBtn.CurrentButton == null)
                            {
                                try
                                {
                                    splitBtn.CurrentButton = added;
                                    Logger.Debug($"Set CurrentButton to newly-added '{sub.DisplayName}' for split button '{component.DisplayName}'.");
                                }
                                catch (Exception ex)
                                {
                                    Logger.Debug($"Failed to set CurrentButton on split button '{component.DisplayName}'. Exception: {ex.Message}");
                                }
                            }
                        }
                    }
                    catch (Exception ex)
                    {
                        Logger.Error($"Failed to create child '{sub.DisplayName}' in split button '{component.DisplayName}': {ex.Message}");
                    }
                }
            }

            foreach (var existingByNamePair in existingByName)
            {
                if (!touchedNames.Contains(existingByNamePair.Key))
                {
                    Logger.Debug($"Hiding stale split child '{existingByNamePair.Key}' in '{component.DisplayName}'.");
                    DeactivateRibbonItem(existingByNamePair.Value, existingByNamePair.Key);
                }
            }

            RebindCurrentButtonIfNeeded(splitBtn, component, visibleChildren, existingByName, touchedNames, newlyVisibleNames);
        }

        /// <summary>
        /// If <see cref="SplitButton.CurrentButton"/> points at a child that was just deactivated
        /// (or is otherwise invisible), reassign it to the first still-visible child in the
        /// declared <paramref name="visibleChildren"/> order. Without this, the split button's
        /// primary action would render as nothing after a beta/version toggle hides the
        /// previously-active child. Also restores declaration-order precedence when reload makes
        /// an earlier child visible again. Walks <paramref name="visibleChildren"/> rather than
        /// the dictionary so the replacement choice is stable across .NET runtimes.
        /// </summary>
        private void RebindCurrentButtonIfNeeded(
            SplitButton splitBtn,
            ParsedComponent component,
            IReadOnlyList<ParsedComponent> visibleChildren,
            System.Collections.Generic.Dictionary<string, PushButton> existingByName,
            System.Collections.Generic.HashSet<string> touchedNames,
            System.Collections.Generic.HashSet<string> newlyVisibleNames)
        {
            try
            {
                var current = splitBtn.CurrentButton;
                if (current == null)
                    return;

                var currentName = current.Name ?? string.Empty;
                var currentIsStale = !string.IsNullOrEmpty(currentName) && !touchedNames.Contains(currentName);

                bool currentIsVisible;
                try { currentIsVisible = current.Visible; }
                catch { currentIsVisible = true; }

                if (!currentIsStale && currentIsVisible)
                {
                    if (string.IsNullOrEmpty(currentName))
                        return;

                    foreach (var sub in visibleChildren)
                    {
                        if (sub.Type == CommandComponentType.Separator)
                            continue;
                        if (string.Equals(sub.DisplayName, currentName, StringComparison.OrdinalIgnoreCase))
                            break;
                        if (!newlyVisibleNames.Contains(sub.DisplayName))
                            continue;
                        if (!existingByName.TryGetValue(sub.DisplayName, out var candidate))
                            continue;
                        if (!IsRibbonItemVisible(candidate, fallbackVisible: false))
                            continue;

                        splitBtn.CurrentButton = candidate;
                        Logger.Debug($"Rebound CurrentButton to newly-visible preceding child '{candidate.Name}' for split button '{component.DisplayName}'.");
                        return;
                    }

                    return;
                }

                PushButton? replacement = null;
                foreach (var sub in visibleChildren)
                {
                    if (sub.Type == CommandComponentType.Separator)
                        continue;
                    if (!existingByName.TryGetValue(sub.DisplayName, out var candidate))
                        continue;
                    if (!IsRibbonItemVisible(candidate, fallbackVisible: false))
                        continue;
                    replacement = candidate;
                    break;
                }

                if (replacement == null || ReferenceEquals(replacement, current))
                    return;

                splitBtn.CurrentButton = replacement;
                Logger.Debug($"Rebound CurrentButton to '{replacement.Name}' for split button '{component.DisplayName}' (previous was stale or hidden).");
            }
            catch (Exception ex)
            {
                Logger.Debug($"Failed to rebind CurrentButton on split button '{component.DisplayName}'. Exception: {ex.Message}");
            }
        }
    }
}
