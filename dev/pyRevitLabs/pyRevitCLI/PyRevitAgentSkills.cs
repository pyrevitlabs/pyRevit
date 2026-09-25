using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

using pyRevitLabs.PyRevit;

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
    }

    /// <summary>
    /// Loads the skills and the entry instructions the MCP server hands to agents. All LLM-facing
    /// guidance lives in markdown next to pyrevitlib, not in code.
    /// </summary>
    /// <remarks>
    /// Shipped skills live in <c>pyrevitlib/pyrevit/agent/skills</c> of the clone this CLI
    /// belongs to, or, for a standalone CLI install, of the first registered clone that has them. Skills in <c>%APPDATA%\pyRevit\agent\skills</c> are added, and replace a
    /// shipped skill of the same name, so a firm can add its own standards without touching the
    /// clone. The entry text is <c>INSTRUCTIONS.md</c> with <c>{skills}</c> replaced by the
    /// generated skill list, so adding a skill folder needs no code change.
    /// </remarks>
    internal static class PyRevitAgentSkills {
        public const string CoreSkill = "revit-scripting";
        private const string SkillFile = "SKILL.md";
        private const string InstructionsFile = "INSTRUCTIONS.md";
        private const int MaxParentLevels = 8;

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
            foreach (var (root, source) in new[] { (ShippedSkillsDir, "pyrevit"), (UserSkillsDir, "user") }) {
                if (root == null || !System.IO.Directory.Exists(root))
                    continue;
                foreach (var skillDir in System.IO.Directory.GetDirectories(root)) {
                    var skill = ReadSkill(skillDir, source);
                    if (skill != null)
                        skills[skill.Name] = skill;
                }
            }
            return skills.Values
                .OrderBy(skill => skill.Name == CoreSkill ? 0 : 1)
                .ThenBy(skill => skill.Name, StringComparer.OrdinalIgnoreCase)
                .ToList();
        }

        public static string Instructions(List<AgentSkill> skills) {
            var list = string.Join("\n", skills.Select(skill => $"- {skill.Name}: {skill.Description}"));
            var shipped = ShippedSkillsDir;
            var template = shipped != null && File.Exists(Path.Combine(shipped, InstructionsFile))
                ? File.ReadAllText(Path.Combine(shipped, InstructionsFile))
                : "pyRevit MCP server for Revit. Call get_context, then get_skill(\"" + CoreSkill + "\"), then the skill for your task.\n\nAvailable skills:\n{skills}\n";
            return template.Replace("{skills}", list.Length > 0 ? list : "(no skills found)");
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
            if (!path.StartsWith(root, StringComparison.OrdinalIgnoreCase) || !path.EndsWith(".md", StringComparison.OrdinalIgnoreCase))
                throw new AgentClientException("invalid_params", "'file' must be a markdown file inside the skill folder.");
            if (!File.Exists(path))
                throw new AgentClientException("skill_not_found", $"Skill '{skill.Name}' has no file '{file}'.");

            var text = File.ReadAllText(path);
            var others = System.IO.Directory.GetFiles(skill.Directory, "*.md", SearchOption.AllDirectories)
                .Select(other => other.Substring(root.Length).Replace('\\', '/'))
                .Where(other => !string.Equals(Path.GetFullPath(Path.Combine(skill.Directory, other)), path, StringComparison.OrdinalIgnoreCase))
                .ToList();
            if (others.Count > 0)
                text += "\n\n---\nMore files in this skill (get_skill with file=...): " + string.Join(", ", others);
            return text;
        }

        private static AgentSkill ReadSkill(string skillDir, string source) {
            var path = Path.Combine(skillDir, SkillFile);
            if (!File.Exists(path))
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

            return new AgentSkill {
                Name = frontMatter.TryGetValue("name", out var name) && name.Length > 0 ? name : Path.GetFileName(skillDir),
                Description = frontMatter.TryGetValue("description", out var description) ? description : string.Empty,
                Directory = skillDir,
                Source = source,
            };
        }
    }
}
