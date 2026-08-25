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
        /// Gets whether rocket mode is enabled.
        /// When true, non-critical startup work is skipped and engine caching is used for compatible extensions.
        /// </summary>
        bool RocketMode { get; }

        /// <summary>
        /// Builds the UI for the specified extension using the provided assembly information.
        /// </summary>
        /// <param name="extension">The parsed extension containing UI component definitions.</param>
        /// <param name="assemblyInfo">Information about the assembly containing command implementations.</param>
        void BuildUI(ParsedExtension extension, ExtensionAssemblyInfo assemblyInfo);

        /// <summary>
        /// Emits the per-extension [PERF] breakdown lines collected during the most recent
        /// <see cref="BuildUI"/> call. Intended to be called by the session manager immediately
        /// after the wrapping <c>[PERF] {ext.Name} - BuildUI: Xms</c> line.
        /// </summary>
        /// <param name="extensionName">The extension name to use as a prefix on each emitted line.</param>
        void EmitBuildUIPerfLines(string extensionName);
    }
}
