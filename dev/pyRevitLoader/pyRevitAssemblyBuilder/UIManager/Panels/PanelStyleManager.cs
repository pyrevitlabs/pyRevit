#nullable enable
using System;
using System.Linq;
using System.Windows.Media;
using Autodesk.Revit.UI;
using Autodesk.Windows;
using pyRevitAssemblyBuilder.SessionManager;
using RibbonPanel = Autodesk.Revit.UI.RibbonPanel;

namespace pyRevitAssemblyBuilder.UIManager.Panels
{
    /// <summary>
    /// Manages panel styling including background colors and visual customization.
    /// </summary>
    public class PanelStyleManager : IPanelStyleManager
    {
        private readonly ILogger _logger;

        /// <summary>
        /// Initializes a new instance of the <see cref="PanelStyleManager"/> class.
        /// </summary>
        /// <param name="logger">The logger instance.</param>
        public PanelStyleManager(ILogger logger)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
        }

        /// <inheritdoc/>
        public SolidColorBrush? ArgbToBrush(string argbColor)
        {
            if (string.IsNullOrEmpty(argbColor))
                return null;

            try
            {
                // Default values
                string a = "FF", r = "FF", g = "FF", b = "FF";

                // Remove # if present
                argbColor = argbColor.TrimStart('#');

                // Parse color components
                if (argbColor.Length >= 6)
                {
                    b = argbColor.Substring(argbColor.Length - 2, 2);
                    g = argbColor.Substring(argbColor.Length - 4, 2);
                    r = argbColor.Substring(argbColor.Length - 6, 2);

                    if (argbColor.Length >= 8)
                    {
                        a = argbColor.Substring(argbColor.Length - 8, 2);
                    }
                }

                byte alpha = Convert.ToByte(a, 16);
                byte red = Convert.ToByte(r, 16);
                byte green = Convert.ToByte(g, 16);
                byte blue = Convert.ToByte(b, 16);

                return new SolidColorBrush(Color.FromArgb(alpha, red, green, blue));
            }
            catch (Exception ex)
            {
                _logger.Debug($"Failed to convert ARGB color string '{argbColor}' to SolidColorBrush. Exception: {ex.Message}");
                return null;
            }
        }

        /// <inheritdoc/>
        public Autodesk.Windows.RibbonPanel? GetAdWindowsPanel(RibbonPanel revitPanel, string tabName)
        {
            if (revitPanel == null || string.IsNullOrEmpty(tabName))
                return null;

            try
            {
                var ribbon = ComponentManager.Ribbon;
                if (ribbon?.Tabs == null)
                    return null;

                var tab = ribbon.Tabs.FirstOrDefault(t => t.Id == tabName);
                if (tab?.Panels == null)
                    return null;

                return tab.Panels.FirstOrDefault(p => p.Source?.Title == revitPanel.Name);
            }
            catch (Exception ex)
            {
                _logger.Debug($"Failed to get Autodesk.Windows panel for '{revitPanel?.Name ?? "unknown"}' in tab '{tabName}'. Exception: {ex.Message}");
                return null;
            }
        }
    }
}
