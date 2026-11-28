using pyRevitCLI;

namespace pyRevitCLI.Tests;

[Trait("Environment", "HostFree")]
[Trait("Level", "Integration")]
[Trait("Category", "RealShippedSkills")]
public class ShippedSkillsInstallTests : IDisposable {
    private readonly string temp = Directory.CreateTempSubdirectory("pyrevit-shipped-install-").FullName;

    public void Dispose() {
        Directory.Delete(temp, recursive: true);
    }

    [RepoSkillsFact]
    public void TheRepositorySkillsInstallAndReportCurrent() {
        var project = Directory.CreateDirectory(Path.Combine(temp, "project")).FullName;
        var context = SkillContext.Create("agents", "project", project, project, temp, RepoSkills.Directory);

        var installed = PyRevitAgentSkillInstaller.Install(context, new SkillOptions());
        var status = PyRevitAgentSkillInstaller.Status(context);

        var summary = string.Join("; ", installed.Actions.Select(action => action.Skill + "=" + action.State.Label()).Concat(installed.Warnings));
        Assert.NotEmpty(installed.Actions);
        Assert.All(status.Actions, action => Assert.True(action.State == SkillState.Current, action.Skill + " is " + action.State.Label() + ": " + summary));
        Assert.Empty(status.Warnings);
    }
}
