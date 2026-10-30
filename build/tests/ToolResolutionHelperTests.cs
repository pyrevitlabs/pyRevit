using Build.Helpers;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Build.Tests;

[TestClass]
[TestCategory("HostFree")]
[TestCategory("Integration")]
[DoNotParallelize]
public sealed class ToolResolutionHelperTests
{
    private string _root = string.Empty;
    private string? _originalPath;
    private string? _originalPathExt;

    [TestInitialize]
    public void SetUp()
    {
        _root = Path.Combine(Path.GetTempPath(), "pyrevit-tools-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(_root);
        _originalPath = Environment.GetEnvironmentVariable("PATH");
        _originalPathExt = Environment.GetEnvironmentVariable("PATHEXT");
        Environment.SetEnvironmentVariable("PATHEXT", ".EXE;.CMD");
    }

    [TestCleanup]
    public void TearDown()
    {
        Environment.SetEnvironmentVariable("PATH", _originalPath);
        Environment.SetEnvironmentVariable("PATHEXT", _originalPathExt);
        Directory.Delete(_root, recursive: true);
    }

    private string Folder(string name)
    {
        var folder = Path.Combine(_root, name);
        Directory.CreateDirectory(folder);
        return folder;
    }

    private static string Tool(string folder, string fileName, string content = "")
    {
        var path = Path.Combine(folder, fileName);
        File.WriteAllText(path, content);
        return path;
    }

    private static void UsePath(params string[] folders) =>
        Environment.SetEnvironmentVariable("PATH", string.Join(Path.PathSeparator, folders));

    [TestMethod]
    public void ResolveAllOnPath_returns_matches_in_path_order_without_duplicates()
    {
        var first = Folder("first");
        var second = Folder("second");
        var firstTool = Tool(first, "tool.EXE");
        var secondTool = Tool(second, "tool.CMD");
        UsePath(" ", "\"" + first + "\"", first, second);

        CollectionAssert.AreEqual(
            new[] { firstTool, secondTool },
            ToolResolutionHelper.ResolveAllOnPath("tool").ToArray());
    }

    [TestMethod]
    public void ResolveOnPath_returns_null_when_nothing_matches()
    {
        UsePath(Folder("empty"));
        Assert.IsNull(ToolResolutionHelper.ResolveOnPath("missing-tool"));
    }

    [TestMethod]
    public void ResolveWingetCreateExecutable_prefers_an_existing_configured_path()
    {
        var configured = Tool(Folder("winget"), "wingetcreate.EXE");
        UsePath(Folder("empty"));
        Assert.AreEqual(configured, ToolResolutionHelper.ResolveWingetCreateExecutable(configured));
    }

    [TestMethod]
    public void ResolveWingetCreateExecutable_falls_back_to_path_when_unconfigured()
    {
        var onPath = Tool(Folder("bin"), "wingetcreate.EXE");
        UsePath(Path.GetDirectoryName(onPath)!);
        Assert.AreEqual(onPath, ToolResolutionHelper.ResolveWingetCreateExecutable(" "));
        Assert.AreEqual(onPath, ToolResolutionHelper.ResolveWingetCreateExecutable(Path.Combine(_root, "absent", "wingetcreate.exe")));
    }

    [TestMethod]
    public void ResolveWingetCreateExecutable_throws_when_not_found()
    {
        UsePath(Folder("empty"));
        Assert.ThrowsExactly<FileNotFoundException>(() => ToolResolutionHelper.ResolveWingetCreateExecutable("wingetcreate.exe"));
    }

    [TestMethod]
    public void ResolvePowerShellExecutable_returns_first_pwsh_without_a_minimum()
    {
        var pwsh = Tool(Folder("pwsh"), "pwsh.EXE");
        UsePath(Path.GetDirectoryName(pwsh)!);
        Assert.AreEqual(pwsh, ToolResolutionHelper.ResolvePowerShellExecutable());
    }

    [TestMethod]
    public void ResolvePowerShellExecutable_checks_the_version_reported_by_pwsh()
    {
        if (!OperatingSystem.IsWindows())
        {
            Assert.Inconclusive("The pwsh double is a Windows batch file.");
        }

        var pwsh = Tool(Folder("pwsh"), "pwsh.CMD", "@echo 7.4.1-preview.2\r\n");
        UsePath(Path.GetDirectoryName(pwsh)!);

        Assert.AreEqual(pwsh, ToolResolutionHelper.ResolvePowerShellExecutable(new Version(7, 4)));

        var fallback = ToolResolutionHelper.ResolvePowerShellExecutable(new Version(99, 0));
        Assert.AreNotEqual(pwsh, fallback);
        StringAssert.EndsWith(fallback, "powershell.exe", StringComparison.OrdinalIgnoreCase);
    }

    [TestMethod]
    public void ResolvePowerShellExecutable_rejects_a_pwsh_that_fails()
    {
        if (!OperatingSystem.IsWindows())
        {
            Assert.Inconclusive("The pwsh double is a Windows batch file.");
        }

        var pwsh = Tool(Folder("pwsh"), "pwsh.CMD", "@exit /b 3\r\n");
        UsePath(Path.GetDirectoryName(pwsh)!);
        Assert.AreNotEqual(pwsh, ToolResolutionHelper.ResolvePowerShellExecutable(new Version(7, 0)));
    }

    [TestMethod]
    public void ResolveMsBuildExecutable_prefers_msbuild_on_path()
    {
        var msbuild = Tool(Folder("msbuild"), "msbuild.EXE");
        UsePath(Path.GetDirectoryName(msbuild)!);
        Assert.AreEqual(msbuild, ToolResolutionHelper.ResolveMsBuildExecutable());
    }
}
