using System.Diagnostics;
using System.Text;
using pyRevitCLI;
using pyRevitLabs.Common;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

internal static class LinkSupport {
    public static readonly bool Available = Probe();

    public static bool MakeJunction(string link, string target) {
        try {
            var start = new ProcessStartInfo("cmd.exe", $"/c mklink /J \"{link}\" \"{target}\"") { CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true };
            using var process = Process.Start(start);
            process.StandardOutput.ReadToEnd();
            process.WaitForExit();
            return process.ExitCode == 0 && Directory.Exists(link);
        }
        catch (Exception) {
            return false;
        }
    }

    private static bool Probe() {
        var root = Directory.CreateTempSubdirectory("pyrevit-link-probe-").FullName;
        try {
            var target = Directory.CreateDirectory(Path.Combine(root, "target")).FullName;
            var link = Path.Combine(root, "link");
            var made = MakeJunction(link, target);
            if (made)
                Directory.Delete(link);
            return made;
        }
        finally {
            Directory.Delete(root, recursive: true);
        }
    }
}

public sealed class LinkFactAttribute : FactAttribute {
    public LinkFactAttribute() {
        if (!LinkSupport.Available)
            Skip = "Junctions cannot be created on this machine.";
    }
}

[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public class AgentSkillInstallerTests : IDisposable {
    private readonly string temp = Directory.CreateTempSubdirectory("pyrevit-skill-install-").FullName;
    private readonly string shipped;
    private readonly string project;
    private readonly string home;
    private readonly List<string> junctions = new List<string>();

    public AgentSkillInstallerTests() {
        shipped = Directory.CreateDirectory(Path.Combine(temp, "shipped")).FullName;
        project = Directory.CreateDirectory(Path.Combine(temp, "project")).FullName;
        home = Directory.CreateDirectory(Path.Combine(temp, "home")).FullName;
        WriteShipped("alpha", "Use when testing alpha.", "alpha body");
        WriteShipped("beta", "Use when testing beta.", "beta body");
        File.WriteAllText(Path.Combine(shipped, "alpha", "extra.md"), "extra");
        File.WriteAllText(Path.Combine(shipped, "alpha", "notes.txt"), "not markdown");
    }

    public void Dispose() {
        foreach (var junction in junctions.Where(Directory.Exists))
            Directory.Delete(junction);
        Directory.Delete(temp, recursive: true);
    }

    private void WriteShipped(string name, string description, string body) {
        var directory = Directory.CreateDirectory(Path.Combine(shipped, name)).FullName;
        File.WriteAllText(Path.Combine(directory, "SKILL.md"), $"---\nname: {name}\ndescription: {description}\n---\n{body}\n");
    }

    private string Skills(string root, params string[] parts) => Path.Combine(new[] { root }.Concat(parts).ToArray());

    private string AgentsSkill(string name, params string[] parts) => Skills(project, new[] { ".agents", "skills", name }.Concat(parts).ToArray());

    private SkillContext Context(string targets = "agents", string scope = "project") =>
        SkillContext.Create(targets, scope, scope == "project" ? project : null, project, home, shipped);

    private SkillsReport Install(string targets = "agents", string scope = "project", bool force = false, bool prefix = false) =>
        PyRevitAgentSkillInstaller.Install(Context(targets, scope), new SkillOptions { Force = force, Prefix = prefix });

    private SkillsReport Status(string targets = "agents", string scope = "project") =>
        PyRevitAgentSkillInstaller.Status(Context(targets, scope));

    private SkillsReport Uninstall(string targets = "agents", string scope = "project", bool force = false) =>
        PyRevitAgentSkillInstaller.Uninstall(Context(targets, scope), force);

    private static SkillState StateOf(SkillsReport report, string skill) => report.Actions.Single(action => action.Skill == skill).State;

    private string MakeForeign(string name, string text = "mine") {
        var foreign = Directory.CreateDirectory(AgentsSkill(name)).FullName;
        File.WriteAllText(Path.Combine(foreign, "SKILL.md"), text);
        return foreign;
    }

    private void MakeJunction(string link, string target) {
        junctions.Add(link);
        Assert.True(LinkSupport.MakeJunction(link, target));
    }

    [Fact]
    public void InstallCopiesMarkdownFilesAndWritesTheMarkerIntoTheAgentsFolder() {
        var report = Install();

        Assert.Equal(SkillState.Installed, StateOf(report, "alpha"));
        Assert.True(File.Exists(AgentsSkill("alpha", "SKILL.md")));
        Assert.Equal("extra", File.ReadAllText(AgentsSkill("alpha", "extra.md")));
        Assert.False(File.Exists(AgentsSkill("alpha", "notes.txt")));
        var marker = JObject.Parse(File.ReadAllText(AgentsSkill("alpha", ".pyrevit-skill.json")));
        Assert.Equal("pyrevit", marker.Value<string>("source"));
        Assert.Equal("alpha", marker.Value<string>("name"));
        Assert.Matches("^[0-9a-f]{64}$", marker.Value<string>("sha256"));
        Assert.Empty(Directory.GetDirectories(Skills(project, ".agents", "skills"), ".pyrevit-tmp-*"));
    }

    [Fact]
    public void InstallAgainReportsCurrentAndDoesNotRewriteTheFiles() {
        Install();
        var old = new DateTime(2001, 1, 1, 0, 0, 0, DateTimeKind.Utc);
        File.SetLastWriteTimeUtc(AgentsSkill("alpha", "SKILL.md"), old);

        var report = Install();

        Assert.Equal(SkillState.Current, StateOf(report, "alpha"));
        Assert.Equal(old, File.GetLastWriteTimeUtc(AgentsSkill("alpha", "SKILL.md")));
    }

    [Fact]
    public void InstallRefreshesAStaleOwnedCopy() {
        Install();
        File.WriteAllText(Path.Combine(shipped, "alpha", "extra.md"), "extra v2");
        Assert.Equal(SkillState.Stale, StateOf(Status(), "alpha"));

        var report = Install();

        Assert.Equal(SkillState.Updated, StateOf(report, "alpha"));
        Assert.Equal("extra v2", File.ReadAllText(AgentsSkill("alpha", "extra.md")));
        Assert.Equal(SkillState.Current, StateOf(Status(), "alpha"));
        Assert.Empty(Directory.GetDirectories(Skills(project, ".agents", "skills"), ".pyrevit-tmp-*"));
    }

    [Fact]
    public void AFolderWithoutTheMarkerIsSkippedAndLeftUntouched() {
        var foreign = MakeForeign("alpha");

        var report = Install(force: true);

        Assert.Equal(SkillState.Foreign, StateOf(report, "alpha"));
        Assert.Equal(SkillState.Installed, StateOf(report, "beta"));
        Assert.Equal("mine", File.ReadAllText(Path.Combine(foreign, "SKILL.md")));
        Assert.Contains(report.Warnings, warning => warning.Contains(foreign) && warning.Contains("--prefix"));
        Assert.Equal(SkillState.Foreign, StateOf(Status(), "alpha"));
    }

    [Fact]
    public void APlainFileNamedLikeASkillIsForeignAndTheRunGoesOn() {
        Directory.CreateDirectory(Skills(project, ".agents", "skills"));
        File.WriteAllText(AgentsSkill("alpha"), "a file");

        var report = Install();

        Assert.Equal(SkillState.Foreign, StateOf(report, "alpha"));
        Assert.Equal(SkillState.Installed, StateOf(report, "beta"));
        Assert.Equal("a file", File.ReadAllText(AgentsSkill("alpha")));
        Assert.Equal(SkillState.Foreign, StateOf(Status(), "alpha"));
        Uninstall();
        Assert.Equal("a file", File.ReadAllText(AgentsSkill("alpha")));
    }

    [Fact]
    public void PrefixInstallsAClashingSkillUnderAPrefixedNameWithTheNameLineRewritten() {
        var foreign = MakeForeign("alpha");

        var report = Install(prefix: true);

        Assert.Equal(SkillState.Installed, StateOf(report, "alpha"));
        Assert.Equal("mine", File.ReadAllText(Path.Combine(foreign, "SKILL.md")));
        var prefixed = File.ReadAllText(AgentsSkill("pyrevit-alpha", "SKILL.md"));
        Assert.Contains("name: pyrevit-alpha\n", prefixed);
        Assert.DoesNotContain("name: alpha", prefixed);
        Assert.True(Directory.Exists(AgentsSkill("beta")));
        Assert.Equal(SkillState.Current, StateOf(Status(), "alpha"));
        Assert.Equal(SkillState.Current, StateOf(Install(prefix: true), "alpha"));
    }

    [Fact]
    public void PrefixWithTheSameNameStillTakenSaysSoInsteadOfAskingForPrefix() {
        MakeForeign("alpha");
        MakeForeign("pyrevit-alpha");

        var report = Install(prefix: true);

        Assert.Equal(SkillState.Foreign, StateOf(report, "alpha"));
        var warning = Assert.Single(report.Warnings, text => text.Contains("pyrevit-alpha"));
        Assert.DoesNotContain("Use --prefix", warning);
    }

    [Fact]
    public void ANamedFileWithCrlfAndABomSurvivesPrefixingByteForByte() {
        var text = "---\r\nname: \"alpha\"\r\ndescription: Use when testing.\r\n---\r\nbody\r\n";
        File.WriteAllBytes(Path.Combine(shipped, "alpha", "SKILL.md"), new UTF8Encoding(true).GetPreamble().Concat(Encoding.UTF8.GetBytes(text)).ToArray());
        MakeForeign("alpha");

        Install(prefix: true);

        var bytes = File.ReadAllBytes(AgentsSkill("pyrevit-alpha", "SKILL.md"));
        var expected = new UTF8Encoding(true).GetPreamble().Concat(Encoding.UTF8.GetBytes(text.Replace("name: \"alpha\"", "name: pyrevit-alpha"))).ToArray();
        Assert.Equal(expected, bytes);
        Assert.Equal(SkillState.Current, StateOf(Status(), "alpha"));
    }

    [Fact]
    public void WithoutPrefixTheInstalledNameIsTheShippedName() {
        Install();

        Assert.True(Directory.Exists(AgentsSkill("alpha")));
        Assert.False(Directory.Exists(AgentsSkill("pyrevit-alpha")));
    }

    [Fact]
    public void AnOwnedPrefixedCopyIsRefreshedInPlaceWhenThePlainNameIsFree() {
        var foreign = MakeForeign("alpha");
        Install(prefix: true);
        Directory.Delete(foreign, recursive: true);
        File.WriteAllText(Path.Combine(shipped, "alpha", "extra.md"), "extra v2");

        Assert.Equal(SkillState.Stale, StateOf(Status(), "alpha"));
        var report = Install();

        Assert.Equal(SkillState.Updated, StateOf(report, "alpha"));
        Assert.False(Directory.Exists(AgentsSkill("alpha")));
        Assert.Equal("extra v2", File.ReadAllText(AgentsSkill("pyrevit-alpha", "extra.md")));
    }

    [Fact]
    public void AHandEditedOwnedCopyIsKeptUntilForceRepairsIt() {
        Install();
        File.AppendAllText(AgentsSkill("alpha", "SKILL.md"), "my edit");

        Assert.Equal(SkillState.Edited, StateOf(Status(), "alpha"));
        Assert.Equal(SkillState.Edited, StateOf(Install(), "alpha"));
        Assert.Contains("my edit", File.ReadAllText(AgentsSkill("alpha", "SKILL.md")));

        Assert.Equal(SkillState.Updated, StateOf(Install(force: true), "alpha"));
        Assert.DoesNotContain("my edit", File.ReadAllText(AgentsSkill("alpha", "SKILL.md")));
    }

    [Fact]
    public void AnEditedPrefixedCopyIsKeptUntilForce() {
        MakeForeign("alpha");
        Install(prefix: true);
        File.AppendAllText(AgentsSkill("pyrevit-alpha", "SKILL.md"), "my edit");

        Assert.Equal(SkillState.Edited, StateOf(Status(), "alpha"));
        Assert.Equal(SkillState.Edited, StateOf(Install(prefix: true), "alpha"));
        Assert.Equal(SkillState.Updated, StateOf(Install(prefix: true, force: true), "alpha"));
    }

    [Fact]
    public void ExtraFilesInAnOwnedFolderMakeItEditedAndSurviveUntilForce() {
        Install();
        File.WriteAllText(AgentsSkill("alpha", "notes.txt"), "my notes");
        Directory.CreateDirectory(AgentsSkill("alpha", "scripts"));
        File.WriteAllText(AgentsSkill("alpha", "scripts", "x.py"), "print(1)");
        File.WriteAllText(Path.Combine(shipped, "alpha", "extra.md"), "extra v2");

        Assert.Equal(SkillState.Edited, StateOf(Status(), "alpha"));
        var kept = Install();
        Assert.Equal(SkillState.Edited, StateOf(kept, "alpha"));
        Assert.Contains(kept.Warnings, warning => warning.Contains("notes.txt") && warning.Contains("scripts/x.py"));
        Assert.True(File.Exists(AgentsSkill("alpha", "notes.txt")));
        Assert.True(File.Exists(AgentsSkill("alpha", "scripts", "x.py")));

        var forced = Install(force: true);
        Assert.Equal(SkillState.Updated, StateOf(forced, "alpha"));
        Assert.Contains(forced.Warnings, warning => warning.Contains("deletes") && warning.Contains("notes.txt"));
        Assert.False(File.Exists(AgentsSkill("alpha", "notes.txt")));
        Assert.Equal(SkillState.Current, StateOf(Status(), "alpha"));
    }

    [Fact]
    public void UninstallKeepsAnEditedOrExtendedCopyUntilForce() {
        Install();
        File.WriteAllText(AgentsSkill("alpha", "notes.txt"), "my notes");
        File.AppendAllText(AgentsSkill("beta", "SKILL.md"), "my edit");

        var kept = Uninstall();

        Assert.All(kept.Actions, action => Assert.Equal(SkillState.Edited, action.State));
        Assert.True(File.Exists(AgentsSkill("alpha", "notes.txt")));
        Assert.Contains("my edit", File.ReadAllText(AgentsSkill("beta", "SKILL.md")));

        var removed = Uninstall(force: true);

        Assert.All(removed.Actions, action => Assert.Equal(SkillState.Removed, action.State));
        Assert.Contains(removed.Warnings, warning => warning.Contains("notes.txt"));
        Assert.False(Directory.Exists(AgentsSkill("alpha")));
        Assert.False(Directory.Exists(AgentsSkill("beta")));
    }

    [Fact]
    public void ACopiedMarkerDoesNotMakeAFolderRemovable() {
        Install();
        var forged = Directory.CreateDirectory(AgentsSkill("mine")).FullName;
        File.WriteAllText(Path.Combine(forged, "SKILL.md"), "my own skill");
        File.Copy(AgentsSkill("beta", ".pyrevit-skill.json"), Path.Combine(forged, ".pyrevit-skill.json"));

        var report = Uninstall();

        Assert.Equal(SkillState.Edited, report.Actions.Single(action => action.Skill == "mine").State);
        Assert.Equal("my own skill", File.ReadAllText(Path.Combine(forged, "SKILL.md")));
    }

    [Theory]
    [InlineData("{\"source\":{\"a\":1},\"sha256\":\"x\"}")]
    [InlineData("{\"source\":[\"pyrevit\"],\"sha256\":[1]}")]
    [InlineData("[1,2]")]
    [InlineData("not json")]
    public void AMalformedMarkerMakesTheFolderForeignWithoutThrowing(string markerText) {
        var foreign = MakeForeign("alpha");
        File.WriteAllText(Path.Combine(foreign, ".pyrevit-skill.json"), markerText);

        var report = Install();

        Assert.Equal(SkillState.Foreign, StateOf(report, "alpha"));
        Assert.Equal(SkillState.Installed, StateOf(report, "beta"));
        Assert.Equal("mine", File.ReadAllText(Path.Combine(foreign, "SKILL.md")));
    }

    [Fact]
    public void StatusReportsMissingForSkillsNotInstalled() {
        var report = Status();

        Assert.All(report.Actions, action => Assert.Equal(SkillState.Missing, action.State));
        Assert.Equal(2, report.Actions.Count);
    }

    [Fact]
    public void UninstallRemovesOnlyOwnedFoldersAndKeepsTheSkillsFolder() {
        Install();
        var skills = Skills(project, ".agents", "skills");
        var foreign = MakeForeign("mine");
        Directory.CreateDirectory(Path.Combine(skills, ".pyrevit-tmp-leftover"));

        Uninstall();

        Assert.False(Directory.Exists(Path.Combine(skills, "alpha")));
        Assert.False(Directory.Exists(Path.Combine(skills, "beta")));
        Assert.False(Directory.Exists(Path.Combine(skills, ".pyrevit-tmp-leftover")));
        Assert.True(File.Exists(Path.Combine(foreign, "SKILL.md")));
    }

    [Fact]
    public void UninstallLeavesAFolderWithoutTheMarkerAlone() {
        var foreign = MakeForeign("alpha");

        Uninstall(force: true);

        Assert.True(File.Exists(Path.Combine(foreign, "SKILL.md")));
    }

    [Fact]
    public void ALeftoverCopyIsPutBackWhenTheDestinationIsMissingAndRemovedWhenItIsNot() {
        Install();
        Directory.Move(AgentsSkill("alpha"), AgentsSkill(".pyrevit-tmp-crash1"));
        Directory.CreateDirectory(AgentsSkill(".pyrevit-tmp-crash2"));
        File.Copy(AgentsSkill("beta", ".pyrevit-skill.json"), AgentsSkill(".pyrevit-tmp-crash2", ".pyrevit-skill.json"));
        File.WriteAllText(AgentsSkill(".pyrevit-tmp-crash2", "SKILL.md"), "x");

        var report = Install();

        Assert.Equal(SkillState.Current, StateOf(report, "alpha"));
        Assert.Contains(report.Warnings, warning => warning.Contains("Restored"));
        Assert.Empty(Directory.GetDirectories(Skills(project, ".agents", "skills"), ".pyrevit-tmp-*"));
    }

    [Fact]
    public void UninstallSweepsLeftoverCopiesThatCarryAMarker() {
        Install();
        Directory.Move(AgentsSkill("alpha"), AgentsSkill(".pyrevit-tmp-crash"));

        Uninstall();

        Assert.Empty(Directory.GetDirectories(Skills(project, ".agents", "skills")));
    }

    [Theory]
    [InlineData("agents", ".agents/skills")]
    [InlineData("claude", ".claude/skills")]
    [InlineData("copilot", ".github/skills")]
    [InlineData("opencode", ".opencode/skills")]
    [InlineData("antigravity", ".agents/skills")]
    public void ProjectScopeWritesTheClientFolderUnderTheProjectRoot(string target, string folder) {
        Install(target);

        Assert.True(File.Exists(Skills(project, folder.Split('/').Concat(new[] { "alpha", "SKILL.md" }).ToArray())));
    }

    [Theory]
    [InlineData("agents", ".agents/skills")]
    [InlineData("claude", ".claude/skills")]
    [InlineData("copilot", ".copilot/skills")]
    [InlineData("opencode", ".config/opencode/skills")]
    [InlineData("antigravity", ".gemini/config/skills")]
    public void UserScopeWritesTheClientFolderUnderTheProfile(string target, string folder) {
        Install(target, scope: "user");

        Assert.True(File.Exists(Skills(home, folder.Split('/').Concat(new[] { "alpha", "SKILL.md" }).ToArray())));
        Assert.False(Directory.Exists(Skills(project, ".agents")));
    }

    [Fact]
    public void SeveralTargetsAreInstalledAndASharedFolderIsWrittenOnce() {
        var report = Install("agents,antigravity,claude");

        Assert.Equal(4, report.Actions.Count);
        Assert.True(File.Exists(Skills(project, ".claude", "skills", "alpha", "SKILL.md")));
    }

    [Fact]
    public void AnUnknownTargetOrScopeNamesTheValidValues() {
        var target = Assert.Throws<PyRevitException>(() => SkillTargets.ParseTargets("agents,nope"));
        Assert.Contains("nope", target.Message);
        Assert.Contains("opencode", target.Message);

        var scope = Assert.Throws<PyRevitException>(() => Context(scope: "everywhere"));
        Assert.Contains("project", scope.Message);
        Assert.Contains("user", scope.Message);
    }

    [Fact]
    public void ThePathOptionBelongsToTheProjectScopeAndBothRootsMustExist() {
        var withPath = Assert.Throws<PyRevitException>(() => SkillContext.Create("agents", "user", project, project, home, shipped));
        Assert.Contains("--path", withPath.Message);
        Assert.Throws<PyRevitException>(() => SkillContext.Create("agents", "project", Path.Combine(temp, "missing"), project, home, shipped));
        Assert.Throws<PyRevitException>(() => SkillContext.Create("agents", "user", null, project, string.Empty, shipped));
        Assert.Equal(Path.GetFullPath(project), SkillContext.Create("agents", "project", null, project, home, shipped).BaseRoot);
    }

    [Fact]
    public void AShippedFileOverTheLimitIsRefusedAndNothingIsInstalled() {
        File.WriteAllText(Path.Combine(shipped, "alpha", "big.md"), new string('x', 129 * 1024));

        Assert.Throws<PyRevitException>(() => Install());

        Assert.False(Directory.Exists(AgentsSkill("alpha")));
    }

    [LinkFact]
    public void ASkillsFolderThatIsAJunctionIsRefused() {
        var elsewhere = Directory.CreateDirectory(Path.Combine(temp, "elsewhere")).FullName;
        Directory.CreateDirectory(Path.Combine(project, ".agents"));
        MakeJunction(Skills(project, ".agents", "skills"), elsewhere);

        Assert.Throws<PyRevitException>(() => Install());
        Assert.Throws<PyRevitException>(() => Status());

        Assert.Empty(Directory.GetFileSystemEntries(elsewhere));
    }

    [LinkFact]
    public void ALinkedSkillFolderIsForeignAndTheRestOfTheRunIsReported() {
        var elsewhere = Directory.CreateDirectory(Path.Combine(temp, "elsewhere")).FullName;
        File.WriteAllText(Path.Combine(elsewhere, "keep.md"), "keep");
        Directory.CreateDirectory(Skills(project, ".agents", "skills"));
        MakeJunction(AgentsSkill("alpha"), elsewhere);

        var installed = Install(force: true, prefix: true);
        var status = Status();
        var removed = Uninstall(force: true);

        Assert.Equal(SkillState.Foreign, StateOf(installed, "alpha"));
        Assert.Equal(SkillState.Installed, StateOf(installed, "beta"));
        Assert.Contains(installed.Warnings, warning => warning.Contains("link"));
        Assert.Equal(2, status.Actions.Count);
        Assert.Equal(SkillState.Foreign, StateOf(status, "alpha"));
        Assert.Equal(SkillState.Removed, StateOf(removed, "beta"));
        Assert.Equal("keep", File.ReadAllText(Path.Combine(elsewhere, "keep.md")));
        Assert.Equal(new[] { "keep.md" }, Directory.GetFileSystemEntries(elsewhere).Select(Path.GetFileName));
    }

    [LinkFact]
    public void AnOwnedFolderHoldingALinkIsReportedEditedAndNeverFollowed() {
        Install();
        var elsewhere = Directory.CreateDirectory(Path.Combine(temp, "elsewhere")).FullName;
        File.WriteAllText(Path.Combine(elsewhere, "keep.md"), "keep");
        MakeJunction(AgentsSkill("alpha", "linked"), elsewhere);

        Assert.Equal(SkillState.Edited, StateOf(Status(), "alpha"));
        Assert.Equal(SkillState.Failed, StateOf(Install(force: true), "alpha"));
        Uninstall(force: true);

        Assert.True(File.Exists(Path.Combine(elsewhere, "keep.md")));
        Assert.True(Directory.Exists(AgentsSkill("alpha")));
    }

    [Fact]
    public void ALockedFileFailsOnlyThatSkillAndTheOldCopyStays() {
        Install();
        File.WriteAllText(Path.Combine(shipped, "alpha", "extra.md"), "extra v2");
        File.WriteAllText(Path.Combine(shipped, "beta", "extra.md"), "beta extra");

        SkillsReport report;
        using (new FileStream(AgentsSkill("alpha", "extra.md"), FileMode.Open, FileAccess.Read, FileShare.Read))
            report = Install();

        Assert.Equal(SkillState.Failed, StateOf(report, "alpha"));
        Assert.Equal(SkillState.Updated, StateOf(report, "beta"));
        Assert.Equal("extra", File.ReadAllText(AgentsSkill("alpha", "extra.md")));
        Assert.Equal(SkillState.Stale, StateOf(Status(), "alpha"));
        Assert.Empty(Directory.GetDirectories(Skills(project, ".agents", "skills"), ".pyrevit-tmp-*"));
        Assert.Contains(report.Warnings, warning => warning.Contains("alpha"));
    }

    [Fact]
    public void ASkillWhoseNameDiffersFromItsFolderIsNotInstalled() {
        Directory.CreateDirectory(Path.Combine(shipped, "gamma"));
        File.WriteAllText(Path.Combine(shipped, "gamma", "SKILL.md"), "---\nname: ../evil\ndescription: x\n---\n");

        var report = Install();

        Assert.DoesNotContain(report.Actions, action => action.Skill == "gamma" && action.State == SkillState.Installed);
        Assert.False(Directory.Exists(Skills(project, ".agents", "evil")));
    }

    [Fact]
    public void StatusWarnsWhenOneClientReadsTheSameOwnedSkillFromTwoFolders() {
        Install("agents,claude");

        var report = Status();

        Assert.Contains(report.Warnings, warning => warning.Contains("OpenCode") && warning.Contains("alpha"));
    }

    [Fact]
    public void TheOverlapWarningAlsoCatchesAPlainAndAPrefixedCopyOfTheSameSkill() {
        var foreign = Directory.CreateDirectory(Skills(project, ".claude", "skills", "alpha")).FullName;
        File.WriteAllText(Path.Combine(foreign, "SKILL.md"), "mine");
        Install("claude", prefix: true);
        Install("agents");

        var report = Status("agents");

        Assert.Contains(report.Warnings, warning => warning.Contains("OpenCode") && warning.Contains("'alpha'") && warning.Contains("pyrevit-alpha"));
    }

    [Fact]
    public void InstallAndStatusWarnAboutAnInstalledDescriptionOverTheLimit() {
        WriteShipped("alpha", new string('d', 241), "alpha body");

        var report = Install();

        Assert.Contains(report.Warnings, warning => warning.Contains("alpha") && warning.Contains("241"));
        Assert.Contains(Status().Warnings, warning => warning.Contains("alpha") && warning.Contains("241"));
    }

    [Fact]
    public void EveryTargetIsDocumentedInTheHelpTextAndTheDocs() {
        var help = PyRevitCLIAppHelps.HelpText(PyRevitCLICommandType.Agent);
        var docs = File.ReadAllText(Path.Combine(RepositoryRoot(), "docs", "agent-runtime.md"));

        foreach (var target in SkillTargets.TargetNames) {
            Assert.Contains(target, help);
            Assert.Contains($"| `{target}` |", docs);
        }
    }

    private static string RepositoryRoot() {
        for (var directory = new DirectoryInfo(AppContext.BaseDirectory); directory != null; directory = directory.Parent)
            if (File.Exists(Path.Combine(directory.FullName, "docs", "agent-runtime.md")))
                return directory.FullName;
        throw new DirectoryNotFoundException("docs/agent-runtime.md not found above " + AppContext.BaseDirectory);
    }
}

[Trait("Environment", "HostFree")]
[Trait("Level", "Integration")]
[Trait("Category", "RealShippedSkills")]
public class ShippedSkillsInstallTests : IDisposable {
    private readonly string temp = Directory.CreateTempSubdirectory("pyrevit-shipped-install-").FullName;

    public void Dispose() {
        Directory.Delete(temp, recursive: true);
    }

    [Fact]
    public void TheShippedPyRevitSkillsInstallAndReportCurrent() {
        var real = PyRevitAgentSkills.ShippedSkillsDir;
        Assert.NotNull(real);
        var project = Directory.CreateDirectory(Path.Combine(temp, "project")).FullName;
        var context = SkillContext.Create("agents", "project", project, project, temp, real);

        var installed = PyRevitAgentSkillInstaller.Install(context, new SkillOptions());
        var status = PyRevitAgentSkillInstaller.Status(context);

        var summary = string.Join("; ", installed.Actions.Select(action => action.Skill + "=" + action.State.Label()).Concat(installed.Warnings));
        Assert.True(installed.Actions.Count >= 10, summary);
        Assert.All(status.Actions, action => Assert.True(action.State == SkillState.Current, action.Skill + " is " + action.State.Label() + ": " + summary));
        Assert.Empty(status.Warnings);
    }
}
