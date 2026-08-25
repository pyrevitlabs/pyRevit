#nullable enable
using System.Windows.Media;
using Autodesk.Revit.UI;

namespace pyRevitAssemblyBuilder.UIManager.Panels
{
    /// <summary>
    /// Interface for managing panel styling and background colors.
    /// </summary>
    public interface IPanelStyleManager
    {
        /// <summary>
        /// Converts an ARGB color string to a SolidColorBrush.
        /// </summary>
        /// <param name="argbColor">Color string in format #AARRGGBB or #RRGGBB.</param>
        /// <returns>SolidColorBrush or null if conversion fails.</returns>
        SolidColorBrush? ArgbToBrush(string argbColor);

        /// <summary>
        /// Gets the Autodesk.Windows RibbonPanel for a given Revit RibbonPanel.
        /// </summary>
        /// <param name="revitPanel">The Revit ribbon panel.</param>
        /// <param name="tabName">The name of the tab containing this panel.</param>
        /// <returns>The Autodesk.Windows.RibbonPanel or null if not found.</returns>
        Autodesk.Windows.RibbonPanel? GetAdWindowsPanel(RibbonPanel revitPanel, string tabName);
    }
}
