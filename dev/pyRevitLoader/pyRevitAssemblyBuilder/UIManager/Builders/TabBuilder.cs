#nullable enable
using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
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
        private static readonly ConcurrentDictionary<string, string> AppliedTitles =
            new ConcurrentDictionary<string, string>();

        private readonly ILogger _logger;
        private readonly UIApplication _uiApp;
        private readonly ITabIconDecorator _tabIconDecorator;
        private readonly bool _showTabIcons;

        /// <summary>
        /// Initializes a new instance of the <see cref="TabBuilder"/> class.
        /// </summary>
        /// <param name="uiApp">The Revit UIApplication instance.</param>
        /// <param name="logger">The logger instance.</param>
        /// <param name="tabIconDecorator">Must be the instance <see cref="SessionManagerService"/> resets and refreshes around each UI build.</param>
        /// <param name="showTabIcons">When <c>false</c>, no tab icon is recorded, so the decorator's
        /// refresh removes any icon a previous session drew.</param>
        public TabBuilder(UIApplication uiApp, ILogger logger, ITabIconDecorator tabIconDecorator, bool showTabIcons = true)
        {
            _uiApp = uiApp ?? throw new ArgumentNullException(nameof(uiApp));
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _tabIconDecorator = tabIconDecorator ?? throw new ArgumentNullException(nameof(tabIconDecorator));
            _showTabIcons = showTabIcons;
        }

        /// <inheritdoc/>
        public string? CreateTab(ParsedComponent component)
        {
            if (component == null)
            {
                _logger.Warning("Cannot create tab: component is null.");
                return null;
            }

            var tabText = component.DisplayName;
            var tabTitle = ExtensionParser.GetComponentTitle(component);

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

                var existingTab = ribbon.Tabs.FirstOrDefault(t => t.Id == tabText)
                    ?? ribbon.Tabs.FirstOrDefault(t => t.Title == tabText);

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

                    if (ShouldApplyTitle(existingTab, tabText, tabTitle))
                    {
                        existingTab.Title = tabTitle;
                        AppliedTitles[tabText] = tabTitle;
                    }

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
            if (!_showTabIcons)
                return;

            var lightIconPath = FirstRasterIconPath(component.Icons?.LightIcons);
            var darkIconPath = FirstRasterIconPath(component.Icons?.DarkIcons);
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

        private static string? FirstRasterIconPath(IEnumerable<ComponentIcon>? icons) =>
            icons?.FirstOrDefault(i =>
                i.IsValid && !string.Equals(i.Extension, ".svg", StringComparison.OrdinalIgnoreCase))?.FilePath;

        private static bool ShouldApplyTitle(RibbonTab tab, string tabName, string tabTitle)
        {
            if (string.IsNullOrEmpty(tabTitle) || tab.Title == tabTitle)
                return false;

            return AppliedTitles.TryGetValue(tabName, out var appliedTitle)
                ? appliedTitle == tab.Title
                : tab.Title == tabName;
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
