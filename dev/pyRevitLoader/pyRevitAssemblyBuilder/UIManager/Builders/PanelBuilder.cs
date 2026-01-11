#nullable enable
using System;
using System.Linq;
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.SessionManager;
using pyRevitAssemblyBuilder.UIManager.Panels;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager.Builders
{
    /// <summary>
    /// Handles the creation and management of ribbon panels.
    /// </summary>
    public class PanelBuilder : IPanelBuilder
    {
        private readonly ILogger _logger;
        private readonly UIApplication _uiApp;
        private readonly IPanelStyleManager _styleManager;

        /// <summary>
        /// Initializes a new instance of the <see cref="PanelBuilder"/> class.
        /// </summary>
        /// <param name="uiApp">The Revit UIApplication instance.</param>
        /// <param name="logger">The logger instance.</param>
        /// <param name="styleManager">The panel style manager for applying colors.</param>
        public PanelBuilder(UIApplication uiApp, ILogger logger, IPanelStyleManager styleManager)
        {
            _uiApp = uiApp ?? throw new ArgumentNullException(nameof(uiApp));
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _styleManager = styleManager ?? throw new ArgumentNullException(nameof(styleManager));
        }

        /// <inheritdoc/>
        public RibbonPanel CreatePanel(ParsedComponent component, string tabName)
        {
            if (component == null)
            {
                _logger.Warning("Cannot create panel: component is null.");
                return null!;
            }

            if (string.IsNullOrEmpty(tabName))
            {
                _logger.Warning($"Cannot create panel '{component.DisplayName}': tabName is null or empty.");
                return null!;
            }

            // Use localized title which handles fallback to DisplayName
            var panelText = ExtensionParser.GetComponentTitle(component);
            
            var panel = _uiApp.GetRibbonPanels(tabName)
                .FirstOrDefault(p => p.Name == panelText)
                ?? _uiApp.CreateRibbonPanel(tabName, panelText);

            _logger.Debug($"Created or retrieved panel '{panelText}' in tab '{tabName}'.");

            return panel;
        }

        /// <inheritdoc/>
        public void ApplyPanelBackgroundColors(RibbonPanel revitPanel, ParsedComponent component, string tabName)
        {
            if (component == null || revitPanel == null)
                return;

            // Check if any background colors are specified
            bool hasBackgroundColors = !string.IsNullOrEmpty(component.PanelBackground) ||
                                       !string.IsNullOrEmpty(component.TitleBackground) ||
                                       !string.IsNullOrEmpty(component.SlideoutBackground);

            if (!hasBackgroundColors)
                return;

            try
            {
                var adwPanel = _styleManager.GetAdWindowsPanel(revitPanel, tabName);
                if (adwPanel == null)
                    return;

                // Reset backgrounds first
                adwPanel.CustomPanelBackground = null;
                adwPanel.CustomPanelTitleBarBackground = null;
                adwPanel.CustomSlideOutPanelBackground = null;

                // Apply panel background - if specified, it sets all three areas
                // This matches Python's set_background() behavior
                if (!string.IsNullOrEmpty(component.PanelBackground))
                {
                    var panelBrush = _styleManager.ArgbToBrush(component.PanelBackground);
                    if (panelBrush != null)
                    {
                        adwPanel.CustomPanelBackground = panelBrush;
                        adwPanel.CustomPanelTitleBarBackground = panelBrush;
                        adwPanel.CustomSlideOutPanelBackground = panelBrush;
                    }
                }

                // Override title background if explicitly specified
                if (!string.IsNullOrEmpty(component.TitleBackground))
                {
                    var titleBrush = _styleManager.ArgbToBrush(component.TitleBackground);
                    if (titleBrush != null)
                        adwPanel.CustomPanelTitleBarBackground = titleBrush;
                }

                // Override slideout background if explicitly specified
                if (!string.IsNullOrEmpty(component.SlideoutBackground))
                {
                    var slideoutBrush = _styleManager.ArgbToBrush(component.SlideoutBackground);
                    if (slideoutBrush != null)
                        adwPanel.CustomSlideOutPanelBackground = slideoutBrush;
                }

                _logger.Debug($"Applied background colors to panel '{revitPanel.Name}' in tab '{tabName}'.");
            }
            catch (Exception ex)
            {
                _logger.Debug($"Failed to apply background colors to panel '{revitPanel?.Name ?? "unknown"}' in tab '{tabName}'. Exception: {ex.Message}");
            }
        }
    }
}
