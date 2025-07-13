using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Reflection;
using System.Reflection.Emit;
using Autodesk.Revit.Attributes;
using pyRevitExtensionParser;
#if !NETFRAMEWORK
using System.Runtime.Loader;
#endif


namespace pyRevitAssemblyBuilder.AssemblyMaker
{
    /// <summary>
    /// Generates C# code for commands via Roslyn, plus availability classes.
    /// </summary>
    public class RoslynCommandTypeGenerator
    {
        public string GenerateExtensionCode(ParsedExtension extension)
        {
            var sb = new StringBuilder();
            sb.AppendLine("#nullable disable");
            sb.AppendLine("using Autodesk.Revit.Attributes;");
            sb.AppendLine("using PyRevitLabs.PyRevit.Runtime;");
            sb.AppendLine();

            foreach (var cmd in extension.CollectCommandComponents())
            {
                string safeClassName = SanitizeClassName(cmd.UniqueId);
                string scriptPath = cmd.ScriptPath;
                string searchPaths = string.Join(";", new[]
                {
                    Path.GetDirectoryName(cmd.ScriptPath),
                    Path.Combine(extension.Directory, "lib"),
                    Path.Combine(extension.Directory, "..", "..", "pyrevitlib"),
                    Path.Combine(extension.Directory, "..", "..", "site-packages")
                });
                string tooltip = cmd.Tooltip ?? string.Empty;
                string bundle = Path.GetFileName(Path.GetDirectoryName(cmd.ScriptPath));
                string extName = extension.Name;
                string ctrlId = $"CustomCtrl_%{extName}%{bundle}%{cmd.Name}";
                string engineCfgs = "{\"clean\": false, \"persistent\": false, \"full_frame\": false}";

                // — Command class —
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
                sb.AppendLine($"        \"{Escape(cmd.Name)}\",");
                sb.AppendLine($"        \"{Escape(bundle)}\",");
                sb.AppendLine($"        \"{Escape(extName)}\",");
                sb.AppendLine($"        \"{cmd.UniqueId}\",");
                sb.AppendLine($"        \"{Escape(ctrlId)}\",");
                sb.AppendLine($"        \"(zero-doc)\",");
                sb.AppendLine($"        \"{Escape(engineCfgs)}\"");
                sb.AppendLine("    )");
                sb.AppendLine("    {");
                sb.AppendLine("    }");
                sb.AppendLine("}");
                sb.AppendLine();

                // — Availability class —
                sb.AppendLine($"public class {safeClassName}_avail : ScriptCommandExtendedAvail");
                sb.AppendLine("{");
                sb.AppendLine($"    public {safeClassName}_avail() : base(\"(zero-doc)\")");
                sb.AppendLine("    {");
                sb.AppendLine("    }");
                sb.AppendLine("}");
                sb.AppendLine();
            }

            return sb.ToString();
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
    /// Generates command types via Reflection.Emit and packs via ILPack, 
    /// plus availability types via the runtime's ScriptCommandExtendedAvail.
    /// </summary>
    public class ReflectionEmitCommandTypeGenerator
    {
        private const string RuntimeNamePrefix = "PyRevitLabs.PyRevit.Runtime";

        private static readonly Assembly _runtimeAsm;
        private static readonly Type _scriptCommandType;
        private static readonly ConstructorInfo _scriptCommandCtor;
        private static readonly Type _extendedAvailType;
        private static readonly ConstructorInfo _extendedAvailCtor;

        static ReflectionEmitCommandTypeGenerator()
        {
            // 1) Locate or load the runtime assembly (PyRevitLabs.PyRevit.Runtime.*.dll)
            _runtimeAsm = AppDomain.CurrentDomain.GetAssemblies()
                .FirstOrDefault(a => a.GetName().Name.StartsWith(RuntimeNamePrefix, StringComparison.OrdinalIgnoreCase));

            if (_runtimeAsm == null)
            {
                var loaderDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
                var probeDir = Path.GetFullPath(Path.Combine(loaderDir, "..", ".."));
                var candidate = Directory.EnumerateFiles(probeDir, $"{RuntimeNamePrefix}.*.dll", SearchOption.TopDirectoryOnly)
                                          .FirstOrDefault();
                if (candidate != null)
                {
#if NETFRAMEWORK
                    _runtimeAsm = Assembly.LoadFrom(candidate);
#else
                    _runtimeAsm = AssemblyLoadContext.Default.LoadFromAssemblyPath(candidate);
#endif
                }
            }

            if (_runtimeAsm == null)
                throw new InvalidOperationException($"Could not load any assembly named {RuntimeNamePrefix}.*.dll");

            // 2) Resolve ScriptCommand and its 13-string ctor
            _scriptCommandType = _runtimeAsm.GetType("PyRevitLabs.PyRevit.Runtime.ScriptCommand")
                                   ?? throw new InvalidOperationException("ScriptCommand type not found.");
            var stringParams = Enumerable.Repeat(typeof(string), 13).ToArray();
            _scriptCommandCtor = _scriptCommandType.GetConstructor(
                BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic,
                null, stringParams, null)
                ?? throw new InvalidOperationException("ScriptCommand constructor not found.");

            // 3) Resolve ScriptCommandExtendedAvail and its single-string ctor
            _extendedAvailType = _runtimeAsm.GetType("PyRevitLabs.PyRevit.Runtime.ScriptCommandExtendedAvail")
                                  ?? throw new InvalidOperationException("ScriptCommandExtendedAvail type not found.");
            _extendedAvailCtor = _extendedAvailType.GetConstructor(new[] { typeof(string) })
                                  ?? throw new InvalidOperationException("ScriptCommandExtendedAvail(string) ctor not found.");
        }

        /// <summary>
        /// Defines both the ScriptCommand-derived class and its matching _avail class.
        /// </summary>
        public void DefineCommandType(ParsedExtension extension, ParsedComponent cmd, ModuleBuilder moduleBuilder)
        {
            // 1) Generate the ScriptCommand type
            var typeName = SanitizeClassName(cmd.UniqueId);
            var tb = moduleBuilder.DefineType(
                typeName,
                TypeAttributes.Public | TypeAttributes.Class,
                _scriptCommandType);

            // [Regeneration] and [Transaction] attributes
            var regenCtor = typeof(RegenerationAttribute)
                .GetConstructor(new[] { typeof(RegenerationOption) })!;
            tb.SetCustomAttribute(new CustomAttributeBuilder(regenCtor, new object[] { RegenerationOption.Manual }));

            var transCtor = typeof(TransactionAttribute)
                .GetConstructor(new[] { typeof(TransactionMode) })!;
            tb.SetCustomAttribute(new CustomAttributeBuilder(transCtor, new object[] { TransactionMode.Manual }));

            // Parameterless ctor
            var ctor = tb.DefineConstructor(
                MethodAttributes.Public,
                CallingConventions.Standard,
                Type.EmptyTypes);
            var il = ctor.GetILGenerator();

            il.Emit(OpCodes.Ldarg_0);

            // Prepare the 13 args
            string scriptPath = cmd.ScriptPath ?? string.Empty;
            string configPath = cmd.ScriptPath ?? string.Empty;
            string searchPaths = string.Join(";", new[]
            {
                Path.GetDirectoryName(cmd.ScriptPath),
                Path.Combine(extension.Directory, "lib"),
                Path.Combine(extension.Directory, "..", "..", "pyrevitlib"),
                Path.Combine(extension.Directory, "..", "..", "site-packages")
            });
            string[] args = {
                scriptPath,
                configPath,
                searchPaths,
                "",
                "",
                cmd.Tooltip  ?? string.Empty,
                cmd.Name,
                Path.GetFileName(Path.GetDirectoryName(cmd.ScriptPath)),
                extension.Name,
                cmd.UniqueId,
                $"CustomCtrl_%{extension.Name}%{Path.GetFileName(Path.GetDirectoryName(cmd.ScriptPath))}%{cmd.Name}",
                "(zero-doc)",
                "{\"clean\":false,\"persistent\":false,\"full_frame\":false}"
            };
            foreach (var a in args) il.Emit(OpCodes.Ldstr, a);

            il.Emit(OpCodes.Call, _scriptCommandCtor);
            il.Emit(OpCodes.Ret);

            tb.CreateType();

            // 2) Generate the matching _avail type
            DefineAvailabilityType(moduleBuilder, cmd);
        }

        private void DefineAvailabilityType(ModuleBuilder moduleBuilder, ParsedComponent cmd)
        {
            var availName = SanitizeClassName(cmd.UniqueId) + "_avail";
            var atb = moduleBuilder.DefineType(
                availName,
                TypeAttributes.Public | TypeAttributes.Class,
                _extendedAvailType);

            // Parameterless ctor for ExtendedAvail
            var ctor = atb.DefineConstructor(
                MethodAttributes.Public,
                CallingConventions.Standard,
                Type.EmptyTypes);
            var il = ctor.GetILGenerator();

            il.Emit(OpCodes.Ldarg_0);
            il.Emit(OpCodes.Ldstr, "(zero-doc)");
            il.Emit(OpCodes.Call, _extendedAvailCtor);
            il.Emit(OpCodes.Ret);

            atb.CreateType();
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
