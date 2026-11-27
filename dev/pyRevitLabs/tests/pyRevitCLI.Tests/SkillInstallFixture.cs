using pyRevitCLI;

namespace pyRevitCLI.Tests;

/// <summary>
/// Shared setup for the skill installer tests: a temp project folder, profile folder and a fake shipped
/// skills folder holding <c>alpha</c> and <c>beta</c>. Nothing here touches the real profile.
/// </summary>
public abstract class SkillInstallFixture : IDisposable {
    internal readonly string temp = Directory.CreateTempSubdirectory("pyrevit-skill-install-").FullName;
    internal readonly string shipped;
    internal readonly string project;
    internal readonly string home;
    private readonly List<string> junctions = new List<string>();

    protected SkillInstallFixture() {
        shipped = Directory.CreateDirectory(Path.Combine(temp, "shipped")).FullName;
        project = Directory.CreateDirectory(Path.Combine(temp, "project")).FullName;
        home = Directory.CreateDirectory(Path.Combine(temp, "home")).FullName;
        WriteShipped("alpha", "Use when testing alpha.", "alpha body");
        WriteShipped("beta", "Use when testing beta.", "beta body");
        File.WriteAllText(Path.Combine(shipped, "alpha", "extra.md"), "extra");
        File.WriteAllText(Path.Combine(shipped, "alpha", "notes.txt"), "not markdown");
    }

    public void Dispose() {
        try {
            foreach (var junction in junctions)
                TryDeleteJunction(junction);
        }
        finally {
            Directory.Delete(temp, recursive: true);
        }
    }

    private static void TryDeleteJunction(string junction) {
        try {
            if (Directory.Exists(junction))
                Directory.Delete(junction);
        }
        catch (Exception ex) when (ex is IOException || ex is UnauthorizedAccessException) {
            Console.Error.WriteLine($"Could not remove junction {junction}: {ex.Message}");
        }
    }

    internal void WriteShipped(string name, string description, string body) {
        var directory = Directory.CreateDirectory(Path.Combine(shipped, name)).FullName;
        File.WriteAllText(Path.Combine(directory, "SKILL.md"), $"---\nname: {name}\ndescription: {description}\n---\n{body}\n");
    }

    internal string Skills(string root, params string[] parts) => Path.Combine(new[] { root }.Concat(parts).ToArray());

    internal string AgentsSkill(string name, params string[] parts) => Skills(project, new[] { ".agents", "skills", name }.Concat(parts).ToArray());

    internal SkillContext Context(string targets = "agents", string scope = "project") =>
        SkillContext.Create(targets, scope, scope == "project" ? project : null, project, home, shipped);

    internal SkillsReport Install(string targets = "agents", string scope = "project", bool force = false, bool prefix = false) =>
        PyRevitAgentSkillInstaller.Install(Context(targets, scope), new SkillOptions { Force = force, Prefix = prefix });

    internal SkillsReport Status(string targets = "agents", string scope = "project") =>
        PyRevitAgentSkillInstaller.Status(Context(targets, scope));

    internal SkillsReport Uninstall(string targets = "agents", string scope = "project", bool force = false) =>
        PyRevitAgentSkillInstaller.Uninstall(
            SkillContext.CreateForUninstall(targets, scope, scope == "project" ? project : null, project, home), force);

    internal static SkillState StateOf(SkillsReport report, string skill) => StateOf(report.Actions, skill);

    internal static SkillState StateOf(List<SkillAction> actions, string skill) => actions.Single(action => action.Skill == skill).State;

    internal string MakeForeign(string name, string text = "mine") {
        var foreign = Directory.CreateDirectory(AgentsSkill(name)).FullName;
        File.WriteAllText(Path.Combine(foreign, "SKILL.md"), text);
        return foreign;
    }

    internal void MakeJunction(string link, string target) {
        junctions.Add(link);
        Assert.True(LinkSupport.MakeJunction(link, target));
    }

    internal static void Age(string directory) => Directory.SetLastWriteTimeUtc(directory, DateTime.UtcNow.AddHours(-1));

    internal static void CopyDirectory(string from, string to) {
        Directory.CreateDirectory(to);
        foreach (var file in Directory.GetFiles(from))
            File.Copy(file, Path.Combine(to, Path.GetFileName(file)));
        foreach (var directory in Directory.GetDirectories(from))
            CopyDirectory(directory, Path.Combine(to, Path.GetFileName(directory)));
    }
}
