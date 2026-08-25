#nullable enable
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager.Builders
{
    /// <summary>
    /// Interface for building ribbon panels in Revit.
    /// </summary>
    public interface IPanelBuilder
    {
        /// <summary>
        /// Creates or retrieves a ribbon panel from the specified component.
        /// </summary>
        /// <param name="component">The panel component to create.</param>
        /// <param name="tabName">The name of the tab containing this panel.</param>
        /// <returns>The created or existing RibbonPanel.</returns>
        RibbonPanel CreatePanel(ParsedComponent component, string tabName);

        /// <summary>
        /// Applies background colors to a panel based on component settings.
        /// </summary>
        /// <param name="revitPanel">The Revit ribbon panel.</param>
        /// <param name="component">The component containing color settings.</param>
        /// <param name="tabName">The name of the tab containing this panel.</param>
        void ApplyPanelBackgroundColors(RibbonPanel revitPanel, ParsedComponent component, string tabName);
    }
}
