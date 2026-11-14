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
        /// <remarks>
        /// Invariant: the tab is found and created under the component's folder name
        /// (<see cref="ParsedComponent.DisplayName"/>), which Revit keeps as the tab id. The localized
        /// title is applied afterwards to a new tab, or to one still showing the title the loader applied
        /// last in this Revit session, so a bundle title edit or locale change takes effect on reload and
        /// a title a script chose is left alone.
        /// </remarks>
        /// <param name="component">The tab component to create.</param>
        /// <returns>
        /// The tab's current display Title if it differs from the folder name (a localized title or a
        /// rename by a script), or null if the tab shows its folder name.
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
