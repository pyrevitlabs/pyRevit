using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Collections.Generic;
using System.Reflection;
using System.Reflection.Emit;
using Microsoft.CodeAnalysis;
using Autodesk.Revit.Attributes;
using pyRevitExtensionParser;
#if !NETFRAMEWORK
using System.Runtime.Loader;
#endif

namespace pyRevitAssemblyBuilder.AssemblyMaker
{
    /// <summary>
    /// Generates C# code for commands via Roslyn.
    /// </summary>
    public class RoslynCommandTypeGenerator
    {
        /// <summary>
        /// Generates C# source code for all commands in the extension.
        /// </summary>
        public string GenerateExtensionCode(ParsedExtension extension)
        {
            var sb = new StringBuilder();
            sb.AppendLine("#nullable disable");
            sb.AppendLine("using Autodesk.Revit.Attributes;");
            sb.AppendLine("using PyRevitLabs.PyRevit.Runtime;");

            foreach (var cmd in CollectCommandComponents(extension.Children))
            {
                string safeClassName = SanitizeClassName(cmd.UniqueId);
                string originalUniqueName = cmd.UniqueId;
                string scriptPath = cmd.ScriptPath;
                string searchPaths = string.Join(";", new[]
                {
                    Path.GetDirectoryName(cmd.ScriptPath),
                    Path.Combine(extension.Directory, "lib"),
                    Path.Combine(extension.Directory, "..", "..", "pyrevitlib"),
                    Path.Combine(extension.Directory, "..", "..", "site-packages")
                });
                string tooltip = cmd.Tooltip ?? string.Empty;
                string name = cmd.Name;
                string bundle = Path.GetFileName(Path.GetDirectoryName(cmd.ScriptPath));
                string extName = extension.Name;
                string ctrlId = $"CustomCtrl_%{extName}%{bundle}%{name}";
                string engineCfgs = "{\"clean\": false, \"persistent\": false, \"full_frame\": false}";

                sb.AppendLine();
                sb.AppendLine("[Regeneration(RegenerationOption.Manual)]");
                sb.AppendLine("[Transaction(TransactionMode.Manual)]");
                sb.AppendLine($"public class {safeClassName} : ScriptCommand");
                sb.AppendLine("{");
                sb.AppendLine($"    public {safeClassName}() : base(");
                sb.AppendLine($"        @\"{EscapeForVerbatim(scriptPath)}\",");
                sb.AppendLine($"        @\"{EscapeForVerbatim(scriptPath)}\",");
                sb.AppendLine($"        @\"{EscapeForVerbatim(searchPaths)}\",");
                sb.AppendLine($"        \"\",");
                sb.AppendLine($"        \"\",");
                sb.AppendLine($"        @\"{EscapeForVerbatim(tooltip)}\",");
                sb.AppendLine($"        \"{Escape(name)}\",");
                sb.AppendLine($"        \"{Escape(bundle)}\",");
                sb.AppendLine($"        \"{Escape(extName)}\",");
                sb.AppendLine($"        \"{originalUniqueName}\",");
                sb.AppendLine($"        \"{Escape(ctrlId)}\",");
                sb.AppendLine($"        \"(zero-doc)\",");
                sb.AppendLine($"        \"{Escape(engineCfgs)}\"");
                sb.AppendLine("    )");
                sb.AppendLine("    {");
                sb.AppendLine("    }");
                sb.AppendLine("}");
            }

            return sb.ToString();
        }

        private IEnumerable<ParsedComponent> CollectCommandComponents(IEnumerable<ParsedComponent> components)
        {
            foreach (var comp in components)
            {
                if (!string.IsNullOrEmpty(comp.ScriptPath))
                    yield return comp;
                if (comp.Children != null)
                {
                    foreach (var child in CollectCommandComponents(comp.Children))
                        yield return child;
                }
            }
        }

        private static string SanitizeClassName(string name)
        {
            var sb = new StringBuilder();
            foreach (char c in name)
                sb.Append(char.IsLetterOrDigit(c) ? c : '_');
            return sb.ToString();
        }

        private static string EscapeForVerbatim(string str) =>
            (str ?? string.Empty).Replace("\"", "\"\"");

        private static string Escape(string str) =>
            (str ?? string.Empty)
                .Replace("\\", "\\\\")
                .Replace("\"", "\\\"");
    }

    /// <summary>
    /// Generates command types via Reflection.Emit and packs via ILPack.
    /// </summary>
    public class ReflectionEmitCommandTypeGenerator
    {
        private static readonly Type ScriptCommandBaseType;
        private static readonly ConstructorInfo ScriptCommandCtor;
        private static readonly string RevitRuntimeNamePrefix = "PyRevitLabs.PyRevit.Runtime";

        static ReflectionEmitCommandTypeGenerator()
        {
            // 1) Try to find an already‐loaded runtime assembly
            var asm = AppDomain.CurrentDomain.GetAssemblies()
                        .FirstOrDefault(a => a.GetName().Name.StartsWith(RevitRuntimeNamePrefix, StringComparison.OrdinalIgnoreCase));

            // 2) If not found, probe two folders up from this DLL and load it
            if (asm == null)
            {
                var loaderDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
                var twoUp = Path.GetFullPath(Path.Combine(loaderDir, "..", ".."));

                // look for any matching runtime DLL in that folder
                var candidate = Directory
                    .EnumerateFiles(twoUp, $"{RevitRuntimeNamePrefix}.*.dll", SearchOption.TopDirectoryOnly)
                    .FirstOrDefault();

                if (candidate != null)
                {
                    #if NETFRAMEWORK
                    asm = Assembly.LoadFrom(candidate);
                    #else
                    asm = AssemblyLoadContext.Default.LoadFromAssemblyPath(candidate);
                    #endif
                }
            }

            if (asm == null)
                throw new InvalidOperationException($"Could not load any assembly named {RevitRuntimeNamePrefix}.*.dll");

            // 3) Grab the ScriptCommand type
            ScriptCommandBaseType = asm.GetType("PyRevitLabs.PyRevit.Runtime.ScriptCommand")
                ?? throw new InvalidOperationException("ScriptCommand type not found in runtime assembly.");

            // 4) Locate the 13-string constructor
            var stringParams = Enumerable.Repeat(typeof(string), 13).ToArray();
            ScriptCommandCtor = ScriptCommandBaseType.GetConstructor(
                BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic,
                null, stringParams, null)
                ?? throw new InvalidOperationException("Could not find the 13-string constructor on ScriptCommand.");
        }


        public void DefineCommandType(ParsedExtension extension, ParsedComponent cmd, ModuleBuilder moduleBuilder)
        {
            // Create the type deriving from ScriptCommand
            var tb = moduleBuilder.DefineType(
                SanitizeClassName(cmd.UniqueId),
                TypeAttributes.Public | TypeAttributes.Class,
                ScriptCommandBaseType);

            // [Regeneration(RegenerationOption.Manual)]
            var regenCtor = typeof(RegenerationAttribute)
                .GetConstructor(new[] { typeof(RegenerationOption) })!;
            tb.SetCustomAttribute(
                new CustomAttributeBuilder(regenCtor, new object[] { RegenerationOption.Manual }));

            // [Transaction(TransactionMode.Manual)]
            var transCtor = typeof(TransactionAttribute)
                .GetConstructor(new[] { typeof(TransactionMode) })!;
            tb.SetCustomAttribute(
                new CustomAttributeBuilder(transCtor, new object[] { TransactionMode.Manual }));

            // Define the parameterless ctor
            var ctor = tb.DefineConstructor(
                MethodAttributes.Public,
                CallingConventions.Standard,
                Type.EmptyTypes);
            var il = ctor.GetILGenerator();

            // **1) Load 'this' onto the stack**
            il.Emit(OpCodes.Ldarg_0);

            // 2) Push all 13 string arguments
            string scriptPath = cmd.ScriptPath ?? string.Empty;
            string configPath = cmd.ScriptPath ?? string.Empty;
            string searchPaths = string.Join(";", new[]
            {
        Path.GetDirectoryName(cmd.ScriptPath),
        Path.Combine(extension.Directory, "lib"),
        Path.Combine(extension.Directory, "..", "..", "pyrevitlib"),
        Path.Combine(extension.Directory, "..", "..", "site-packages")
    });
            string[] ctorArgs = {
        scriptPath,
        configPath,
        searchPaths,
        "",
        "",
        cmd.Tooltip ?? string.Empty,
        cmd.Name,
        Path.GetFileName(Path.GetDirectoryName(cmd.ScriptPath)),
        extension.Name,
        cmd.UniqueId,
        $"CustomCtrl_%{extension.Name}%{Path.GetFileName(Path.GetDirectoryName(cmd.ScriptPath))}%{cmd.Name}",
        "(zero-doc)",
        "{\"clean\":false,\"persistent\":false,\"full_frame\":false}"
    };
            foreach (var arg in ctorArgs)
                il.Emit(OpCodes.Ldstr, arg);

            // 3) Call the base ScriptCommand ctor
            il.Emit(OpCodes.Call, ScriptCommandCtor);

            // 4) Return
            il.Emit(OpCodes.Ret);

            // Bake the type
            tb.CreateType();
        }
        private static string SanitizeClassName(string name)
        {
            var sb = new StringBuilder();
            foreach (char c in name)
                sb.Append(char.IsLetterOrDigit(c) ? c : '_');
            return sb.ToString();
        }
    }
}
