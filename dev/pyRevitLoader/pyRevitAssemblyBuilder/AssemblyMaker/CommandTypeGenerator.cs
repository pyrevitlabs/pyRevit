using System;
using System.IO;
using System.Text;
using System.Linq;
using pyRevitAssemblyBuilder.SessionManager;
using Autodesk.Revit.Attributes;

namespace pyRevitAssemblyBuilder.AssemblyMaker
{
    public class CommandTypeGenerator
    {
        public string GenerateExtensionCode(WrappedExtension extension)
        {
            var sb = new StringBuilder();
            sb.AppendLine("#nullable disable");
            sb.AppendLine("using Autodesk.Revit.Attributes;");
            sb.AppendLine("using PyRevitLabs.PyRevit.Runtime;");
            foreach (var cmd in extension.GetAllCommands())
            {
                // Replace invalid characters with underscores for valid C# identifiers
                string safeClassName = SanitizeClassName(cmd.UniqueId);
                string originalUniqueName = cmd.UniqueId;
                string scriptPath = cmd.ScriptPath;
                string searchPaths = string.Join(";", new[] {
                    Path.GetDirectoryName(cmd.ScriptPath),
                    Path.Combine(extension.Directory, "lib"),
                    Path.Combine(extension.Directory, "..", "..", "pyrevitlib"),
                    Path.Combine(extension.Directory, "..", "..", "site-packages")
                });
                string tooltip = cmd.Tooltip ?? "";
                string name = cmd.Name;
                string bundle = Path.GetFileName(Path.GetDirectoryName(cmd.ScriptPath));
                string extName = extension.Name;
                string ctrlId = $"CustomCtrl_%{extName}%{bundle}%{name}";
                string engineCfgs = @"{""clean"": false, ""persistent"": false, ""full_frame"": false}";
                sb.AppendLine();
                sb.AppendLine("[Regeneration(RegenerationOption.Manual)]");
                sb.AppendLine("[Transaction(TransactionMode.Manual)]");
                sb.AppendLine($"public class {safeClassName} : ScriptCommand");
                sb.AppendLine("{");
                sb.AppendLine($"    public {safeClassName}()");
                sb.AppendLine("        : base(");
                sb.AppendLine($"            @\"{Escape(scriptPath)}\",");
                sb.AppendLine($"            @\"{Escape(scriptPath)}\",");
                sb.AppendLine($"            @\"{Escape(searchPaths)}\",");
                sb.AppendLine("            \"\",");
                sb.AppendLine("            \"\",");
                sb.AppendLine($"            @\"{Escape(tooltip)}\",");
                sb.AppendLine($"            \"{Escape(name)}\",");
                sb.AppendLine($"            \"{Escape(bundle)}\",");
                sb.AppendLine($"            \"{Escape(extName)}\",");
                sb.AppendLine($"            \"{originalUniqueName}\",");
                sb.AppendLine($"            \"{Escape(ctrlId)}\",");
                sb.AppendLine("            \"(zero-doc)\",");
                sb.AppendLine($"            @\"{EscapeJsonForVerbatimString(engineCfgs)}\"");
                sb.AppendLine("        )");
                sb.AppendLine("    {");
                sb.AppendLine("    }");
                sb.AppendLine("}");
            }
            return sb.ToString();
        }

        private static string SanitizeClassName(string name)
        {
            var sb = new StringBuilder();
            foreach (char c in name)
            {
                sb.Append(char.IsLetterOrDigit(c) ? c : '_');
            }
            return sb.ToString();
        }

        private static string Escape(string str)
        {
            return str?
                .Replace("\"", "\"\"") // for verbatim strings
                .Replace("\r", "")
                .Replace("\n", "\\n")
                ?? "";
        }

        private static string EscapeJsonForVerbatimString(string jsonStr)
        {
            // This method specifically handles JSON strings in verbatim string literals
            // It properly escapes quotes by doubling them
            if (string.IsNullOrEmpty(jsonStr))
                return "";

            return jsonStr.Replace("\"", "\"\"");
        }
    }
}