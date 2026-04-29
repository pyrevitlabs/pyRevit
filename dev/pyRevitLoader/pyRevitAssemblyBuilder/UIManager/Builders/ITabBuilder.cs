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
        /// Creates a ribbon tab from the specified component, or finds and re-enables
        /// an existing one (including tabs whose Title was renamed by a script).
        /// </summary>
        /// <param name="component">The tab component to create.</param>
        /// <returns>
        /// The tab's current display Title if it differs from the requested name
        /// (i.e. the tab was renamed by a script), or null if no rename was detected.
        /// Callers can use this to dual-mark the scanner registry under both names.
        /// </returns>
        string? CreateTab(ParsedComponent component);

        /// <summary>
        /// Tags a ribbon tab with the pyRevit identifier for runtime icon toggling.
        /// </summary>
        /// <param name="tabName">The name of the tab to tag.</param>
        void TagTabAsPyRevit(string tabName);
    }
}
