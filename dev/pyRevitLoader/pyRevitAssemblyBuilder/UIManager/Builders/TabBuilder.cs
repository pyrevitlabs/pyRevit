#nullable enable
using System;
using System.Linq;
using Autodesk.Revit.UI;
using Autodesk.Windows;
using pyRevitAssemblyBuilder.SessionManager;
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

        /// <summary>
        /// Initializes a new instance of the <see cref="TabBuilder"/> class.
        /// </summary>
        /// <param name="uiApp">The Revit UIApplication instance.</param>
        /// <param name="logger">The logger instance.</param>
        public TabBuilder(UIApplication uiApp, ILogger logger)
        {
            _uiApp = uiApp ?? throw new ArgumentNullException(nameof(uiApp));
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
        }

        /// <inheritdoc/>
        public void CreateTab(ParsedComponent component)
        {
            if (component == null)
            {
                _logger.Warning("Cannot create tab: component is null.");
                return;
            }

            // Use localized title which handles fallback to DisplayName
            var tabText = ExtensionParser.GetComponentTitle(component);
            
            try
            {
                _uiApp.CreateRibbonTab(tabText);
                _logger.Debug($"Created ribbon tab '{tabText}'.");
            }
            catch (Exception ex)
            {
                // Tab may already exist, which is acceptable - log at debug level
                _logger.Debug($"Failed to create ribbon tab '{tabText}'. Tab may already exist. Exception: {ex.Message}");
            }

            // Mark the tab as a pyRevit tab so toggle_icon can find it at runtime
            TagTabAsPyRevit(tabText);
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

                // Find the tab by Title (display name) since that's how tabs are identified
                var tab = ribbon.Tabs.FirstOrDefault(t => t.Title == tabName || t.Id == tabName);
                if (tab != null)
                {
                    tab.Tag = UIManagerConstants.PyRevitTabIdentifier;
                    _logger.Debug($"Tagged tab '{tabName}' as pyRevit tab for runtime icon toggling");
                }
            }
            catch (Exception ex)
            {
                _logger.Debug($"Failed to tag tab '{tabName}' as pyRevit tab. Exception: {ex.Message}");
            }
        }
    }
}
