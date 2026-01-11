using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
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
                
                searchPathsList.Add(Path.Combine(extension.Directory, "..", "..", "pyrevitlib"));
                searchPathsList.Add(Path.Combine(extension.Directory, "..", "..", "site-packages"));
                
                string searchPaths = string.Join(";", searchPathsList);
                string tooltip = cmd.Tooltip ?? string.Empty;
                string bundle = string.IsNullOrEmpty(scriptDir) ? string.Empty : Path.GetFileName(scriptDir);
                string extName = extension.Name;
                // Use the properly-built control ID from the component hierarchy
                string ctrlId = cmd.ControlId ?? $"CustomCtrl_%CustomCtrl_%{extName}%{bundle}%{cmd.Name}";
                
                // Build engine configs based on bundle configuration or script type
                string engineCfgs = CommandGenerationUtilities.BuildEngineConfigs(cmd, scriptPath);
                
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
                sb.AppendLine($"        \"{context}\",");
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
                    sb.AppendLine($"    public {safeClassName}_avail() : base(\"{context}\")");
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
            return sb.ToString();
        }

        private static string EscapeForVerbatim(string str) =>
            (str ?? string.Empty).Replace("\"", "\"\"");

        private static string Escape(string str) =>
            (str ?? string.Empty)
                .Replace("\\", "\\\\")
                .Replace("\"", "\\\"");
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
        
        /// <summary>
        /// Builds the engine configuration JSON string based on script type and bundle settings
        /// </summary>
        public static string BuildEngineConfigs(ParsedComponent cmd, string scriptPath)
        {
            var configs = new Dictionary<string, object>();
            
            // Check if this is a Dynamo script
            bool isDynamoScript = scriptPath != null && 
                                scriptPath.EndsWith(".dyn", StringComparison.OrdinalIgnoreCase);
            
            // Core engine settings (apply to all script types)
            configs["clean"] = cmd.Engine?.Clean ?? false;
            
            if (isDynamoScript)
            {
                // For Dynamo scripts, use appropriate settings
                // Use automate or mainthread setting (automate is Dynamo-specific synonym)
                bool requiresMainThread = (cmd.Engine?.MainThread ?? false) || (cmd.Engine?.Automate ?? true);
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
