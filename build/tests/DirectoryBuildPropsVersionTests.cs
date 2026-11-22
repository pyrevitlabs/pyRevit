using System.Diagnostics;
using System.Xml.Linq;
using Build.Helpers;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Build.Tests;

[TestClass]
[TestCategory("HostFree")]
[TestCategory("Integration")]
public sealed class DirectoryBuildPropsVersionTests
{
    [TestMethod]
    public void DirectoryBuildProps_givesMsBuildTheExportedBuildVersion()
    {
        var original = Environment.GetEnvironmentVariable(VersionHelper.BuildVersionVariable);
        var projectDirectory = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(projectDirectory);
        try
        {
            var projectPath = Path.Combine(projectDirectory, "Probe.csproj");
            new XElement(
                "Project",
                new XAttribute("Sdk", "Microsoft.NET.Sdk"),
                new XElement("Import", new XAttribute("Project", PyRevitPaths.DirectoryBuildProps)),
                new XElement("PropertyGroup", new XElement("TargetFramework", "net10.0")))
                .Save(projectPath);
            VersionHelper.ExportBuildVersion("7.2.0.26326+1041");

            var version = EvaluateMsBuildProperty(projectPath, "Version");

            Assert.AreEqual("7.2.0.26326+1041", version);
        }
        finally
        {
            Environment.SetEnvironmentVariable(VersionHelper.BuildVersionVariable, original);
            Directory.Delete(projectDirectory, recursive: true);
        }
    }

    private static string EvaluateMsBuildProperty(string projectPath, string property)
    {
        var startInfo = new ProcessStartInfo("dotnet")
        {
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            WorkingDirectory = Path.GetDirectoryName(projectPath)!,
        };
        startInfo.ArgumentList.Add("msbuild");
        startInfo.ArgumentList.Add(projectPath);
        startInfo.ArgumentList.Add($"-getProperty:{property}");

        using var process = Process.Start(startInfo)!;
        var output = process.StandardOutput.ReadToEnd();
        var error = process.StandardError.ReadToEnd();
        process.WaitForExit();
        Assert.AreEqual(0, process.ExitCode, error + output);
        return output.Trim();
    }
}
