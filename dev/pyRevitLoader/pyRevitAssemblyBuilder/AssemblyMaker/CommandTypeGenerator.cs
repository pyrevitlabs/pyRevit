using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using Autodesk.Revit.Attributes;
using pyRevitExtensionParser;
using pyRevitAssemblyBuilder.SessionManager;
using static pyRevitExtensionParser.ExtensionParser;


namespace pyRevitAssemblyBuilder.AssemblyMaker
{
    /// <summary>
    /// Generates C# code for commands via Roslyn, plus availability classes.
    /// </summary>
    public class RoslynCommandTypeGenerator
    {
        // Cache the pyRevit root derived from DLL location
        // Uses marker-based detection (pyRevitfile or pyrevitlib directory)
        // for robustness against directory structure changes.
        private static readonly string _pyRevitRoot = GetPyRevitRoot();
        
        /// <summary>
        /// Finds the pyRevit root directory by searching upward for marker files/directories.
        /// Falls back to the original 4-level traversal if markers are not found.
        /// </summary>
        private static string GetPyRevitRoot()
        {
            var currentDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            // Search upward for pyRevit root using established markers
            while (!string.IsNullOrEmpty(currentDir))
            {
                var markerPath = Path.Combine(currentDir, Constants.PYREVIT_MARKER_FILE);
                var libDirPath = Path.Combine(currentDir, Constants.PYREVIT_LIB_DIR);
                
                if (File.Exists(markerPath) || Directory.Exists(libDirPath))
                    return currentDir;
                
                // Move to parent directory
                var parentDir = Path.GetDirectoryName(currentDir);
                if (parentDir == currentDir)
                    break; // Reached filesystem root
                currentDir = parentDir;
            }
            
            // Fallback to hardcoded traversal if markers not found
            var dllDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            return Path.GetFullPath(Path.Combine(dllDir, "..", "..", "..", ".."));
        }

        public string GenerateExtensionCode(ParsedExtension extension, string revitVersion, IEnumerable<ParsedExtension> libraryExtensions = null, bool rocketMode = false)
        {
            var sb = new StringBuilder();
            sb.AppendLine("#nullable disable");
            sb.AppendLine("using Autodesk.Revit.Attributes;");
            sb.AppendLine("using PyRevitLabs.PyRevit.Runtime;");
            sb.AppendLine();

            // Fix for #3140: Track emitted class names to prevent Roslyn CS0101
            // (duplicate type definition) which kills the entire extension assembly.
            // The legacy loader isolates failures per-command via try/except in
            // typemaker.make_bundle_types(); this HashSet provides equivalent safety.
            var emittedClassNames = new HashSet<string>(StringComparer.Ordinal);

            foreach (var cmd in extension.CollectCommandComponents())
            {
                string safeClassName = SanitizeClassName(cmd.UniqueId);

                if (!emittedClassNames.Add(safeClassName))
                {
                    // Duplicate — skip this command to avoid CS0101.
                    // Emit a comment in the generated .cs so the user can diagnose
                    // which script was dropped (the .cs file is saved alongside the DLL).
                    sb.AppendLine($"// WARNING [#3140]: Skipped duplicate class '{safeClassName}'");
                    sb.AppendLine($"//   Script: {cmd.ScriptPath ?? "(no script)"}");
                    sb.AppendLine($"//   UniqueId: {cmd.UniqueId}");
                    sb.AppendLine($"//   Two bundle directories produced the same UniqueId.");
                    sb.AppendLine($"//   Rename one directory to fix this.");
                    sb.AppendLine();
                    continue;
                }

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

                var searchPathsList = new List<string>();
                if (!string.IsNullOrEmpty(scriptDir))
                    searchPathsList.Add(scriptDir);
                
                // Add lib/ folders from component hierarchy (extension -> tab -> panel -> button)
                searchPathsList.AddRange(extension.CollectLibraryPaths(cmd));
                
                // Add binary paths from component hierarchy for module DLLs
                searchPathsList.AddRange(extension.CollectBinaryPaths(cmd));
                
                // Add all library extension directories
                if (libraryExtensions != null)
                {
                    var libExtList = libraryExtensions.ToList();
                    foreach (var libExt in libExtList)
                    {
                        if (!string.IsNullOrEmpty(libExt.Directory))
                            searchPathsList.Add(libExt.Directory);
                    }
                }
                
                // Add pyrevitlib/ and site-packages/ paths if pyRevitRoot is valid
                if (!string.IsNullOrEmpty(_pyRevitRoot))
                {
                    var pyRevitLibDir = Path.Combine(_pyRevitRoot, Constants.PYREVIT_LIB_DIR);
                    searchPathsList.Add(pyRevitLibDir);

                    var sitePackagesDir = Path.Combine(_pyRevitRoot, Constants.SITE_PACKAGES_DIR);
                    searchPathsList.Add(sitePackagesDir);
                }
                
                string searchPaths = string.Join(";", searchPathsList);
                string tooltip = cmd.Tooltip ?? string.Empty;
                string bundle = string.IsNullOrEmpty(scriptDir) ? string.Empty : Path.GetFileName(scriptDir);
                string extName = extension.Name;
                // Use the properly-built control ID from the component hierarchy
                string ctrlId = cmd.ControlId ?? $"CustomCtrl_%CustomCtrl_%{extName}%{bundle}%{cmd.Name}";
                
                // Build engine configs based on bundle configuration or script type
                string engineCfgs = CommandGenerationUtilities.BuildEngineConfigs(cmd, scriptPath, extension, rocketMode);
                
                // Get context from component - only use if explicitly defined
                string context = cmd.Context ?? string.Empty;
                bool hasExplicitContext = !string.IsNullOrEmpty(cmd.Context);
                
                string arguments = CommandGenerationUtilities.BuildCommandArguments(extension, cmd, revitVersion);

                // Get config script path - use ConfigScriptPath if different from ScriptPath, otherwise use ScriptPath
                string configScriptPath = cmd.ConfigScriptPath ?? scriptPath;
                
                // — Command class —
                sb.AppendLine("[Regeneration(RegenerationOption.Manual)]");
                sb.AppendLine("[Transaction(TransactionMode.Manual)]");
                sb.AppendLine($"public class {safeClassName} : ScriptCommand");
                sb.AppendLine("{");
                sb.AppendLine($"    public {safeClassName}() : base(");
                sb.AppendLine($"        @\"{EscapeForVerbatim(scriptPath)}\",");
                sb.AppendLine($"        @\"{EscapeForVerbatim(configScriptPath)}\",");  // configScriptPath - use actual config script if exists
                sb.AppendLine($"        @\"{EscapeForVerbatim(searchPaths)}\",");
                sb.AppendLine($"        @\"{EscapeForVerbatim(arguments)}\",");
                sb.AppendLine($"        \"\",");
                sb.AppendLine($"        @\"{EscapeForVerbatim(tooltip)}\",");
                sb.AppendLine($"        \"{Escape(cmd.DisplayName)}\",");  // Use DisplayName to match button's Revit API name for toggle_icon
                sb.AppendLine($"        \"{Escape(bundle)}\",");
                sb.AppendLine($"        \"{Escape(extName)}\",");
                sb.AppendLine($"        \"{cmd.UniqueId}\",");
                sb.AppendLine($"        \"{Escape(ctrlId)}\",");
                sb.AppendLine($"        \"{Escape(context)}\",");
                sb.AppendLine($"        \"{Escape(engineCfgs)}\"");
                sb.AppendLine("    )");
                sb.AppendLine("    {");
                sb.AppendLine("    }");
                sb.AppendLine("}");
                sb.AppendLine();

                // — Availability class — only create if context is explicitly defined
                if (hasExplicitContext)
                {
                    sb.AppendLine($"public class {safeClassName}_avail : ScriptCommandExtendedAvail");
                    sb.AppendLine("{");
                    sb.AppendLine($"    public {safeClassName}_avail() : base(\"{Escape(context)}\")");
                    sb.AppendLine("    {");
                    sb.AppendLine("    }");
                    sb.AppendLine("}");
                    sb.AppendLine();
                }
            }

            return sb.ToString();
        }

        private static string SanitizeClassName(string name)
        {
            var sb = new StringBuilder();
            foreach (char c in name)
                sb.Append(char.IsLetterOrDigit(c) ? c : '_');

            // Fix for #3107: C# identifiers cannot start with a digit.
            // The legacy loader used Reflection.Emit (IL-level) where leading digits
            // were valid. Roslyn compiles C# source, which requires a letter or '_'
            // as the first character. Prepend '_' to make it a valid identifier.
            if (sb.Length > 0 && char.IsDigit(sb[0]))
                sb.Insert(0, '_');

            return sb.ToString();
        }

        private static string EscapeForVerbatim(string str) =>
            (str ?? string.Empty).Replace("\"", "\"\"");

        private static string Escape(string str) =>
            (str ?? string.Empty)
                .Replace("\\", "\\\\")
                .Replace("\"", "\\\"");
    }

    public static class CommandGenerationUtilities
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
        
        /// <summary>
        /// Builds the engine configuration JSON string based on script type and bundle settings
        /// </summary>
        /// <param name="cmd">The command component to build configs for</param>
        /// <param name="scriptPath">Path to the script file</param>
        /// <param name="extension">The parent extension (for rocket mode compatibility check)</param>
        /// <param name="rocketMode">Whether rocket mode is enabled globally</param>
        public static string BuildEngineConfigs(ParsedComponent cmd, string scriptPath, ParsedExtension extension = null, bool rocketMode = false)
        {
            var configs = new Dictionary<string, object>();
            
            // Check if this is a Dynamo script
            bool isDynamoScript = scriptPath != null && 
                                scriptPath.EndsWith(".dyn", StringComparison.OrdinalIgnoreCase);

            // Determine clean engine setting:
            // - Script/bundle may force clean scope via Engine.Clean (__cleanengine__ / bundle.yaml).
            // - Rocket mode with a rocket-compatible extension reuses a cached engine (clean = false).
            // - Otherwise use a clean engine scope (clean = true).
            bool engineCleanFromMetadata = cmd.Engine != null && cmd.Engine.Clean;
            bool extensionRocketOk = extension != null && extension.RocketModeCompatible;
            bool useCleanEngine;
            if (engineCleanFromMetadata)
                useCleanEngine = true;
            else if (rocketMode && extensionRocketOk)
                useCleanEngine = false;
            else
                useCleanEngine = true;

            configs["clean"] = useCleanEngine;

            // Add engine type only when explicitly specified in metadata.
            // Do not force the default IronPython value into configs,
            // otherwise runtime shebang detection (#! python3) is bypassed.
            if (cmd.Engine?.HasTypeOverride == true)
            {
                configs["type"] = cmd.Engine.Type;
                configs["type_explicit"] = true;
            }
            
            if (isDynamoScript)
            {
                // Use EngineConfig.RequiresMainThread which already has the correct defaults.
                bool requiresMainThread = cmd.Engine?.RequiresMainThread ?? false;
                configs["automate"] = requiresMainThread;
                
                // Add Dynamo-specific settings
                if (!string.IsNullOrEmpty(cmd.Engine?.DynamoPath))
                    configs["dynamo_path"] = cmd.Engine.DynamoPath;
                    
                // dynamo_path_exec defaults to true if not specified
                configs["dynamo_path_exec"] = cmd.Engine?.DynamoPathExec ?? true;
                
                if (cmd.Engine?.DynamoPathCheckExisting != null)
                    configs["dynamo_path_check_existing"] = cmd.Engine.DynamoPathCheckExisting.Value;
                    
                if (cmd.Engine?.DynamoForceManualRun != null)
                    configs["dynamo_force_manual_run"] = cmd.Engine.DynamoForceManualRun.Value;
                    
                if (!string.IsNullOrEmpty(cmd.Engine?.DynamoModelNodesInfo))
                    configs["dynamo_model_nodes_info"] = cmd.Engine.DynamoModelNodesInfo;
            }
            else
            {
                // For non-Dynamo scripts (Python, C#, VB, Ruby, etc.)
                configs["full_frame"] = cmd.Engine?.FullFrame ?? false;
                configs["persistent"] = cmd.Engine?.Persistent ?? false;
                
                // Include mainthread setting if specified (for Python scripts that need main thread)
                if (cmd.Engine?.MainThread != null)
                    configs["mainthread"] = cmd.Engine.MainThread.Value;
            }
            
            // Build JSON string manually to ensure proper formatting
            var jsonParts = new List<string>();
            foreach (var kvp in configs)
            {
                if (kvp.Value is bool boolValue)
                    jsonParts.Add($"\"{kvp.Key}\":{boolValue.ToString().ToLower()}");
                else if (kvp.Value is string stringValue)
                    jsonParts.Add($"\"{kvp.Key}\":\"{stringValue.Replace("\\", "\\\\").Replace("\"", "\\\"")}\"");
                else
                    jsonParts.Add($"\"{kvp.Key}\":{kvp.Value}");
            }
            
            return "{" + string.Join(",", jsonParts) + "}";
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

            var validPaths = searchPaths.Where(p => !string.IsNullOrEmpty(p)).ToList();
            foreach (var path in validPaths)
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
