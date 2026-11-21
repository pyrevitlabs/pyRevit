#nullable enable
using System;
using System.IO;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager
{
    /// <summary>
    /// Tells whether a command click on a bundle runs its script under CPython.
    /// </summary>
    /// <remarks>
    /// Important: the precedence mirrors the runtime's engine choice for a click (<c>ScriptRuntime.EngineType</c>
    /// plus the configs <c>CommandTypeGenerator</c> writes): a bundle's own <c>CPython</c> or <c>IronPython</c>
    /// <c>engine.type</c> wins; any other non-blank <c>engine.type</c> is ignored and, like a bundle without one,
    /// the choice falls to a first line containing <c>python3</c> or <c>cpython</c>. The extension's CPython
    /// declaration applies only to bundles without an <c>engine.type</c>.
    /// Keep the three in sync, or start-up reports a failure for scripts that run fine on click.
    /// </remarks>
    internal static class CPythonScriptDetector
    {
        private const string IronPythonEngineType = "IronPython";
        private static readonly string[] FirstLineMarkers = { "python3", "cpython" };

        internal static bool RunsOnCPython(ParsedComponent component, ParsedExtension? extension)
        {
            var hasEngineOverride = component.Engine?.HasTypeOverride == true;
            if (hasEngineOverride)
            {
                if (IsEngineType(component.Engine!.Type, ParsedExtension.CPythonEngineType))
                    return true;
                if (IsEngineType(component.Engine.Type, IronPythonEngineType))
                    return false;
            }
            else if (extension?.DeclaresCPython == true)
            {
                return true;
            }

            var firstLine = ReadFirstLine(component.ScriptPath);
            return firstLine != null && Array.Exists(FirstLineMarkers, marker => firstLine.Contains(marker));
        }

        private static bool IsEngineType(string type, string expected)
        {
            return string.Equals(type, expected, StringComparison.OrdinalIgnoreCase);
        }

        private static string? ReadFirstLine(string? scriptPath)
        {
            if (string.IsNullOrEmpty(scriptPath) || !File.Exists(scriptPath))
                return null;

            try
            {
                using var reader = new StreamReader(scriptPath);
                return reader.ReadLine();
            }
            catch (Exception ex) when (ex is IOException || ex is UnauthorizedAccessException)
            {
                return null;
            }
        }
    }
}
