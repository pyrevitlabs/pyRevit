#nullable enable
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager.Builders
{
    /// <summary>
    /// Interface for building stacked button groups.
    /// </summary>
    public interface IStackBuilder
    {
        /// <summary>
        /// Builds a stack of buttons from the specified component.
        /// </summary>
        /// <param name="component">The stack component containing child buttons.</param>
        /// <param name="parentPanel">The panel to add the stack to.</param>
        /// <param name="assemblyInfo">Information about the assembly containing command implementations.</param>
        void BuildStack(ParsedComponent component, RibbonPanel parentPanel, ExtensionAssemblyInfo assemblyInfo);
    }
}
