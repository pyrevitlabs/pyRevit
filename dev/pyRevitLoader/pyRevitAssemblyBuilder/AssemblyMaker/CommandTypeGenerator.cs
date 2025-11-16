using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Reflection;
using System.Reflection.Emit;
using Autodesk.Revit.Attributes;
using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;
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
        public string GenerateExtensionCode(ParsedExtension extension, string revitVersion, IEnumerable<ParsedExtension> libraryExtensions = null)
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
                
                // Build search paths matching Python's behavior:
                // 1. Script's own directory
                // 2. Component hierarchy lib/ folders (button -> panel -> tab -> extension)
                // 3. Library extensions
                // 4. pyrevitlib/
                // 5. site-packages/
                string scriptDir = string.IsNullOrEmpty(cmd.ScriptPath)
                    ? string.Empty
                    : Path.GetDirectoryName(cmd.ScriptPath);

                var searchPathsList = new System.Collections.Generic.List<string>();
                if (!string.IsNullOrEmpty(scriptDir))
                    searchPathsList.Add(scriptDir);
                
                // Add lib/ folders from component hierarchy (extension -> tab -> panel -> button)
                searchPathsList.AddRange(extension.CollectLibraryPaths(cmd));
                
                // Add binary paths from component hierarchy for module DLLs
                searchPathsList.AddRange(extension.CollectBinaryPaths(cmd));
                
                // Add all library extension directories
                if (libraryExtensions != null)
                {
                    foreach (var libExt in libraryExtensions)
                    {
                        if (!string.IsNullOrEmpty(libExt.Directory))
                            searchPathsList.Add(libExt.Directory);
                    }
                }
                
                searchPathsList.Add(Path.Combine(extension.Directory, "..", "..", "pyrevitlib"));
                searchPathsList.Add(Path.Combine(extension.Directory, "..", "..", "site-packages"));
                
                string searchPaths = string.Join(";", searchPathsList);
                string tooltip = cmd.Tooltip ?? string.Empty;
                string bundle = string.IsNullOrEmpty(scriptDir) ? string.Empty : Path.GetFileName(scriptDir);
                string extName = extension.Name;
                string ctrlId = $"CustomCtrl_%{extName}%{bundle}%{cmd.Name}";
                string engineCfgs = "{\"clean\": false, \"persistent\": false, \"full_frame\": false}";
                
                // Get context from component, default to "(zero-doc)" if not specified
                string context = !string.IsNullOrEmpty(cmd.Context) ? $"({cmd.Context})" : "(zero-doc)";
                
                string arguments = CommandGenerationUtilities.BuildCommandArguments(extension, cmd, revitVersion);

                // — Command class —
                sb.AppendLine("[Regeneration(RegenerationOption.Manual)]");
                sb.AppendLine("[Transaction(TransactionMode.Manual)]");
                sb.AppendLine($"public class {safeClassName} : ScriptCommand");
                sb.AppendLine("{");
                sb.AppendLine($"    public {safeClassName}() : base(");
                sb.AppendLine($"        @\"{EscapeForVerbatim(scriptPath)}\",");
                sb.AppendLine($"        @\"{EscapeForVerbatim(scriptPath)}\",");
                sb.AppendLine($"        @\"{EscapeForVerbatim(searchPaths)}\",");
                sb.AppendLine($"        @\"{EscapeForVerbatim(arguments)}\",");
                sb.AppendLine($"        \"\",");
                sb.AppendLine($"        @\"{EscapeForVerbatim(tooltip)}\",");
                sb.AppendLine($"        \"{Escape(cmd.Name)}\",");
                sb.AppendLine($"        \"{Escape(bundle)}\",");
                sb.AppendLine($"        \"{Escape(extName)}\",");
                sb.AppendLine($"        \"{cmd.UniqueId}\",");
                sb.AppendLine($"        \"{Escape(ctrlId)}\",");
                sb.AppendLine($"        \"{context}\",");
                sb.AppendLine($"        \"{Escape(engineCfgs)}\"");
                sb.AppendLine("    )");
                sb.AppendLine("    {");
                sb.AppendLine("    }");
                sb.AppendLine("}");
                sb.AppendLine();

                // — Availability class —
                sb.AppendLine($"public class {safeClassName}_avail : ScriptCommandExtendedAvail");
                sb.AppendLine("{");
                sb.AppendLine($"    public {safeClassName}_avail() : base(\"{context}\")");
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
        public void DefineCommandType(ParsedExtension extension, ParsedComponent cmd, ModuleBuilder moduleBuilder, IEnumerable<ParsedExtension> libraryExtensions = null, string revitVersion = null)
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

            // Prepare the 13 args - ensure all values are non-null for Ldstr
            string scriptPath = cmd.ScriptPath ?? string.Empty;
            string configPath = cmd.ScriptPath ?? string.Empty;
            
            // Build search paths matching Python's behavior:
            // 1. Script's own directory
            // 2. Component hierarchy lib/ folders (button -> panel -> tab -> extension)
            // 3. Library extensions
            // 4. pyrevitlib/
            // 5. site-packages/
            string scriptDir = string.IsNullOrEmpty(cmd.ScriptPath) ? string.Empty : (Path.GetDirectoryName(cmd.ScriptPath) ?? string.Empty);
            string extensionDir = extension.Directory ?? string.Empty;
            
            var searchPathsList = new System.Collections.Generic.List<string>
            {
                scriptDir
            };
            
            // Add lib/ folders from component hierarchy (extension -> tab -> panel -> button)
            searchPathsList.AddRange(extension.CollectLibraryPaths(cmd));
            
            // Add all library extension directories
            if (libraryExtensions != null)
            {
                foreach (var libExt in libraryExtensions)
                {
                    if (!string.IsNullOrEmpty(libExt.Directory))
                        searchPathsList.Add(libExt.Directory);
                }
            }
            
            searchPathsList.Add(Path.Combine(extensionDir, "..", "..", "pyrevitlib"));
            searchPathsList.Add(Path.Combine(extensionDir, "..", "..", "site-packages"));
            
            string searchPaths = string.Join(";", searchPathsList.Where(p => !string.IsNullOrEmpty(p)));
            
            // Get context from component, default to "(zero-doc)" if not specified
            string context = !string.IsNullOrEmpty(cmd.Context) ? $"({cmd.Context})" : "(zero-doc)";
            
            // Get bundle name (parent directory of script)
            string bundleName = string.IsNullOrEmpty(scriptDir) ? string.Empty : (Path.GetFileName(scriptDir) ?? string.Empty);
            
            string arguments = CommandGenerationUtilities.BuildCommandArguments(extension, cmd, revitVersion);
            
            string[] args = {
                scriptPath,
                configPath,
                searchPaths,
                arguments,  // arg 4 - hyperlink for URL buttons
                string.Empty,  // arg 5
                cmd.Tooltip ?? string.Empty,
                cmd.Name ?? string.Empty,
                bundleName,
                extension.Name ?? string.Empty,
                cmd.UniqueId ?? string.Empty,
                $"CustomCtrl_%{extension.Name ?? string.Empty}%{bundleName}%{cmd.Name ?? string.Empty}",
                context,
                "{\"clean\":false,\"persistent\":false,\"full_frame\":false}"
            };
            
            // Emit all string arguments - they should all be non-null now
            foreach (var a in args) il.Emit(OpCodes.Ldstr, a ?? string.Empty);

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

            // Get context from component, default to "(zero-doc)" if not specified
            string context = !string.IsNullOrEmpty(cmd.Context) ? $"({cmd.Context})" : "(zero-doc)";

            // Parameterless ctor for ExtendedAvail
            var ctor = atb.DefineConstructor(
                MethodAttributes.Public,
                CallingConventions.Standard,
                Type.EmptyTypes);
            var il = ctor.GetILGenerator();

            il.Emit(OpCodes.Ldarg_0);
            il.Emit(OpCodes.Ldstr, context);
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

    internal static class CommandGenerationUtilities
    {
        public static string BuildCommandArguments(ParsedExtension extension, ParsedComponent component, string revitVersion)
        {
            if (component == null)
                return string.Empty;

            if (component.Type == CommandComponentType.UrlButton && !string.IsNullOrEmpty(component.Hyperlink))
                return component.Hyperlink;

            if (component.Type == CommandComponentType.InvokeButton)
            {
                var assemblyPath = ResolveInvokeAssemblyPath(extension, component, revitVersion);
                if (string.IsNullOrEmpty(component.CommandClass))
                    return assemblyPath;

                return $"{assemblyPath}::{component.CommandClass}";
            }

            return string.Empty;
        }

        public static string ResolveInvokeAssemblyPath(ParsedExtension extension, ParsedComponent component, string revitVersion)
        {
            if (component == null)
                throw new ArgumentNullException(nameof(component));

            if (string.IsNullOrWhiteSpace(component.TargetAssembly))
                throw new InvalidOperationException($"Invoke button '{component.DisplayName}' must define an 'assembly' entry in bundle.yaml.");

            var assemblyValue = component.TargetAssembly.Trim();

            if (Path.IsPathRooted(assemblyValue) && File.Exists(assemblyValue))
                return Path.GetFullPath(assemblyValue);

            var baseFileName = assemblyValue;
            var includesDirectories = assemblyValue.Contains(Path.DirectorySeparatorChar) || assemblyValue.Contains(Path.AltDirectorySeparatorChar);

            if (!assemblyValue.EndsWith(".dll", StringComparison.OrdinalIgnoreCase))
                baseFileName += ".dll";

            var candidateNames = new List<string>();
            if (!string.IsNullOrWhiteSpace(revitVersion))
            {
                var name = Path.GetFileNameWithoutExtension(baseFileName);
                var ext = Path.GetExtension(baseFileName);
                candidateNames.Add($"{name}_{revitVersion}{ext}");
            }
            candidateNames.Add(Path.GetFileName(baseFileName));

            if (!Path.IsPathRooted(assemblyValue) && includesDirectories && !string.IsNullOrEmpty(component.Directory))
            {
                var relativePath = Path.GetFullPath(Path.Combine(component.Directory, assemblyValue));
                if (File.Exists(relativePath))
                    return relativePath;
            }

            var searchPaths = new List<string>();
            if (extension != null)
                searchPaths.AddRange(extension.CollectBinaryPaths(component));
            else if (!string.IsNullOrEmpty(component.Directory))
                searchPaths.Add(component.Directory);

            if (!string.IsNullOrEmpty(extension?.Directory) && !searchPaths.Contains(extension.Directory))
                searchPaths.Add(extension.Directory);

            foreach (var path in searchPaths.Where(p => !string.IsNullOrEmpty(p)))
            {
                foreach (var candidate in candidateNames)
                {
                    var candidatePath = Path.Combine(path, candidate);
                    if (File.Exists(candidatePath))
                        return candidatePath;
                }

                if (!Path.IsPathRooted(assemblyValue))
                {
                    var fallback = Path.Combine(path, assemblyValue);
                    if (File.Exists(fallback))
                        return fallback;
                }
            }

            throw new FileNotFoundException($"Invoke button '{component.DisplayName}' could not locate assembly '{assemblyValue}'.");
        }
    }
}
