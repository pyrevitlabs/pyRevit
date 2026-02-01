#nullable enable
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
        /// Registers hooks and checks for the specified extension.
        /// </summary>
        /// <param name="extension">The extension to register hooks for.</param>
        void RegisterHooks(ParsedExtension extension);
    }
}
