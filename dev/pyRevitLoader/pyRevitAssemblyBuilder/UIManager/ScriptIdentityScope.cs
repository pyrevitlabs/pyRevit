#nullable enable
using System.Collections.Generic;
using System.IO;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager
{
    /// <summary>
    /// Builds the identity values a script sees in its own module scope when pyRevit runs it outside a
    /// command click, such as a smart button's start-up initializer or a checkbox's handler setup.
    /// </summary>
    /// <remarks>
    /// Important: <c>EXEC_PARAMS</c> reads <c>__commandname__</c> and the other identity values from the
    /// nearest calling module that also defines <c>__scriptruntime__</c>. Without these values,
    /// <c>EXEC_PARAMS.command_name</c> is None while such a script's module level runs, so a call like
    /// <c>script.get_config()</c> there raises. The values match what a click on the same button reports.
    /// </remarks>
    internal static class ScriptIdentityScope
    {
        /// <summary>
        /// Returns the module-scope variables that give <paramref name="component"/>'s script its identity.
        /// <c>__scriptruntime__</c> is None because the run is not a command run.
        /// </summary>
        public static Dictionary<string, object?> Build(ParsedComponent component)
        {
            var bundleDirectory = component.Directory ?? string.Empty;
            return new Dictionary<string, object?>
            {
                ["__scriptruntime__"] = null,
                ["__commandpath__"] = bundleDirectory,
                ["__commandname__"] = component.DisplayName,
                ["__commandbundle__"] = Path.GetFileName(bundleDirectory),
                ["__commandextension__"] = FindExtensionName(bundleDirectory),
                ["__commanduniqueid__"] = component.UniqueId,
            };
        }

        private static string FindExtensionName(string bundleDirectory)
        {
            var current = string.IsNullOrEmpty(bundleDirectory) ? null : new DirectoryInfo(bundleDirectory);
            while (current != null)
            {
                if (current.Name.EndsWith(".extension", System.StringComparison.OrdinalIgnoreCase))
                    return Path.GetFileNameWithoutExtension(current.Name);
                current = current.Parent;
            }

            return string.Empty;
        }
    }
}
