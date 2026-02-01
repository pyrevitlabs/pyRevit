#nullable enable
using pyRevitAssemblyBuilder;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager.Builders
{
    /// <summary>
    /// Interface for building ribbon tabs in Revit.
    /// </summary>
    public interface ITabBuilder
    {
        /// <summary>
        /// Creates a ribbon tab from the specified component.
        /// </summary>
        /// <param name="component">The tab component to create.</param>
        void CreateTab(ParsedComponent component);

        /// <summary>
        /// Tags a ribbon tab with the pyRevit identifier for runtime icon toggling.
        /// </summary>
        /// <param name="tabName">The name of the tab to tag.</param>
        void TagTabAsPyRevit(string tabName);
    }
}
