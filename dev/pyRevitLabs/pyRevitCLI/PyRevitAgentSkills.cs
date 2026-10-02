using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;

using pyRevitLabs.PyRevit;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI {
    /// <summary>
    /// A skill: task guidance for agents, stored as <c>&lt;name&gt;/SKILL.md</c> with
    /// <c>name</c> and <c>description</c> front matter (the Agent Skills layout).
    /// </summary>
    internal sealed class AgentSkill {
        public string Name { get; set; }
        public string Description { get; set; }
        public string Directory { get; set; }
        public string Source { get; set; }
        public string Hash { get; set; }
    }

    /// <summary>
    /// Loads the skills and the entry instructions the MCP server hands to agents. All LLM-facing
    /// guidance lives in markdown next to pyrevitlib, not in code.
    /// </summary>
    /// <remarks>
    /// Shipped skills live in <c>pyrevitlib/pyrevit/agent/skills</c> of the clone this CLI
    /// belongs to, or, for a standalone CLI install, of the first registered clone that has them. When enabled, skills in <c>%APPDATA%\pyRevit\agent\skills</c> are added so a firm
    /// can add its own standards without touching the clone; a user skill with the same name as a
    /// shipped skill is ignored, and an unreadable one is skipped. The entry text is <c>INSTRUCTIONS.md</c> with <c>{skills}</c> replaced by the
    /// generated skill list, so adding a skill folder needs no code change.
    /// </remarks>
    internal static class PyRevitAgentSkills {
        public const string CoreSkill = "revit-scripting";
        private const string SkillFile = "SKILL.md";
        private const string InstructionsFile = "INSTRUCTIONS.md";
        private const int MaxParentLevels = 8;
        private const int MaxSkillBytes = 128 * 1024;
        private const int MaxUserDescriptionChars = 240;
        private static readonly Regex SkillName = new Regex("^[a-z0-9][a-z0-9-]{0,63}$", RegexOptions.Compiled);

        public static string UserSkillsDir => Path.Combine(PyRevitAgentClient.AgentDir, "skills");

        public static string ShippedSkillsDir {
            get {
                var directory = new DirectoryInfo(AppContext.BaseDirectory);
                for (var level = 0; directory != null && level < MaxParentLevels; level++, directory = directory.Parent) {
                    var candidate = SkillsDirIn(directory.FullName);
                    if (System.IO.Directory.Exists(candidate))
                        return candidate;
                }

                try {
                    return PyRevitClones.GetRegisteredClones()
                        .Select(clone => SkillsDirIn(clone.ClonePath))
                        .FirstOrDefault(System.IO.Directory.Exists);
                }
                catch (Exception) {
                    return null;
                }
            }
        }

        private static string SkillsDirIn(string root) {
            return Path.Combine(root, "pyrevitlib", "pyrevit", "agent", "skills");
        }

        public static List<AgentSkill> Load() {
            var skills = new Dictionary<string, AgentSkill>(StringComparer.OrdinalIgnoreCase);
            foreach (var (root, source) in SkillRoots()) {
                if (root == null || !System.IO.Directory.Exists(root))
                    continue;
                string[] skillDirs;
                try {
                    skillDirs = System.IO.Directory.GetDirectories(root);
                }
                catch (Exception ex) when (ex is IOException || ex is UnauthorizedAccessException) {
                    continue;
                }
                foreach (var skillDir in skillDirs.OrderBy(path => path, StringComparer.OrdinalIgnoreCase)) {
                    AgentSkill skill;
                    try {
                        skill = ReadSkill(skillDir, source);
                    }
                    catch (Exception ex) when (ex is IOException || ex is UnauthorizedAccessException) {
                        continue;
                    }
                    if (skill != null && !skills.ContainsKey(skill.Name))
                        skills[skill.Name] = skill;
                }
            }
            return skills.Values
                .OrderBy(skill => skill.Name == CoreSkill ? 0 : 1)
                .ThenBy(skill => skill.Name, StringComparer.OrdinalIgnoreCase)
                .ToList();
        }

        public static string Instructions(List<AgentSkill> skills) {
            var list = string.Join("\n", skills.Select(skill => $"- {skill.Name} ({skill.Source}, sha256:{skill.Hash})"));
            var shipped = ShippedSkillsDir;
            var template = shipped != null && File.Exists(Path.Combine(shipped, InstructionsFile))
                ? File.ReadAllText(Path.Combine(shipped, InstructionsFile))
                : "pyRevit MCP server for Revit. Call get_context, then get_skill(\"" + CoreSkill + "\"), then the skill for your task.\n\nAvailable skills:\n{skills}\n";
            return template.Replace("{skills}", list.Length > 0 ? list : "(no skills found)");
        }

        /// <summary>
        /// Returns bounded, attributable metadata for the skills available to this MCP server.
        /// </summary>
        public static JArray List() {
            return new JArray(Load().Select(skill => new JObject {
                ["name"] = skill.Name,
                ["description"] = skill.Description,
                ["source"] = skill.Source,
                ["sha256"] = skill.Hash,
            }));
        }

        /// <summary>
        /// Returns a skill's SKILL.md, or another markdown file inside the same skill folder.
        /// </summary>
        /// <exception cref="AgentClientException">
        /// <c>skill_not_found</c> for an unknown skill, <c>invalid_params</c> for a file outside
        /// the skill folder or not markdown.
        /// </exception>
        public static string Read(string name, string file) {
            var skill = Load().FirstOrDefault(candidate => string.Equals(candidate.Name, name, StringComparison.OrdinalIgnoreCase))
                ?? throw new AgentClientException(
                    "skill_not_found",
                    $"No skill named '{name}'. Available: {string.Join(", ", Load().Select(candidate => candidate.Name))}.");

            var root = Path.GetFullPath(skill.Directory) + Path.DirectorySeparatorChar;
            var path = Path.GetFullPath(Path.Combine(skill.Directory, string.IsNullOrWhiteSpace(file) ? SkillFile : file));
            if (!path.StartsWith(root, StringComparison.OrdinalIgnoreCase) || !path.EndsWith(".md", StringComparison.OrdinalIgnoreCase) || IsReparsePoint(path))
                throw new AgentClientException("invalid_params", "'file' must be a markdown file inside the skill folder.");
            if (!File.Exists(path))
                throw new AgentClientException("skill_not_found", $"Skill '{skill.Name}' has no file '{file}'.");
            if (new FileInfo(path).Length > MaxSkillBytes)
                throw new AgentClientException("invalid_params", $"Skill file '{file}' exceeds the {MaxSkillBytes / 1024} KiB limit.");

            var text = File.ReadAllText(path);
            var others = MarkdownFiles(skill.Directory)
                .Select(other => other.Substring(root.Length).Replace('\\', '/'))
                .Where(other => !string.Equals(Path.GetFullPath(Path.Combine(skill.Directory, other)), path, StringComparison.OrdinalIgnoreCase))
                .ToList();
            if (others.Count > 0)
                text += "\n\n---\nMore files in this skill (get_skill with file=...): " + string.Join(", ", others);
            return text;
        }

        private static AgentSkill ReadSkill(string skillDir, string source) {
            var path = Path.Combine(skillDir, SkillFile);
            if (IsReparsePoint(skillDir) || !File.Exists(path) || new FileInfo(path).Length > MaxSkillBytes)
                return null;

            var lines = File.ReadAllLines(path);
            var frontMatter = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            if (lines.Length > 0 && lines[0].Trim() == "---") {
                for (var index = 1; index < lines.Length && lines[index].Trim() != "---"; index++) {
                    var separator = lines[index].IndexOf(':');
                    if (separator > 0)
                        frontMatter[lines[index].Substring(0, separator).Trim()] = lines[index].Substring(separator + 1).Trim();
                }
            }

            var name = frontMatter.TryGetValue("name", out var declaredName) && declaredName.Length > 0 ? declaredName : Path.GetFileName(skillDir);
            if (!SkillName.IsMatch(name))
                return null;
            var description = frontMatter.TryGetValue("description", out var declaredDescription) ? declaredDescription : string.Empty;
            if (source == "user" && description.Length > MaxUserDescriptionChars)
                description = description.Substring(0, MaxUserDescriptionChars - 3) + "...";
            return new AgentSkill {
                Name = name,
                Description = description,
                Directory = skillDir,
                Source = source,
                Hash = Hash(path),
            };
        }

        private static IEnumerable<(string Root, string Source)> SkillRoots() {
            yield return (ShippedSkillsDir, "pyrevit");
            if (PyRevitConfigs.GetAgentUserSkillsEnabled())
                yield return (UserSkillsDir, "user");
        }

        private static IEnumerable<string> MarkdownFiles(string root) {
            foreach (var file in System.IO.Directory.GetFiles(root, "*.md"))
                if (!IsReparsePoint(file))
                    yield return file;
            foreach (var directory in System.IO.Directory.GetDirectories(root)) {
                if (IsReparsePoint(directory))
                    continue;
                foreach (var file in MarkdownFiles(directory))
                    yield return file;
            }
        }

        private static bool IsReparsePoint(string path) {
            return (File.Exists(path) || System.IO.Directory.Exists(path))
                && (File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0;
        }

        private static string Hash(string path) {
            using (var sha256 = SHA256.Create())
            using (var stream = File.OpenRead(path))
                return BitConverter.ToString(sha256.ComputeHash(stream)).Replace("-", string.Empty).ToLowerInvariant();
        }
    }
}
