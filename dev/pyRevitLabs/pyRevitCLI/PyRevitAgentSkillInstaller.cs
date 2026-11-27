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
    /// carries a <c>.pyrevit-skill.json</c> marker; a folder is pyRevit-owned only while the marker names that
    /// folder and the content still matches it.
    /// Invariants: a folder without a valid marker is never overwritten, replaced or deleted; an owned
    /// folder that was edited or holds extra files is replaced or removed only with <c>force</c>, which
    /// names the extra files first; nothing is written or deleted through a link; every path stays inside
    /// the skills folder. A skill or skills folder that cannot be handled is reported as <c>failed</c> or
    /// <c>foreign</c> and the run goes on. Install and uninstall hold a named mutex per skills folder.
    /// Installed copies are guidance, not policy: they cannot change host policy.
    /// </remarks>
    internal static class PyRevitAgentSkillInstaller {
        internal const string DefaultTarget = "agents";
        internal const string DefaultScope = "project";
        private const int MaxDescriptionChars = 240;
        private const int MaxListedExtras = 10;
        private const string NamePrefix = "pyrevit-";
        private const string SkillLabel = "Skill";
        private const string UserSkillLabel = "User skill";
        private const string WholeFolder = "(skills folder)";

        private sealed class Inspection {
            public SkillState State { get; set; }
            public List<string> Extras { get; set; } = new List<string>();
            public string Note { get; set; }
        }

        private sealed class Located {
            private Located() {
            }

            public string Name { get; private set; }
            public string Folder { get; private set; }
            public string PlainFolder { get; private set; }
            public bool PrefixTried { get; private set; }
            public Inspection Inspection { get; private set; }

            public static Located Plain(string folder, Inspection inspection) {
                return new Located { Name = Path.GetFileName(folder), Folder = folder, PlainFolder = folder, Inspection = inspection };
            }

            public static Located Prefixed(string folder, string plainFolder, Inspection inspection) {
                return new Located { Name = Path.GetFileName(folder), Folder = folder, PlainFolder = plainFolder, PrefixTried = true, Inspection = inspection };
            }
        }

        /// <summary>
        /// Installs the shipped skills into the skills folder of each target.
        /// </summary>
        /// <remarks>
        /// Idempotent: a current copy is reported and not rewritten, a stale owned copy is refreshed. A folder
        /// without the marker is skipped with a warning, or the skill is installed as
        /// <c>pyrevit-&lt;name&gt;</c> with <see cref="SkillOptions.Prefix"/>. An existing owned prefixed copy is
        /// refreshed in place when the plain name is free or taken by a foreign folder.
        /// <see cref="SkillOptions.Force"/> replaces an owned copy that was edited, removing any extra files in
        /// it after naming them in a warning.
        /// </remarks>
        /// <exception cref="PyRevitException">The shipped skills are missing or have a file over the limit.</exception>
        public static SkillsReport Install(SkillContext context, SkillOptions options) {
            var report = new SkillsReport();
            var shipped = LoadShipped(context.ShippedDir, report);
            foreach (var destination in context.Destinations) {
                try {
                    SkillFiles.EnsureSkillsDir(context.BaseRoot, destination.SkillsDir, create: true);
                    using (SkillFiles.Lock(destination.SkillsDir)) {
                        report.Warnings.AddRange(SkillFiles.SweepTemp(destination.SkillsDir, restore: true));
                        foreach (var skill in shipped)
                            report.Actions.Add(InstallOne(destination, skill, options, report));
                    }
                }
                catch (Exception ex) when (SkillFiles.IsRecoverable(ex)) {
                    FailDestination(report, destination, ex);
                }
            }
            return report;
        }

        /// <summary>
        /// Compares the copies in each target's skills folder with the shipped skills.
        /// </summary>
        /// <remarks>
        /// States: <c>current</c>, <c>stale</c> (shipped skill changed), <c>edited</c> (content differs from the
        /// marker or has extra files), <c>missing</c>, <c>foreign</c> (a folder pyRevit did not write holds the
        /// name), <c>failed</c> (the skills folder or skill could not be read). Also warns when one client would
        /// read the same pyRevit-owned skill from several folders. Read-only.
        /// </remarks>
        public static SkillsReport Status(SkillContext context) {
            var report = new SkillsReport();
            var shipped = LoadShipped(context.ShippedDir, report);
            foreach (var destination in context.Destinations) {
                try {
                    var exists = SkillFiles.EnsureSkillsDir(context.BaseRoot, destination.SkillsDir, create: false);
                    foreach (var skill in shipped)
                        report.Actions.Add(StatusOne(destination, skill, exists, report));
                }
                catch (Exception ex) when (SkillFiles.IsRecoverable(ex)) {
                    FailDestination(report, destination, ex);
                }
            }
            SkillTargets.WarnOverlaps(context, report.Warnings);
            return report;
        }

        /// <summary>
        /// Removes the pyRevit-owned skill folders from each target's skills folder.
        /// </summary>
        /// <param name="context">Created with <see cref="SkillContext.CreateForUninstall"/>; the shipped skills are not needed.</param>
        /// <param name="force">Also removes an owned folder that was edited or holds extra files, naming them first.</param>
        /// <remarks>
        /// Removes only folders whose marker names them and matches their content, plus old leftover
        /// <c>.pyrevit-tmp-*</c> folders. Never removes the skills folder, a folder without a valid marker or
        /// anything reached through a link.
        /// </remarks>
        public static SkillsReport Uninstall(SkillContext context, bool force) {
            var report = new SkillsReport();
            foreach (var destination in context.Destinations) {
                try {
                    if (!SkillFiles.EnsureSkillsDir(context.BaseRoot, destination.SkillsDir, create: false))
                        continue;
                    using (SkillFiles.Lock(destination.SkillsDir)) {
                        report.Warnings.AddRange(SkillFiles.SweepTemp(destination.SkillsDir, restore: false));
                        foreach (var directory in Directory.GetDirectories(destination.SkillsDir).OrderBy(path => path, StringComparer.OrdinalIgnoreCase)) {
                            var action = RemoveOwned(destination, directory, force, report);
                            if (action != null)
                                report.Actions.Add(action);
                        }
                    }
                }
                catch (Exception ex) when (SkillFiles.IsRecoverable(ex)) {
                    FailDestination(report, destination, ex);
                }
            }
            return report;
        }

        /// <summary>
        /// Warns about every user skill whose description is over the limit agents handle well.
        /// </summary>
        /// <remarks>
        /// Never throws for a folder that cannot be listed or read: that becomes a warning, so a finished install
        /// or a status report is still printed.
        /// </remarks>
        public static List<string> UserSkillWarnings(string userSkillsDir) {
            var warnings = new List<string>();
            if (userSkillsDir == null || !Directory.Exists(userSkillsDir))
                return warnings;
            try {
                foreach (var directory in Directory.GetDirectories(userSkillsDir))
                    WarnAboutUserSkill(directory, warnings);
            }
            catch (Exception ex) when (SkillFiles.IsRecoverable(ex)) {
                warnings.Add($"{UserSkillLabel}s in {userSkillsDir} could not be checked: {ex.Message}");
            }
            return warnings;
        }

        private static void WarnAboutUserSkill(string directory, List<string> warnings) {
            try {
                if (!SkillFiles.IsLink(directory))
                    WarnLongDescription(directory, warnings, UserSkillLabel);
            }
            catch (Exception ex) when (SkillFiles.IsRecoverable(ex)) {
                warnings.Add($"{UserSkillLabel} {directory} could not be checked: {ex.Message}");
            }
        }

        private static void FailDestination(SkillsReport report, SkillDestination destination, Exception ex) {
            report.Actions.Add(new SkillAction { Target = destination.Label, Skill = WholeFolder, State = SkillState.Failed, Folder = destination.SkillsDir });
            report.Warnings.Add($"Could not use {destination.SkillsDir}: {ex.Message}");
        }

        private static SkillAction StatusOne(SkillDestination destination, ShippedSkill skill, bool skillsDirExists, SkillsReport report) {
            var plainFolder = Path.Combine(destination.SkillsDir, skill.Name);
            var action = new SkillAction { Target = destination.Label, Skill = skill.Name, State = SkillState.Missing, Folder = plainFolder };
            if (!skillsDirExists)
                return action;
            try {
                var located = Locate(destination, skill, installPrefixed: false);
                action.State = located.Inspection.State;
                action.Folder = located.Folder;
                if (located.Inspection.Note != null)
                    report.Warnings.Add($"{located.Folder}: {located.Inspection.Note}.");
                if (located.Inspection.State == SkillState.Edited && located.Inspection.Extras.Count > 0)
                    report.Warnings.Add($"{located.Folder} holds files pyRevit did not install{Describe(located.Inspection.Extras, null)}.");
                if (IsOwned(action.State))
                    WarnLongDescription(located.Folder, report.Warnings, SkillLabel);
            }
            catch (Exception ex) when (SkillFiles.IsRecoverable(ex)) {
                action.State = SkillState.Failed;
                report.Warnings.Add($"Could not read '{skill.Name}' in {plainFolder}: {ex.Message}");
            }
            return action;
        }

        private static SkillAction RemoveOwned(SkillDestination destination, string directory, bool force, SkillsReport report) {
            var name = Path.GetFileName(directory);
            if (name.StartsWith(SkillFiles.TempPrefix, StringComparison.Ordinal) || SkillFiles.IsLink(directory))
                return null;
            var action = new SkillAction { Target = destination.Label, Skill = name, Folder = directory };
            try {
                var check = SkillFiles.Verify(directory);
                if (check.Marker == null)
                    return null;
                if (!check.Intact && !force) {
                    report.Warnings.Add(EditedMessage(directory, check.Extras, check.Note, ", so it was kept. Use --force to remove it."));
                    action.State = SkillState.Edited;
                }
                else if (SkillFiles.ContainsLink(directory)) {
                    report.Warnings.Add($"Kept {directory}: it contains a link or a cloud placeholder.");
                    action.State = SkillState.Foreign;
                }
                else {
                    if (!check.Intact)
                        report.Warnings.Add(ForceDeleteWarning("Removing", directory, check.Extras, check.Note));
                    Directory.Delete(directory, recursive: true);
                    action.State = SkillState.Removed;
                }
            }
            catch (Exception ex) when (SkillFiles.IsRecoverable(ex)) {
                action.State = SkillState.Failed;
                report.Warnings.Add($"Could not remove {directory}: {ex.Message}");
            }
            return action;
        }

        private static SkillAction InstallOne(SkillDestination destination, ShippedSkill skill, SkillOptions options, SkillsReport report) {
            var action = new SkillAction { Target = destination.Label, Skill = skill.Name, State = SkillState.Failed, Folder = Path.Combine(destination.SkillsDir, skill.Name) };
            try {
                var located = Locate(destination, skill, options.Prefix);
                var inspection = located.Inspection;
                action.State = inspection.State;
                action.Folder = located.Folder;
                switch (inspection.State) {
                    case SkillState.Foreign:
                        report.Warnings.Add(ForeignMessage(skill, located, options));
                        break;
                    case SkillState.Current:
                        break;
                    case SkillState.Edited when !options.Force:
                        report.Warnings.Add(EditedMessage(located.Folder, inspection.Extras, inspection.Note, $", so '{skill.Name}' was skipped. Use --force to replace it."));
                        break;
                    case SkillState.Missing:
                    case SkillState.Stale:
                    case SkillState.Edited:
                        var replace = inspection.State != SkillState.Missing;
                        var forceWarning = ForceReplaceWarning(inspection, located.Folder);
                        if (forceWarning != null)
                            report.Warnings.Add(forceWarning);
                        var leftover = SkillFiles.WriteAtomically(destination.SkillsDir, skill, located.Name, replace);
                        if (leftover != null)
                            report.Warnings.Add(leftover);
                        action.State = replace ? SkillState.Updated : SkillState.Installed;
                        break;
                }
                if (IsOwned(action.State))
                    WarnLongDescription(located.Folder, report.Warnings, SkillLabel);
            }
            catch (Exception ex) when (SkillFiles.IsRecoverable(ex)) {
                action.State = SkillState.Failed;
                report.Warnings.Add($"Could not install '{skill.Name}' into {action.Folder}: {ex.Message}");
            }
            return action;
        }

        private static string ForceReplaceWarning(Inspection inspection, string folder) {
            return inspection.State == SkillState.Edited ? ForceDeleteWarning("Replacing", folder, inspection.Extras, inspection.Note) : null;
        }

        private static string ForceDeleteWarning(string verb, string folder, List<string> extras, string note) {
            return $"{verb} {folder} with --force deletes the whole folder, including your edits{Describe(extras, note)}.";
        }

        private static string EditedMessage(string folder, List<string> extras, string note, string outcome) {
            return $"{folder} was edited or holds files pyRevit did not install{Describe(extras, note)}{outcome}";
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

        /// <summary>
        /// Finds the folder a skill lives in. The plain name wins unless it is free or foreign and the prefixed
        /// folder is the better answer: an owned prefixed copy exists, or <paramref name="installPrefixed"/> and the
        /// plain name is foreign.
        /// </summary>
        private static Located Locate(SkillDestination destination, ShippedSkill skill, bool installPrefixed) {
            var plainFolder = Path.Combine(destination.SkillsDir, skill.Name);
            var plain = Located.Plain(plainFolder, Inspect(plainFolder, skill));
            var prefixedName = NamePrefix + skill.Name;
            var canPrefix = !skill.Name.StartsWith(NamePrefix, StringComparison.Ordinal) && SkillFiles.IsValidName(prefixedName);
            var plainFree = plain.Inspection.State == SkillState.Missing;
            var plainClash = plain.Inspection.State == SkillState.Foreign && plain.Inspection.Note == null;
            if (!canPrefix || !(plainFree || plainClash))
                return plain;
            var prefixedFolder = Path.Combine(destination.SkillsDir, prefixedName);
            var prefixed = Inspect(prefixedFolder, skill);
            if (IsOwned(prefixed.State) || (plainClash && installPrefixed))
                return Located.Prefixed(prefixedFolder, plainFolder, prefixed);
            return plain;
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
            return state == SkillState.Installed || state == SkillState.Updated || state == SkillState.Current || state == SkillState.Stale || state == SkillState.Edited;
        }

        private static string Describe(List<string> extras, string note) {
            var parts = new List<string>();
            if (extras != null && extras.Count > 0)
                parts.Add(" (" + string.Join(", ", extras.Take(MaxListedExtras)) + (extras.Count > MaxListedExtras ? ", ..." : string.Empty) + ")");
            if (note != null)
                parts.Add(" (" + note + ")");
            return string.Concat(parts);
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
                skills.Add(SkillFiles.LoadShipped(directory, skill.Name));
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
            catch (Exception ex) when (SkillFiles.IsRecoverable(ex)) {
                warnings.Add($"{label} {folder}: could not read the description: {ex.Message}");
            }
        }
    }
}
