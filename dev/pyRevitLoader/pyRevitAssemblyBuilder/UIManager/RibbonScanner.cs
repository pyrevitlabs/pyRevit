#nullable enable
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Autodesk.Windows;
using pyRevitAssemblyBuilder.SessionManager;

namespace pyRevitAssemblyBuilder.UIManager
{
    /// <summary>
    /// Service for scanning and managing pyRevit UI elements in the ribbon.
    /// Uses a registry-based approach to track which elements are pyRevit-managed
    /// and which have been touched during the current session.
    ///
    /// This mirrors Python's _PyRevitUI wrapper approach where:
    /// 1. A registry tracks all pyRevit UI elements by their IDs
    /// 2. During session load, elements are marked as "touched" when created/updated
    /// 3. After loading, untouched elements are deactivated (hidden)
    /// </summary>
    public class RibbonScanner : IUIRibbonScanner
    {
        private readonly ILogger _logger;

        // Registry of known pyRevit UI elements
        // Key format: "{type}:{id}" or "{type}:{parentId}:{id}" for hierarchical items
        // Value: true if touched during current session, false otherwise
        private readonly Dictionary<string, bool> _elementRegistry = new Dictionary<string, bool>(StringComparer.OrdinalIgnoreCase);

        // Prefix used to identify pyRevit tabs (matching Python behavior)
        private const string PYREVIT_TAB_PREFIX = "pyRevit";

        /// <summary>
        /// Initializes a new instance of the <see cref="RibbonScanner"/> class.
        /// </summary>
        /// <param name="logger">The logger instance for diagnostics.</param>
        public RibbonScanner(ILogger logger)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
        }

        /// <inheritdoc/>
        public void ResetDirtyFlags()
        {
            try
            {
                // If registry is empty, scan the existing ribbon to discover pyRevit UI elements
                // This handles the case where pyRevit was already loaded before this instance was created
                // (matching Python's get_current_ui() which scans ribbon on first access)
                if (_elementRegistry.Count == 0)
                {
                    ScanExistingPyRevitElements();
                }

                // Mark all registered elements as untouched (dirty = false in Python terminology)
                var keys = _elementRegistry.Keys.ToList();
                foreach (var key in keys)
                {
                    _elementRegistry[key] = false;
                }

                _logger.Debug($"Reset dirty flags on {keys.Count} registered pyRevit UI elements.");
            }
            catch (Exception ex)
            {
                _logger.Error($"Error resetting dirty flags: {ex.Message}");
            }
        }

        /// <summary>
        /// Scans the existing ribbon for pyRevit UI elements and adds them to the registry.
        /// This is called on first use to discover tabs/panels/buttons that were created in a previous session.
        /// Matches Python's _PyRevitUI.__init__() which scans ribbon tabs on construction.
        /// </summary>
        private void ScanExistingPyRevitElements()
        {
            try
            {
                var ribbon = ComponentManager.Ribbon;
                if (ribbon?.Tabs == null)
                {
                    _logger.Debug("Cannot scan existing elements: ribbon or tabs is null.");
                    return;
                }

                int tabCount = 0;
                int panelCount = 0;
                int buttonCount = 0;

                foreach (var tab in ribbon.Tabs)
                {
                    if (tab == null) continue;

                    // Check if this is a pyRevit tab by looking at the Tag property
                    // pyRevit tabs are tagged with UIManagerConstants.PyRevitTabIdentifier
                    if (!IsPyRevitTabByTag(tab))
                        continue;

                    var tabName = tab.Title ?? tab.Id;
                    if (string.IsNullOrEmpty(tabName))
                        continue;

                    // Register the tab
                    var tabKey = BuildKey("tab", tabName, null);
                    _elementRegistry[tabKey] = false; // Will be marked true when touched
                    tabCount++;
                    _logger.Debug($"Discovered existing pyRevit tab: {tabName}");

                    // Register panels in this tab
                    if (tab.Panels != null)
                    {
                        foreach (var panelObj in tab.Panels)
                        {
                            var panel = panelObj as RibbonPanel;
                            if (panel == null) continue;

                            var panelName = panel.Source?.Title ?? panel.Source?.Id ?? "";
                            if (string.IsNullOrEmpty(panelName))
                                continue;

                            var panelKey = BuildKey("panel", panelName, tabName);
                            _elementRegistry[panelKey] = false;
                            panelCount++;
                            _logger.Debug($"Discovered existing pyRevit panel: {panelName} in tab {tabName}");

                            // Register buttons in this panel
                            if (panel.Source?.Items != null)
                            {
                                buttonCount += ScanPanelItems(panel.Source.Items, panelName);
                            }
                        }
                    }
                }

                _logger.Info($"Scanned ribbon and discovered {tabCount} pyRevit tabs with {panelCount} panels and {buttonCount} buttons.");
            }
            catch (Exception ex)
            {
                _logger.Error($"Error scanning existing pyRevit elements: {ex.Message}");
            }
        }

        /// <summary>
        /// Recursively scans panel items (buttons, split buttons, pulldowns, stacks) and registers them.
        /// </summary>
        private int ScanPanelItems(IEnumerable<RibbonItem> items, string panelName)
        {
            int count = 0;
            foreach (var item in items)
            {
                if (item == null) continue;

                // Handle RibbonRowPanel (stack) specially - its children should use panelName as parent
                // This matches how UIManagerService marks stack children:
                //   _ribbonScanner?.MarkElementTouched("button", child.DisplayName, panelName);
                if (item is RibbonRowPanel rowPanel && rowPanel.Items != null)
                {
                    // Scan stack items with panelName as parent (not the row panel's name)
                    foreach (var stackItem in rowPanel.Items)
                    {
                        if (stackItem == null) continue;

                        var stackItemName = GetButtonIdentifier(stackItem);
                        if (string.IsNullOrEmpty(stackItemName))
                            continue;

                        // Use panelName as parent to match UIManagerService's MarkElementTouched
                        var stackItemKey = BuildKey("button", stackItemName, panelName);
                        _elementRegistry[stackItemKey] = false;
                        count++;

                        // Also scan children of stack items (e.g., split buttons in stack)
                        if (stackItem is RibbonSplitButton splitInStack && splitInStack.Items != null)
                        {
                            count += ScanContainerItems(splitInStack.Items, stackItemName);
                        }
                        else if (stackItem is RibbonMenuButton menuInStack && menuInStack.Items != null)
                        {
                            count += ScanContainerItems(menuInStack.Items, stackItemName);
                        }
                    }
                    continue;
                }

                var buttonName = GetButtonIdentifier(item);
                if (string.IsNullOrEmpty(buttonName))
                    continue;

                var itemKey = BuildKey("button", buttonName, panelName);
                _elementRegistry[itemKey] = false;
                count++;

                // Scan children of container buttons (split buttons, pulldowns)
                if (item is RibbonSplitButton splitButton && splitButton.Items != null)
                {
                    count += ScanContainerItems(splitButton.Items, buttonName);
                }
                else if (item is RibbonMenuButton menuButton && menuButton.Items != null)
                {
                    count += ScanContainerItems(menuButton.Items, buttonName);
                }
            }
            return count;
        }

        /// <summary>
        /// Scans children of container buttons (split, pulldown, stack).
        /// </summary>
        private int ScanContainerItems(IEnumerable<RibbonItem> items, string parentName)
        {
            int count = 0;
            foreach (var item in items)
            {
                if (item == null) continue;

                var buttonName = GetButtonIdentifier(item);
                if (string.IsNullOrEmpty(buttonName))
                    continue;

                var buttonKey = BuildKey("button", buttonName, parentName);
                _elementRegistry[buttonKey] = false;
                count++;
            }
            return count;
        }

        /// <summary>
        /// Gets the identifier for a ribbon item used for tracking.
        /// Extracts the button's internal name from the Id property.
        /// </summary>
        private static string GetButtonIdentifier(RibbonItem item)
        {
            // The Id property contains the control ID in format like:
            // "CustomCtrl_%CustomCtrl_%Add-Ins%TabName%ButtonName" or just "ButtonName"
            // We need to extract the last segment which is the button's DisplayName
            // This matches what UIManagerService.MarkElementTouched() uses (DisplayName from folder basename)

            var id = item.Id;
            if (!string.IsNullOrEmpty(id))
            {
                // Extract the last segment after the last '%' character
                var lastPercentIndex = id.LastIndexOf('%');
                if (lastPercentIndex >= 0 && lastPercentIndex < id.Length - 1)
                {
                    return id.Substring(lastPercentIndex + 1);
                }
                return id; // Return as-is if no '%' found
            }

            // Fallback to AutomationName if Id is not available
            return item.AutomationName ?? "";
        }

        /// <summary>
        /// Checks if a tab is a pyRevit tab by examining its Tag property.
        /// </summary>
        private bool IsPyRevitTabByTag(RibbonTab tab)
        {
            try
            {
                // Check if the tab has been tagged as a pyRevit tab
                var tag = tab.Tag as string;
                return tag == UIManagerConstants.PyRevitTabIdentifier;
            }
            catch
            {
                return false;
            }
        }

        /// <inheritdoc/>
        public void MarkElementTouched(string elementType, string elementId, string? parentId = null)
        {
            if (string.IsNullOrEmpty(elementType) || string.IsNullOrEmpty(elementId))
                return;

            var key = BuildKey(elementType, elementId, parentId);
            _elementRegistry[key] = true; // Mark as touched

            _logger.Debug($"Marked element as touched: {key}");
        }

        /// <inheritdoc/>
        public bool IsRegisteredElement(string elementType, string elementId)
        {
            if (string.IsNullOrEmpty(elementType) || string.IsNullOrEmpty(elementId))
                return false;

            var key = BuildKey(elementType, elementId, null);
            return _elementRegistry.ContainsKey(key);
        }

        /// <inheritdoc/>
        public void CleanupOrphanedElements()
        {
            try
            {
                // Early exit if registry is empty (first load - nothing to cleanup)
                if (_elementRegistry.Count == 0)
                {
                    _logger.Debug("Registry is empty (first load) - skipping cleanup.");
                    return;
                }

                var ribbon = ComponentManager.Ribbon;
                if (ribbon?.Tabs == null)
                {
                    _logger.Debug("Cannot cleanup orphaned elements: ribbon or tabs is null.");
                    return;
                }

                // Get all untouched elements (those with value = false)
                var untouchedElements = _elementRegistry
                    .Where(kvp => !kvp.Value)
                    .Select(kvp => kvp.Key)
                    .ToList();

                // Early exit if no untouched elements
                if (untouchedElements.Count == 0)
                {
                    _logger.Debug("No untouched elements to cleanup - all elements were touched.");
                    return;
                }

                _logger.Debug($"Found {untouchedElements.Count} untouched elements to cleanup: {string.Join(", ", untouchedElements)}");

                int hiddenCount = 0;

                // Process untouched tabs
                foreach (var tab in ribbon.Tabs.ToList())
                {
                    if (tab == null) continue;

                    var tabKey = BuildKey("tab", tab.Title ?? tab.Id, null);

                    // Only process if this is a registered pyRevit tab that wasn't touched
                    if (untouchedElements.Contains(tabKey))
                    {
                        // Deactivate: set visible=false, enabled=false (matching Python behavior)
                        DeactivateTab(tab);
                        hiddenCount++;
                        _logger.Debug($"Deactivated orphaned tab: {tab.Title}");
                        continue; // Skip processing panels if tab is hidden
                    }

                    // Process panels in this tab
                    if (tab.Panels != null)
                    {
                        foreach (var panelObj in tab.Panels.ToList())
                        {
                            var panel = panelObj as RibbonPanel;
                            if (panel == null) continue;

                            var panelName = panel.Source?.Title ?? panel.Source?.Id ?? "";
                            var panelKey = BuildKey("panel", panelName, tab.Title);

                            if (untouchedElements.Contains(panelKey))
                            {
                                DeactivatePanel(panel);
                                hiddenCount++;
                                _logger.Debug($"Deactivated orphaned panel: {panelName}");
                                continue; // Skip processing buttons if panel is hidden
                            }

                            // Process buttons in this panel
                            if (panel.Source?.Items != null)
                            {
                                foreach (var item in panel.Source.Items.ToList())
                                {
                                    if (item == null) continue;

                                    // Handle RibbonRowPanel (stack) - check children with panelName as parent
                                    if (item is RibbonRowPanel rowPanel && rowPanel.Items != null)
                                    {
                                        foreach (var stackItem in rowPanel.Items.ToList())
                                        {
                                            if (stackItem == null) continue;

                                            var stackItemName = GetButtonIdentifier(stackItem);
                                            var stackItemKey = BuildKey("button", stackItemName, panelName);

                                            if (untouchedElements.Contains(stackItemKey))
                                            {
                                                DeactivateItem(stackItem);
                                                hiddenCount++;
                                                _logger.Debug($"Deactivated orphaned stack item: {stackItemName}");
                                            }
                                        }
                                        continue;
                                    }

                                    // Use same identifier method as scanning for consistency
                                    var buttonName = GetButtonIdentifier(item);
                                    var buttonKey = BuildKey("button", buttonName, panelName);

                                    if (untouchedElements.Contains(buttonKey))
                                    {
                                        DeactivateItem(item);
                                        hiddenCount++;
                                        _logger.Debug($"Deactivated orphaned button: {buttonName}");
                                    }
                                }
                            }
                        }
                    }
                }

                // Remove deactivated elements from registry
                foreach (var key in untouchedElements)
                {
                    _elementRegistry.Remove(key);
                }

                _logger.Info($"Cleaned up {hiddenCount} orphaned pyRevit UI elements.");
            }
            catch (Exception ex)
            {
                _logger.Error($"Error cleaning up orphaned elements: {ex.Message}");
            }
        }

        /// <inheritdoc/>
        public void ResetPanelBackgrounds()
        {
            try
            {
                var ribbon = ComponentManager.Ribbon;
                if (ribbon?.Tabs == null)
                {
                    _logger.Debug("Cannot reset panel backgrounds: ribbon or tabs is null.");
                    return;
                }

                int resetCount = 0;

                foreach (var tab in ribbon.Tabs)
                {
                    if (tab?.Panels == null) continue;

                    // Only process pyRevit tabs (matching Python behavior)
                    if (!IsPyRevitTab(tab))
                        continue;

                    foreach (var panelObj in tab.Panels)
                    {
                        var panel = panelObj as RibbonPanel;
                        if (panel == null) continue;

                        // Reset custom backgrounds
                        try
                        {
                            panel.CustomPanelBackground = null;
                            panel.CustomPanelTitleBarBackground = null;
                            panel.CustomSlideOutPanelBackground = null;
                            resetCount++;
                        }
                        catch (Exception ex)
                        {
                            _logger.Debug($"Failed to reset background for panel: {ex.Message}");
                        }
                    }
                }

                _logger.Debug($"Reset backgrounds on {resetCount} pyRevit panels.");
            }
            catch (Exception ex)
            {
                _logger.Error($"Error resetting panel backgrounds: {ex.Message}");
            }
        }

        /// <summary>
        /// Builds a registry key for an element.
        /// </summary>
        private static string BuildKey(string elementType, string elementId, string? parentId)
        {
            if (string.IsNullOrEmpty(parentId))
                return $"{elementType}:{elementId}";
            return $"{elementType}:{parentId}:{elementId}";
        }

        /// <summary>
        /// Checks if a tab is a pyRevit tab (not native Revit).
        /// </summary>
        private bool IsPyRevitTab(RibbonTab tab)
        {
            // Check if this tab is in our registry
            var tabKey = BuildKey("tab", tab.Title ?? tab.Id, null);
            if (_elementRegistry.ContainsKey(tabKey))
                return true;

            // Also check for tabs created by pyRevit based on naming or other heuristics
            // In Python, pyRevit tabs are identified by having the pyRevit addin ID
            // For now, we'll rely on the registry
            return false;
        }

        /// <summary>
        /// Deactivates a ribbon tab (sets visible=false, enabled=false).
        /// Matches Python's deactivate() behavior.
        /// </summary>
        private void DeactivateTab(RibbonTab tab)
        {
            try
            {
                tab.IsVisible = false;
                tab.IsEnabled = false;
            }
            catch (Exception ex)
            {
                _logger.Debug($"Failed to deactivate tab '{tab?.Title}': {ex.Message}");
            }
        }

        /// <summary>
        /// Deactivates a ribbon panel (sets visible=false, enabled=false).
        /// </summary>
        private void DeactivatePanel(RibbonPanel panel)
        {
            try
            {
                panel.IsVisible = false;
                panel.IsEnabled = false;
            }
            catch (Exception ex)
            {
                _logger.Debug($"Failed to deactivate panel '{panel?.Source?.Title}': {ex.Message}");
            }
        }

        /// <summary>
        /// Deactivates a ribbon item (sets visible=false, enabled=false).
        /// </summary>
        private void DeactivateItem(RibbonItem item)
        {
            try
            {
                item.IsVisible = false;
                item.IsEnabled = false;
            }
            catch (Exception ex)
            {
                _logger.Debug($"Failed to deactivate item '{item?.AutomationName}': {ex.Message}");
            }
        }
    }
}
