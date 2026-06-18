namespace Build.Helpers;

/// <summary>
/// Repository paths and constants ported from dev/scripts/configs.py.
/// </summary>
public static class PyRevitPaths
{
    public static string Root { get; private set; } = FindRepositoryRoot();

    public static string DevPath => Path.Combine(Root, "dev");
    public static string BinPath => Path.Combine(Root, "bin");
    public static string DistPath => Path.Combine(Root, "dist");
    public static string ReleasePath => Path.Combine(Root, "release");

    public static string LabsSolution => Path.Combine(DevPath, "pyRevitLabs", "pyRevitLabs.sln");
    public static string LabsCliProject => Path.Combine(DevPath, "pyRevitLabs", "pyRevitCLI", "pyRevitCLI.csproj");
    public static string LabsDoctorProject => Path.Combine(DevPath, "pyRevitLabs", "pyRevitDoctor", "pyRevitDoctor.csproj");
    public static string LoadersSolution => Path.Combine(DevPath, "pyRevitLoader", "pyRevitLoader.sln");
    public static string Loader2712Project => Path.Combine(DevPath, "pyRevitLoader", "pyRevitLoader.2712PR", "pyRevitLoader.2712PR.csproj");
    public static string Loader342Project => Path.Combine(DevPath, "pyRevitLoader", "pyRevitLoader.342", "pyRevitLoader.342.csproj");
    public static string Runner2712Project => Path.Combine(DevPath, "pyRevitLoader", "pyRevitRunner.2712PR", "pyRevitRunner.2712PR.csproj");
    public static string Runner342Project => Path.Combine(DevPath, "pyRevitLoader", "pyRevitRunner.342", "pyRevitRunner.342.csproj");
    public static string ExtensionParserTestProject => Path.Combine(DevPath, "pyRevitLoader", "pyRevitExtensionParserTester", "pyRevitExtensionParserTest.csproj");

    public static string IronPython2Solution => Path.Combine(DevPath, "modules", "pyRevitLabs.IronPython2.sln");
    public static string IronPython2LibProject => Path.Combine(DevPath, "modules", "pyRevitLabs.ironpython2", "Src", "IronPython", "IronPython.csproj");
    public static string IronPython2ModulesProject => Path.Combine(DevPath, "modules", "pyRevitLabs.ironpython2", "Src", "IronPython.Modules", "IronPython.Modules.csproj");
    public static string IronPython2SqliteProject => Path.Combine(DevPath, "modules", "pyRevitLabs.ironpython2", "Src", "IronPython.SQLite", "IronPython.SQLite.csproj");
    public static string IronPython2WpfProject => Path.Combine(DevPath, "modules", "pyRevitLabs.ironpython2", "Src", "IronPython.Wpf", "IronPython.Wpf.csproj");

    public static string Engines2712NetFxPath => Path.Combine(BinPath, "netfx", "engines", "IPY2712PR");
    public static string Engines2712NetCorePath => Path.Combine(BinPath, "netcore", "engines", "IPY2712PR");

    public static string RuntimeSolution => Path.Combine(DevPath, "pyRevitLabs.PyRevit.Runtime", "pyRevitLabs.PyRevit.Runtime.sln");
    public static string DirectoryBuildProps => Path.Combine(DevPath, "Directory.Build.props");

    public static string TelemetryServerPath => Path.Combine(DevPath, "pyRevitTelemetryServer");
    public static string TelemetryServerMain => Path.Combine(TelemetryServerPath, "main.go");
    public static string TelemetryServerBin => Path.Combine(BinPath, "pyrevit-telemetryserver.exe");

    public static string AutocompPath => Path.Combine(Root, "dev", "pyRevitLabs", "pyRevitCLIAutoComplete");
    public static string AutocompSource => Path.Combine(AutocompPath, "pyrevit-autocomplete.go");
    public static string AutocompBin => Path.Combine(BinPath, "pyrevit-autocomplete.exe");
    public static string UsagePatterns => Path.Combine(DevPath, "pyRevitLabs", "pyRevitCLI", "Resources", "UsagePatterns.txt");

    public static string VersionFile => Path.Combine(Root, "pyrevitlib", "pyrevit", "version");
    public static string InstallVersionFile => Path.Combine(ReleasePath, "version");
    public static string ProductsTemplateFile => Path.Combine(ReleasePath, "pyrevit-products.json");
    public static string ProductsDataFile => Path.Combine(BinPath, "pyrevit-products.json");
    public static string HostsDataFile => Path.Combine(ReleasePath, "pyrevit-hosts.json");
    public static string BinAssetsPath => Path.Combine(ReleasePath, "bin-assets");
    public static string CEnginesPath => Path.Combine(ReleasePath, "cengines");

    public static IReadOnlyList<string> HostsDataTargets =>
    [
        Path.Combine(BinPath, "pyrevit-hosts.json"),
        Path.Combine(BinPath, "netfx", "pyrevit-hosts.json"),
        Path.Combine(BinPath, "netcore", "pyrevit-hosts.json"),
    ];
    public static string VerifyLibGit2Script => Path.Combine(ReleasePath, "Verify-LibGit2NativeDll.ps1");

    public static string PyRevitInnoProductCode => "f2a3da53-6f34-41d5-abbd-389ffa7f4d5f";
    public static string PyRevitCliInnoProductCode => "9557b432-cf79-4ece-91cf-b8f996c88b47";
    public static string PyRevitCliUpgradeCode => "618520c4-0c3a-4e8d-8e8a-b74db3f3592b";
    public static string WipVersionExtension => "-wip";

    public static string PyRevitInstallerScript => Path.Combine(ReleasePath, "pyrevit.iss");
    public static string PyRevitAdminInstallerScript => Path.Combine(ReleasePath, "pyrevit-admin.iss");
    public static string PyRevitCliInstallerScript => Path.Combine(ReleasePath, "pyrevit-cli.iss");
    public static string PyRevitCliAdminInstallerScript => Path.Combine(ReleasePath, "pyrevit-cli-admin.iss");
    public static string PyRevitCommonMsiProps => Path.Combine(ReleasePath, "pyrevit-common.props");
    public static string PyRevitCliMsiProps => Path.Combine(ReleasePath, "pyrevit-cli.props");
    public static string PyRevitCliMsiProject => Path.Combine(ReleasePath, "pyrevit-cli.wixproj");
    public static string PyRevitChocoNuspec => Path.Combine(ReleasePath, "choco", "pyrevit-cli.nuspec");
    public static string PyRevitChocoInstallScript => Path.Combine(ReleasePath, "choco", "tools", "chocolateyinstall.ps1");

    public static string PyRevitInstallerName => "pyRevit_{0}_signed";
    public static string PyRevitAdminInstallerName => "pyRevit_{0}_admin_signed";
    public static string PyRevitCliInstallerName => "pyRevit_CLI_{0}_signed";
    public static string PyRevitCliAdminInstallerName => "pyRevit_CLI_{0}_admin_signed";
    public static string PyRevitChocoNupkgName => "pyrevit-cli.{0}.nupkg";

    public static IReadOnlyList<string> VersionFiles =>
    [
        DirectoryBuildProps,
        VersionFile,
    ];

    public static IReadOnlyList<string> CopyrightFiles =>
    [
        DirectoryBuildProps,
        Path.Combine(Root, "pyrevitlib", "pyrevit", "versionmgr", "about.py"),
        Path.Combine(Root, "README.md"),
        PyRevitInstallerScript,
        PyRevitCliInstallerScript,
        PyRevitAdminInstallerScript,
        PyRevitCliAdminInstallerScript,
    ];

    public static IReadOnlyList<string> InstallerScripts =>
    [
        PyRevitInstallerScript,
        PyRevitCliInstallerScript,
        PyRevitAdminInstallerScript,
        PyRevitCliAdminInstallerScript,
    ];

    public static IReadOnlyList<string> StampedReleaseMetadataFiles =>
    [
        VersionFile,
        InstallVersionFile,
        PyRevitInstallerScript,
        PyRevitAdminInstallerScript,
        PyRevitCliInstallerScript,
        PyRevitCliAdminInstallerScript,
        PyRevitCommonMsiProps,
        PyRevitChocoNuspec,
    ];

    public static string IsccPath =>
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), "Inno Setup 6", "ISCC.exe");

    public static void Initialize(string? rootOverride = null)
    {
        if (!string.IsNullOrWhiteSpace(rootOverride))
        {
            Root = Path.GetFullPath(rootOverride);
        }
    }

    private static string FindRepositoryRoot()
    {
        var current = new DirectoryInfo(AppContext.BaseDirectory);
        while (current is not null)
        {
            if (File.Exists(Path.Combine(current.FullName, "pyRevitfile")))
            {
                return current.FullName;
            }

            current = current.Parent;
        }

        return Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
    }
}
