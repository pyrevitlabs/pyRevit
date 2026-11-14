#nullable enable
using System;
using System.Linq;
using Autodesk.Revit.UI;
using Autodesk.Windows;
using pyRevitAssemblyBuilder.SessionManager;
using pyRevitAssemblyBuilder.UIManager.Icons;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager.Builders
{
    /// <summary>
    /// Handles the creation and management of ribbon tabs.
    /// </summary>
    public class TabBuilder : ITabBuilder
    {
        private readonly ILogger _logger;
        private readonly UIApplication _uiApp;
        private readonly ITabIconDecorator _tabIconDecorator;

        /// <summary>
        /// Initializes a new instance of the <see cref="TabBuilder"/> class.
        /// </summary>
        /// <param name="uiApp">The Revit UIApplication instance.</param>
        /// <param name="logger">The logger instance.</param>
        /// <param name="tabIconDecorator">Shows the optional tab bundle icon before the tab title.</param>
        public TabBuilder(UIApplication uiApp, ILogger logger, ITabIconDecorator tabIconDecorator)
        {
            _uiApp = uiApp ?? throw new ArgumentNullException(nameof(uiApp));
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _tabIconDecorator = tabIconDecorator ?? throw new ArgumentNullException(nameof(tabIconDecorator));
        }

        /// <inheritdoc/>
        public string? CreateTab(ParsedComponent component)
        {
            if (component == null)
            {
                _logger.Warning("Cannot create tab: component is null.");
                return null;
            }

            // Use localized title which handles fallback to DisplayName
            var tabText = ExtensionParser.GetComponentTitle(component);

            try
            {
                _uiApp.CreateRibbonTab(tabText);
            }
            catch (Exception ex)
            {
                // Tab may already exist, which is acceptable - log at debug level
                _logger.Debug($"Failed to create ribbon tab '{tabText}'. Tab may already exist. Exception: {ex.Message}");
            }

            // Find the tab, tag it as pyRevit, ensure it's visible, and detect renames.
            // Done in a single ribbon scan to avoid the circular dependency where
            // TagTabAsPyRevit would need the Tag to find renamed tabs but is itself
            // the method that sets the Tag.
            string? renamedTitle = null;
            try
            {
                var ribbon = ComponentManager.Ribbon;
                if (ribbon?.Tabs == null) return null;

                // Primary search: exact Title or Id match
                var existingTab = ribbon.Tabs.FirstOrDefault(t =>
                    t.Title == tabText || t.Id == tabText);

                // Fallback: tab was renamed by a script (e.g. translation) so Title no
                // longer matches. Search by pyRevit Tag (set during the previous session)
                // combined with exact Id match. The Tag persists on the AdWindows object
                // across reloads within the same Revit session.
                if (existingTab == null)
                {
                    existingTab = ribbon.Tabs.FirstOrDefault(t =>
                        (t.Tag as string) == UIManagerConstants.PyRevitTabIdentifier
                        && string.Equals(t.Id, tabText, StringComparison.OrdinalIgnoreCase));
                }

                if (existingTab != null)
                {
                    existingTab.Tag = UIManagerConstants.PyRevitTabIdentifier;
                    existingTab.IsVisible = true;
                    existingTab.IsEnabled = true;
                    ApplyTabIcon(existingTab, component);

                    // Detect rename: if the current Title differs, return it so the
                    // caller can dual-mark the scanner registry under both names.
                    if (existingTab.Title != tabText)
                    {
                        renamedTitle = existingTab.Title;
                        _logger.Debug($"Tab '{tabText}' found with renamed Title '{renamedTitle}'.");
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.Debug($"Failed to find/enable tab '{tabText}'. Exception: {ex.Message}");
            }

            return renamedTitle;
        }

        private void ApplyTabIcon(RibbonTab tab, ParsedComponent component)
        {
            var lightIconPath = component.Icons?.PrimaryIcon?.FilePath;
            var darkIconPath = component.Icons?.PrimaryDarkIcon?.FilePath;
            if (lightIconPath == null && darkIconPath == null)
                return;

            try
            {
                var currentSource = _tabIconDecorator.GetIconSource(tab);
                if (currentSource == null)
                {
                    _tabIconDecorator.TryAddIcons(tab, component.Directory, lightIconPath, darkIconPath);
                }
                else if (!string.Equals(currentSource, component.Directory, StringComparison.OrdinalIgnoreCase))
                {
                    _logger.Error(
                        $"Tab '{tab.Title}' already shows the icon from '{currentSource}'; " +
                        $"the icon in '{component.Directory}' is ignored. Keep a tab icon in only one extension.");
                }
            }
            catch (Exception ex)
            {
                _logger.Debug($"Failed to apply icon to tab '{tab.Title}'. Exception: {ex.Message}");
            }
        }

        /// <inheritdoc/>
        public void TagTabAsPyRevit(string tabName)
        {
            if (string.IsNullOrEmpty(tabName))
            {
                _logger.Debug("Cannot tag tab: tabName is null or empty.");
                return;
            }

            try
            {
                var ribbon = ComponentManager.Ribbon;
                if (ribbon?.Tabs == null)
                    return;

                // Primary: find by Title or Id
                var tab = ribbon.Tabs.FirstOrDefault(t =>
                    t.Title == tabName || t.Id == tabName);

                // Fallback: renamed tab — match by existing Tag + exact Id
                if (tab == null)
                {
                    tab = ribbon.Tabs.FirstOrDefault(t =>
                        (t.Tag as string) == UIManagerConstants.PyRevitTabIdentifier
                        && string.Equals(t.Id, tabName, StringComparison.OrdinalIgnoreCase));
                }

                if (tab != null)
                {
                    tab.Tag = UIManagerConstants.PyRevitTabIdentifier;
                }
            }
            catch (Exception ex)
            {
                _logger.Debug($"Failed to tag tab '{tabName}' as pyRevit tab. Exception: {ex.Message}");
            }
        }
    }
}
