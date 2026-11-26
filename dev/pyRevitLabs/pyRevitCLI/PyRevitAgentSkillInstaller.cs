using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

using pyRevitLabs.Common;

namespace pyRevitCLI {
    internal enum SkillState {
        Installed,
        Updated,
        Current,
        Stale,
        Edited,
        Missing,
        Foreign,
        Removed,
        Failed,
    }

    internal static class SkillStateText {
        /// <summary>
        /// The lowercase word printed for a state; the only place a state becomes text.
        /// </summary>
        public static string Label(this SkillState state) {
            return state.ToString().ToLowerInvariant();
        }
    }

    /// <summary>
    /// One skill in one skills folder: what <c>agent skills install|status|uninstall</c> found or did.
    /// </summary>
    internal sealed class SkillAction {
        public string Target { get; set; }
        public string Skill { get; set; }
        public SkillState State { get; set; }
        public string Folder { get; set; }
    }

    /// <summary>
    /// The outcome of an install, status or uninstall run, with the warnings to show the user.
    /// </summary>
    internal sealed class SkillsReport {
        public List<SkillAction> Actions { get; } = new List<SkillAction>();
        public List<string> Warnings { get; } = new List<string>();
    }

    /// <summary>
    /// Copies the shipped agent skills into the skill folders other coding agents read, and reports
    /// or removes those copies.
    /// </summary>
    /// <remarks>
    /// Only skills shipped with pyRevit are copied, never user skills or <c>INSTRUCTIONS.md</c>. Each copy
    /// carries a <c>.pyrevit-skill.json</c> marker; a folder is pyRevit-owned only while its content
    /// still matches the marker.
    /// Invariants: a folder without a valid marker is never overwritten, replaced or deleted; an owned
    /// folder that was edited or holds extra files is replaced or removed only with <c>force</c>, which
    /// names the extra files first; nothing is written or deleted through a link; every path stays inside
    /// the skills folder. One skill that cannot be handled is reported as <c>failed</c> or <c>foreign</c>
    /// and the run goes on.
    /// Installed copies are guidance, not policy: they cannot change host policy.
    /// </remarks>
    internal static class PyRevitAgentSkillInstaller {
        public const string DefaultTarget = "agents";
        public const string DefaultScope = "project";
        public const int MaxDescriptionChars = 240;
        private const string NamePrefix = "pyrevit-";

        private sealed class Inspection {
            public SkillState State { get; set; }
            public List<string> Extras { get; set; } = new List<string>();
            public string Note { get; set; }
        }

        private sealed class Located {
            public string Name { get; set; }
            public string Folder { get; set; }
            public Inspection Inspection { get; set; }
            public string PlainFolder { get; set; }
            public bool PrefixTried { get; set; }
        }

        /// <summary>
        /// Installs the shipped skills into the skills folder of each target.
        /// </summary>
        /// <remarks>
        /// Idempotent: a current copy is reported and not rewritten, a stale owned copy is refreshed. A folder
        /// without the marker is skipped with a warning, or the skill is installed as
        /// <c>pyrevit-&lt;name&gt;</c> with <see cref="SkillOptions.Prefix"/>. An existing owned prefixed copy is
        /// refreshed in place when the plain name is free. <see cref="SkillOptions.Force"/> replaces an owned
        /// copy that was edited, removing any extra files in it after naming them in a warning.
        /// </remarks>
        /// <exception cref="PyRevitException">
        /// The shipped skills are missing or have a file over the limit, or a link is on the way to a skills folder.
        /// </exception>
        public static SkillsReport Install(SkillContext context, SkillOptions options) {
            var report = new SkillsReport();
            var shipped = LoadShipped(context.ShippedDir, report);
            foreach (var destination in context.Destinations) {
                PrepareSkillsDir(context, destination, create: true);
                SkillFiles.SweepTemp(destination.SkillsDir, restore: true, report.Warnings);
                foreach (var skill in shipped)
                    report.Actions.Add(InstallOne(destination, skill, options, report));
            }
            return report;
        }

        /// <summary>
        /// Compares the copies in each target's skills folder with the shipped skills.
        /// </summary>
        /// <remarks>
        /// States: <c>current</c>, <c>stale</c> (shipped skill changed), <c>edited</c> (content differs from the
        /// marker or has extra files), <c>missing</c>, <c>foreign</c> (a folder pyRevit did not write holds the
        /// name). Also warns when one client would read the same pyRevit-owned skill from several folders.
        /// Read-only.
        /// </remarks>
        public static SkillsReport Status(SkillContext context) {
            var report = new SkillsReport();
            var shipped = LoadShipped(context.ShippedDir, report);
            foreach (var destination in context.Destinations) {
                var exists = PrepareSkillsDir(context, destination, create: false);
                foreach (var skill in shipped) {
                    var located = exists ? Locate(destination, skill, prefixOnClash: true) : PlainMissing(destination, skill);
                    if (located.PrefixTried && located.Inspection.State == SkillState.Missing)
                        located = Locate(destination, skill, prefixOnClash: false);
                    if (located.Inspection.Note != null)
                        report.Warnings.Add($"{located.Folder}: {located.Inspection.Note}.");
                    if (located.Inspection.State == SkillState.Edited && located.Inspection.Extras.Count > 0)
                        report.Warnings.Add($"{located.Folder} holds files pyRevit did not install{Describe(located.Inspection.Extras, null)}.");
                    report.Actions.Add(new SkillAction { Target = destination.Label, Skill = skill.Name, State = located.Inspection.State, Folder = located.Folder });
                    if (IsOwned(located.Inspection.State))
                        WarnLongDescription(located.Folder, report.Warnings, "Skill");
                }
            }
            SkillTargets.WarnOverlaps(context, report.Warnings);
            return report;
        }

        /// <summary>
        /// Removes the pyRevit-owned skill folders from each target's skills folder.
        /// </summary>
        /// <param name="context">The shipped skills folder is not needed and may be null.</param>
        /// <param name="force">Also removes an owned folder that was edited or holds extra files, naming them first.</param>
        /// <remarks>
        /// Removes only folders whose marker matches their content, plus leftover <c>.pyrevit-tmp-*</c> folders.
        /// Never removes the skills folder, a folder without a valid marker or anything reached through a link.
        /// </remarks>
        public static SkillsReport Uninstall(SkillContext context, bool force) {
            var report = new SkillsReport();
            foreach (var destination in context.Destinations) {
                if (!PrepareSkillsDir(context, destination, create: false))
                    continue;
                SkillFiles.SweepTemp(destination.SkillsDir, restore: false, report.Warnings);
                foreach (var directory in Directory.GetDirectories(destination.SkillsDir).OrderBy(path => path, StringComparer.OrdinalIgnoreCase)) {
                    var name = Path.GetFileName(directory);
                    if (name.StartsWith(SkillFiles.TempPrefix, StringComparison.Ordinal) || SkillFiles.IsLink(directory))
                        continue;
                    var action = new SkillAction { Target = destination.Label, Skill = name, Folder = directory };
                    try {
                        var check = SkillFiles.Verify(directory);
                        if (check.Marker == null)
                            continue;
                        if (!check.Intact && !force) {
                            action.State = SkillState.Edited;
                            report.Warnings.Add($"Kept {directory}: it was edited or holds files pyRevit did not install{Describe(check.Extras, check.Note)}. Use --force to remove it.");
                        }
                        else if (SkillFiles.ContainsLink(directory)) {
                            action.State = SkillState.Foreign;
                            report.Warnings.Add($"Kept {directory}: it contains a link or a cloud placeholder.");
                        }
                        else {
                            if (!check.Intact)
                                report.Warnings.Add($"Removing {directory} with --force deletes{Describe(check.Extras, check.Note)}.");
                            Directory.Delete(directory, recursive: true);
                            action.State = SkillState.Removed;
                        }
                    }
                    catch (Exception ex) when (ex is IOException || ex is UnauthorizedAccessException) {
                        action.State = SkillState.Failed;
                        report.Warnings.Add($"Could not remove {directory}: {ex.Message}");
                    }
                    report.Actions.Add(action);
                }
            }
            return report;
        }

        /// <summary>
        /// Warns about every user skill whose description is over the limit agents handle well.
        /// </summary>
        public static List<string> UserSkillWarnings(string userSkillsDir) {
            var warnings = new List<string>();
            if (userSkillsDir == null || !Directory.Exists(userSkillsDir))
                return warnings;
            foreach (var directory in Directory.GetDirectories(userSkillsDir).Where(path => !SkillFiles.IsLink(path)))
                WarnLongDescription(directory, warnings, "User skill");
            return warnings;
        }

        private static SkillAction InstallOne(SkillDestination destination, ShippedSkill skill, SkillOptions options, SkillsReport report) {
            var located = Locate(destination, skill, options.Prefix);
            var inspection = located.Inspection;
            var action = new SkillAction { Target = destination.Label, Skill = skill.Name, State = inspection.State, Folder = located.Folder };
            try {
                switch (inspection.State) {
                    case SkillState.Foreign:
                        report.Warnings.Add(ForeignMessage(skill, located, options));
                        break;
                    case SkillState.Current:
                        break;
                    case SkillState.Edited when !options.Force:
                        report.Warnings.Add($"Skipped '{skill.Name}': {located.Folder} was edited or holds files pyRevit did not install{Describe(inspection.Extras, inspection.Note)}. Use --force to replace it.");
                        break;
                    default:
                        if (inspection.State == SkillState.Edited && (inspection.Extras.Count > 0 || inspection.Note != null))
                            report.Warnings.Add($"Replacing {located.Folder} with --force deletes{Describe(inspection.Extras, inspection.Note)}.");
                        var replace = inspection.State != SkillState.Missing;
                        SkillFiles.WriteAtomically(destination.SkillsDir, skill, located.Name, replace, report.Warnings);
                        action.State = replace ? SkillState.Updated : SkillState.Installed;
                        break;
                }
            }
            catch (Exception ex) when (ex is PyRevitException || ex is IOException || ex is UnauthorizedAccessException) {
                action.State = SkillState.Failed;
                report.Warnings.Add($"Could not install '{skill.Name}' into {located.Folder}: {ex.Message}");
            }
            if (action.State == SkillState.Installed || action.State == SkillState.Updated || action.State == SkillState.Current)
                WarnLongDescription(located.Folder, report.Warnings, "Skill");
            return action;
        }

        private static string ForeignMessage(ShippedSkill skill, Located located, SkillOptions options) {
            if (located.Inspection.Note != null)
                return $"Skipped '{skill.Name}': {located.Folder} {located.Inspection.Note}.";
            if (located.PrefixTried)
                return $"Skipped '{skill.Name}': {located.PlainFolder} and {located.Folder} exist and were not installed by pyRevit.";
            if (options.Prefix && skill.Name.StartsWith(NamePrefix, StringComparison.Ordinal))
                return $"Skipped '{skill.Name}': {located.Folder} exists and was not installed by pyRevit, and a name starting with {NamePrefix} is not prefixed again.";
            return $"Skipped '{skill.Name}': {located.Folder} exists and was not installed by pyRevit. Use --prefix to install it as {NamePrefix}{skill.Name}.";
        }

        private static Located Locate(SkillDestination destination, ShippedSkill skill, bool prefixOnClash) {
            var plainFolder = Path.Combine(destination.SkillsDir, skill.Name);
            var plain = Inspect(plainFolder, skill);
            var located = new Located { Name = skill.Name, Folder = plainFolder, Inspection = plain, PlainFolder = plainFolder };
            var prefixedName = NamePrefix + skill.Name;
            var canPrefix = !skill.Name.StartsWith(NamePrefix, StringComparison.Ordinal) && SkillFiles.IsValidName(prefixedName);
            var clash = plain.State == SkillState.Foreign && plain.Note == null && prefixOnClash;
            if (!canPrefix || !(clash || plain.State == SkillState.Missing))
                return located;
            var prefixedFolder = Path.Combine(destination.SkillsDir, prefixedName);
            var prefixed = Inspect(prefixedFolder, skill);
            if (clash || IsOwned(prefixed.State))
                return new Located { Name = prefixedName, Folder = prefixedFolder, Inspection = prefixed, PlainFolder = plainFolder, PrefixTried = true };
            return located;
        }

        private static Located PlainMissing(SkillDestination destination, ShippedSkill skill) {
            return new Located {
                Name = skill.Name,
                Folder = Path.Combine(destination.SkillsDir, skill.Name),
                Inspection = new Inspection { State = SkillState.Missing },
            };
        }

        private static Inspection Inspect(string folder, ShippedSkill skill) {
            var check = SkillFiles.Verify(folder);
            if (!check.Exists)
                return new Inspection { State = SkillState.Missing };
            if (check.Marker == null)
                return new Inspection { State = SkillState.Foreign, Note = check.Note };
            if (!check.Intact)
                return new Inspection { State = SkillState.Edited, Extras = check.Extras, Note = check.Note };
            return new Inspection { State = check.Marker.Sha256 == skill.Digest ? SkillState.Current : SkillState.Stale };
        }

        private static bool IsOwned(SkillState state) {
            return state == SkillState.Current || state == SkillState.Stale || state == SkillState.Edited;
        }

        private static string Describe(List<string> extras, string note) {
            var parts = new List<string>();
            if (extras != null && extras.Count > 0)
                parts.Add(" (" + string.Join(", ", extras.Take(10)) + (extras.Count > 10 ? ", ..." : string.Empty) + ")");
            if (note != null)
                parts.Add(" (" + note + ")");
            return string.Concat(parts);
        }

        private static bool PrepareSkillsDir(SkillContext context, SkillDestination destination, bool create) {
            SkillFiles.AssertInside(context.BaseRoot, destination.SkillsDir);
            SkillFiles.AssertNoLink(context.BaseRoot, destination.SkillsDir);
            if (Directory.Exists(destination.SkillsDir))
                return true;
            if (create)
                Directory.CreateDirectory(destination.SkillsDir);
            return create;
        }

        private static List<ShippedSkill> LoadShipped(string shippedSkillsDir, SkillsReport report) {
            if (string.IsNullOrWhiteSpace(shippedSkillsDir) || !Directory.Exists(shippedSkillsDir))
                throw new PyRevitException("The shipped agent skills were not found. Run this command from a pyRevit install or clone that has pyrevitlib/pyrevit/agent/skills.");
            var skills = new List<ShippedSkill>();
            foreach (var directory in Directory.GetDirectories(shippedSkillsDir).OrderBy(path => path, StringComparer.Ordinal)) {
                var skill = SkillFiles.IsLink(directory) ? null : PyRevitAgentSkills.ReadSkill(directory, PyRevitAgentSkills.ShippedSource);
                if (skill == null)
                    continue;
                if (skill.Name != Path.GetFileName(directory)) {
                    report.Warnings.Add($"Skipped {directory}: the skill name '{skill.Name}' differs from its folder name.");
                    continue;
                }
                var files = SkillFiles.CollectFiles(directory);
                skills.Add(new ShippedSkill { Name = skill.Name, Files = files, Digest = SkillFiles.Digest(files) });
            }
            return skills;
        }

        private static void WarnLongDescription(string folder, List<string> warnings, string label) {
            var path = Path.Combine(folder, SkillFiles.SkillFile);
            try {
                if (!File.Exists(path) || SkillFiles.IsLink(path) || new FileInfo(path).Length > SkillFiles.MaxFileBytes)
                    return;
                var frontMatter = PyRevitAgentSkills.ParseFrontMatter(File.ReadAllLines(path));
                if (frontMatter.TryGetValue("description", out var description) && description.Length > MaxDescriptionChars)
                    warnings.Add($"{label} {folder}: the description has {description.Length} characters; agents may shorten or drop it above {MaxDescriptionChars}.");
            }
            catch (Exception ex) when (ex is IOException || ex is UnauthorizedAccessException) {
            }
        }
    }
}
