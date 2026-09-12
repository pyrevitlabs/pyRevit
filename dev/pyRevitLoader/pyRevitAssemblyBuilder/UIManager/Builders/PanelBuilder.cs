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
        private readonly RevitThemeDetector _themeDetector;

        /// <summary>
        /// Initializes a new instance of the <see cref="PanelBuilder"/> class.
        /// </summary>
        /// <param name="uiApp">The Revit UIApplication instance.</param>
        /// <param name="logger">The logger instance.</param>
        /// <param name="styleManager">The panel style manager for applying colors.</param>
        public PanelBuilder(UIApplication uiApp, ILogger logger, IPanelStyleManager styleManager)
            : this(uiApp, logger, styleManager, null)
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="PanelBuilder"/> class with a custom theme detector.
        /// </summary>
        /// <param name="uiApp">The Revit UIApplication instance.</param>
        /// <param name="logger">The logger instance.</param>
        /// <param name="styleManager">The panel style manager for applying colors.</param>
        /// <param name="themeDetector">Theme detector used to choose between light and dark backgrounds.</param>
        public PanelBuilder(
            UIApplication uiApp,
            ILogger logger,
            IPanelStyleManager styleManager,
            RevitThemeDetector? themeDetector)
        {
            _uiApp = uiApp ?? throw new ArgumentNullException(nameof(uiApp));
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _styleManager = styleManager ?? throw new ArgumentNullException(nameof(styleManager));
            _themeDetector = themeDetector ?? new RevitThemeDetector(logger);
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

            try
            {
                var adwPanel = _styleManager.GetAdWindowsPanel(panel, tabName);
                if (adwPanel != null)
                {
                    adwPanel.IsVisible = true;
                    adwPanel.IsEnabled = true;
                }
            }
            catch (Exception ex)
            {
                _logger.Debug($"Failed to re-enable panel '{panelText}' in tab '{tabName}'. Exception: {ex.Message}");
            }

            return panel;
        }

        /// <inheritdoc/>
        public void ApplyPanelBackgroundColors(RibbonPanel revitPanel, ParsedComponent component, string tabName)
        {
            if (component == null || revitPanel == null)
                return;

            if (!PanelBackgroundResolver.HasBackgroundColors(component))
                return;

            try
            {
                var adwPanel = _styleManager.GetAdWindowsPanel(revitPanel, tabName);
                if (adwPanel == null)
                    return;

                var panelName = revitPanel.Name;
                RibbonThemeRegistry.Register(
                    adwPanel,
                    isDarkTheme => ApplyPanelBackgroundColors(adwPanel, component, panelName, tabName, isDarkTheme));

                ApplyPanelBackgroundColors(adwPanel, component, panelName, tabName, _themeDetector.IsDarkTheme());
            }
            catch (Exception ex)
            {
                _logger.Debug($"Failed to apply background colors to panel '{revitPanel.Name}' in tab '{tabName}'. Exception: {ex.Message}");
            }
        }

        /// <summary>
        /// Paints a panel with the background colors declared for the supplied theme.
        /// </summary>
        /// <remarks>
        /// Invariant: the three custom brushes are cleared before painting. A panel that declares
        /// colors for one theme only must fall back to the stock Revit background in the other theme
        /// rather than keep the brushes applied for the previous theme.
        /// </remarks>
        private void ApplyPanelBackgroundColors(
            Autodesk.Windows.RibbonPanel adwPanel,
            ParsedComponent component,
            string panelName,
            string tabName,
            bool isDarkTheme)
        {
            try
            {
                adwPanel.CustomPanelBackground = null;
                adwPanel.CustomPanelTitleBarBackground = null;
                adwPanel.CustomSlideOutPanelBackground = null;

                var colors = PanelBackgroundResolver.Resolve(component, isDarkTheme);

                // Apply panel background - if specified, it sets all three areas
                if (colors.Panel is string panelColor && panelColor.Length > 0)
                {
                    var panelBrush = _styleManager.ArgbToBrush(panelColor);
                    if (panelBrush != null)
                    {
                        adwPanel.CustomPanelBackground = panelBrush;
                        adwPanel.CustomPanelTitleBarBackground = panelBrush;
                        adwPanel.CustomSlideOutPanelBackground = panelBrush;
                    }
                }

                // Override title background if explicitly specified
                if (colors.Title is string titleColor && titleColor.Length > 0)
                {
                    var titleBrush = _styleManager.ArgbToBrush(titleColor);
                    if (titleBrush != null)
                        adwPanel.CustomPanelTitleBarBackground = titleBrush;
                }

                // Override slideout background if explicitly specified
                if (colors.Slideout is string slideoutColor && slideoutColor.Length > 0)
                {
                    var slideoutBrush = _styleManager.ArgbToBrush(slideoutColor);
                    if (slideoutBrush != null)
                        adwPanel.CustomSlideOutPanelBackground = slideoutBrush;
                }

                _logger.Debug($"Applied {(isDarkTheme ? "dark" : "light")} background colors to panel '{panelName}' in tab '{tabName}'.");
            }
            catch (Exception ex)
            {
                _logger.Debug($"Failed to apply background colors to panel '{panelName}' in tab '{tabName}'. Exception: {ex.Message}");
            }
        }
    }
}
