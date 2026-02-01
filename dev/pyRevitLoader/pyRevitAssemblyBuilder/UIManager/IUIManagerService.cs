#nullable enable
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager
{
    /// <summary>
    /// Interface for building Revit UI elements from parsed extensions.
    /// </summary>
    public interface IUIManagerService
    {
        /// <summary>
        /// Gets the UIApplication instance used by this service.
        /// </summary>
        UIApplication UIApplication { get; }

        /// <summary>
        /// Builds the UI for the specified extension using the provided assembly information.
        /// </summary>
        /// <param name="extension">The parsed extension containing UI component definitions.</param>
        /// <param name="assemblyInfo">Information about the assembly containing command implementations.</param>
        void BuildUI(ParsedExtension extension, ExtensionAssemblyInfo assemblyInfo);
    }
}
