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
    /// plus the configs <c>CommandTypeGenerator</c> writes): a bundle's own <c>engine.type</c> wins, then the
    /// extension's CPython declaration, then a first line containing <c>python3</c> or <c>cpython</c>.
    /// Keep the three in sync, or start-up reports a failure for scripts that run fine on click.
    /// </remarks>
    internal static class CPythonScriptDetector
    {
        private static readonly string[] FirstLineMarkers = { "python3", "cpython" };

        internal static bool RunsOnCPython(ParsedComponent component, ParsedExtension? extension)
        {
            if (component.Engine?.HasTypeOverride == true)
                return string.Equals(component.Engine.Type, ParsedExtension.CPythonEngineType, StringComparison.OrdinalIgnoreCase);

            if (extension?.DeclaresCPython == true)
                return true;

            var firstLine = ReadFirstLine(component.ScriptPath);
            return firstLine != null && Array.Exists(FirstLineMarkers, marker => firstLine.Contains(marker));
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
            catch (IOException)
            {
                return null;
            }
        }
    }
}
