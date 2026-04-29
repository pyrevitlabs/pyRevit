#nullable enable
using System.Collections.Generic;
using System.Reflection;
using pyRevitAssemblyBuilder;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Interface for managing extension hooks and checks.
    /// </summary>
    public interface IHookManager
    {
        /// <summary>
        /// Registers hooks for the specified extension by discovering hook scripts
        /// and calling EventHooks.RegisterHook() on the runtime via reflection.
        /// Replaces the Python-side hooks.register_hooks() call that triggered
        /// a redundant full extension re-parse.
        /// </summary>
        /// <param name="extension">The extension to register hooks for.</param>
        /// <param name="libraryExtensions">Library extensions whose lib/ paths are added to hook search paths.</param>
        /// <param name="runtimeAssembly">The loaded pyRevit Runtime assembly for reflection calls.</param>
        /// <param name="pyRevitRoot">Root directory of the pyRevit installation (for pyrevitlib + site-packages paths).</param>
        void RegisterHooks(
            ParsedExtension extension,
            List<ParsedExtension> libraryExtensions,
            Assembly runtimeAssembly,
            string? pyRevitRoot);
    }
}