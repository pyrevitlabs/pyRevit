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

    [TestMethod]
    public void VersionStamping_cannot_rewrite_the_webview2_pin()
    {
        var pinFile = Path.Combine(PyRevitPaths.DevPath, "WebView2Version.props");

        StringAssert.Contains(File.ReadAllText(pinFile), "<PyRevitWebView2Version>");

        foreach (var file in PyRevitPaths.VersionFiles)
        {
            Assert.IsFalse(
                File.ReadAllText(file).Contains("PyRevitWebView2Version", StringComparison.Ordinal),
                $"{file} is stamped and would overwrite the pinned WebView2 version.");
        }
    }

    [TestMethod]
    public void VersionStamping_keepsTheExportedBuildVersionOverride()
    {
        var copy = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N") + ".props");
        try
        {
            File.Copy(PyRevitPaths.DirectoryBuildProps, copy);

            VersionHelper.ReplaceVersionInFiles([copy], "9.9.9.99999+9999");

            var stamped = File.ReadAllText(copy);
            StringAssert.Contains(stamped, "<Version>9.9.9.99999+9999</Version>");
            StringAssert.Contains(stamped, $"$({VersionHelper.BuildVersionVariable})</Version>");
        }
        finally
        {
            File.Delete(copy);
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
