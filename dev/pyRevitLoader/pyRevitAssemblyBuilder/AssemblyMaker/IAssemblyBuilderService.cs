#nullable enable
using System.Collections.Generic;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.AssemblyMaker
{
    /// <summary>
    /// Interface for building extension assemblies from parsed extensions.
    /// </summary>
    public interface IAssemblyBuilderService
    {
        /// <summary>
        /// Builds an assembly for the specified extension.
        /// </summary>
        /// <param name="extension">The parsed extension to build an assembly for.</param>
        /// <param name="libraryExtensions">Optional collection of library extensions to include as references.</param>
        /// <returns>Information about the built assembly, or null if building fails.</returns>
        ExtensionAssemblyInfo? BuildExtensionAssembly(ParsedExtension extension, IEnumerable<ParsedExtension>? libraryExtensions = null);

        /// <summary>
        /// Loads an assembly into the current AppDomain.
        /// </summary>
        /// <param name="info">Information about the assembly to load.</param>
        void LoadAssembly(ExtensionAssemblyInfo info);
    }
}
