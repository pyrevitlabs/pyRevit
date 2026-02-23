using System;
using System.Diagnostics;
using Nuke.Common;
using Nuke.Common.IO;
using Nuke.Common.Execution;
using Nuke.Common.Tools.DotNet;
using static Nuke.Common.Tools.DotNet.DotNetTasks;

[UnsetVisualStudioEnvironmentVariables]
partial class Build : NukeBuild
{
    public static int Main() => Execute<Build>(x => x.BuildProducts);

    [Parameter("Configuration to build (Release or Debug)")]
    readonly string Configuration = "Release";

    AbsolutePath DevPath => RootDirectory / "dev";
    AbsolutePath BinPath => RootDirectory / "bin";
    AbsolutePath LibsNetFx => DevPath / "libs" / "netfx";
    AbsolutePath LibsNetCore => DevPath / "libs" / "netcore";
    AbsolutePath Engines2NetFx => BinPath / "netfx" / "engines" / "IPY2712PR";
    AbsolutePath Engines2NetCore => BinPath / "netcore" / "engines" / "IPY2712PR";

    static readonly string[] ProxyEnvVars = { "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "GIT_HTTP_PROXY", "GIT_HTTPS_PROXY", "NO_PROXY", "SOCKS_PROXY", "SOCKS5_PROXY" };

    static void RunProcess(string fileName, string arguments, string? workingDirectory = null, bool captureOutput = false, bool unsetProxy = false)
    {
        var startInfo = new ProcessStartInfo
        {
            FileName = fileName,
            Arguments = arguments,
            UseShellExecute = false,
            RedirectStandardOutput = captureOutput,
            RedirectStandardError = captureOutput
        };
        if (workingDirectory != null)
            startInfo.WorkingDirectory = workingDirectory;
        if (unsetProxy)
        {
            foreach (System.Collections.DictionaryEntry e in Environment.GetEnvironmentVariables())
                startInfo.Environment[(string)e.Key] = (string?)e.Value;
            foreach (var key in ProxyEnvVars)
                startInfo.Environment.Remove(key);
        }
        var p = Process.Start(startInfo);
        if (p == null)
            throw new Exception($"Failed to start {fileName}");
        string outStr = "", errStr = "";
        if (captureOutput)
        {
            var outTask = System.Threading.Tasks.Task.Run(() => p.StandardOutput.ReadToEnd());
            var errTask = System.Threading.Tasks.Task.Run(() => p.StandardError.ReadToEnd());
            outStr = outTask.GetAwaiter().GetResult();
            errStr = errTask.GetAwaiter().GetResult();
        }
        p.WaitForExit();
        if (p.ExitCode != 0)
        {
            var msg = $"{fileName} {arguments} exited with {p.ExitCode}";
            if (captureOutput && (!string.IsNullOrWhiteSpace(outStr) || !string.IsNullOrWhiteSpace(errStr)))
                msg += "\n--- stdout ---\n" + outStr + "\n--- stderr ---\n" + errStr;
            throw new Exception(msg);
        }
    }

    void DotNetPublishTo(AbsolutePath project, string framework, AbsolutePath output)
    {
        RunProcess("dotnet", $"publish \"{project}\" -c {Configuration} -f {framework} -o \"{output}\"");
    }

    Target Clean => _ => _
        .Description("Remove dev/**/bin, obj, .vs, TestResults.")
        .Executes(() =>
        {
            foreach (var dir in DevPath.GlobDirectories("**/bin", "**/obj", "**/.vs", "**/TestResults"))
                dir.DeleteDirectory();
        });

    Target BuildDeps => _ => _
        .Description("Build dependencies: MahApps, Newtonsoft.Json, NLog, IronPython2, Python.Net → dev/libs and engine folders.")
        .Executes(() =>
        {
            var mahApps = DevPath / "modules" / "pyRevitLabs.MahApps.Metro" / "src" / "MahApps.Metro" / "MahApps.Metro.csproj";
            var newtonsoft = DevPath / "modules" / "pyRevitLabs.Newtonsoft.Json" / "Src" / "Newtonsoft.Json" / "Newtonsoft.Json.csproj";
            var nlog = DevPath / "modules" / "pyRevitLabs.NLog" / "src" / "NLog" / "NLog.csproj";
            var ironPython2Sln = DevPath / "modules" / "pyRevitLabs.IronPython2.sln";
            var ironPython2Lib = DevPath / "modules" / "pyRevitLabs.IronPython2" / "Src" / "IronPython" / "IronPython.csproj";
            var ironPython2Modules = DevPath / "modules" / "pyRevitLabs.IronPython2" / "Src" / "IronPython.Modules" / "IronPython.Modules.csproj";
            var ironPython2Sqlite = DevPath / "modules" / "pyRevitLabs.IronPython2" / "Src" / "IronPython.SQLite" / "IronPython.SQLite.csproj";
            var ironPython2Wpf = DevPath / "modules" / "pyRevitLabs.IronPython2" / "Src" / "IronPython.Wpf" / "IronPython.Wpf.csproj";
            var pythonRuntime = DevPath / "modules" / "pyRevitLabs.Python.Net" / "src" / "runtime" / "Python.Runtime.csproj";

            LibsNetFx.CreateDirectory();
            LibsNetCore.CreateDirectory();
            Engines2NetFx.CreateDirectory();
            Engines2NetCore.CreateDirectory();

            DotNetBuild(_ => _.SetProjectFile(mahApps).SetConfiguration(Configuration).SetFramework("net47"));
            DotNetPublishTo(mahApps, "net47", LibsNetFx);
            DotNetPublishTo(mahApps, "netcoreapp3.1", LibsNetCore);

            DotNetPublishTo(newtonsoft, "net45", LibsNetFx);
            DotNetPublishTo(newtonsoft, "net6.0", LibsNetCore);

            DotNetPublishTo(nlog, "net46", LibsNetFx);
            DotNetPublishTo(nlog, "netstandard2.0", LibsNetCore);

            DotNetPublishTo(ironPython2Sln, "net48", Engines2NetFx);
            DotNetPublishTo(ironPython2Lib, "netstandard2.0", Engines2NetCore);
            DotNetPublishTo(ironPython2Modules, "netstandard2.0", Engines2NetCore);
            DotNetPublishTo(ironPython2Sqlite, "netstandard2.0", Engines2NetCore);
            DotNetPublishTo(ironPython2Wpf, "net6.0-windows", Engines2NetCore);

            DotNetPublishTo(pythonRuntime, "netstandard2.0", LibsNetFx);
            DotNetPublishTo(pythonRuntime, "netstandard2.0", LibsNetCore);
        });

    Target BuildLabs => _ => _
        .Description("Build Labs (pyRevitLabs.sln), CLI, Doctor. Run BuildDeps first or invoke this and deps run automatically.")
        .DependsOn(BuildDeps)
        .Executes(() =>
        {
            var labs = DevPath / "pyRevitLabs" / "pyRevitLabs.sln";
            var cli = DevPath / "pyRevitLabs" / "pyRevitCLI" / "pyRevitCLI.csproj";
            var doctor = DevPath / "pyRevitLabs" / "pyRevitDoctor" / "pyRevitDoctor.csproj";
            DotNetBuild(_ => _.SetProjectFile(labs).SetConfiguration(Configuration));
            BinPath.CreateDirectory();
            DotNetPublishTo(cli, "net8.0-windows", BinPath);
            DotNetPublishTo(doctor, "net8.0-windows", BinPath);
        });

    Target BuildLoaders => _ => _
        .Description("Build loaders (pyRevitLoader.sln). Depends on BuildLabs (and thus BuildDeps).")
        .DependsOn(BuildLabs)
        .Executes(() =>
        {
            var loaders = DevPath / "pyRevitLoader" / "pyRevitLoader.sln";
            // Single-threaded build so Deploy targets (copy to engine folders) don't race; avoids "file in use" on first run after Clean.
            RunProcess("dotnet", $"build \"{loaders}\" -c {Configuration} /m:1", captureOutput: true);
        });

    Target BuildRuntime => _ => _
        .Description("Build Runtime (IPY2712PR + IPY342). Depends on BuildLoaders.")
        .DependsOn(BuildLoaders)
        .Executes(() =>
        {
            var runtime = DevPath / "pyRevitLabs.PyRevit.Runtime" / "pyRevitLabs.PyRevit.Runtime.sln";
            DotNetBuild(_ => _.SetProjectFile(runtime).SetConfiguration($"{Configuration} IPY2712PR"));
            DotNetBuild(_ => _.SetProjectFile(runtime).SetConfiguration($"{Configuration} IPY342"));
        });

    Target DeployLibsToEngines => _ => _
        .Description("Copy dev/libs/netcore (MahApps, etc.) into netcore engine folders. Depends on BuildRuntime.")
        .DependsOn(BuildRuntime)
        .Executes(() =>
        {
            foreach (var engineDir in new[] { Engines2NetCore, BinPath / "netcore" / "engines" / "IPY342" })
            {
                if (!engineDir.Exists()) continue;
                foreach (var f in LibsNetCore.GlobFiles("*"))
                    FileSystemTasks.CopyFile(f, engineDir / f.Name, FileExistsPolicy.Overwrite);
            }
        });

    void BuildTelemCore()
    {
        var telemPath = DevPath / "pyRevitTelemetryServer";
        var outputExe = BinPath / "pyrevit-telemetryserver.exe";
        BinPath.CreateDirectory();
        RunProcess("go", "get ./...", (string)telemPath, captureOutput: true, unsetProxy: true);
        RunProcess("go", $"build -o \"{outputExe}\" .", (string)telemPath, captureOutput: true, unsetProxy: true);
    }

    Target BuildTelem => _ => _
        .Description("Build telemetry server (Go) to bin/pyrevit-telemetryserver.exe. No project dependencies; can run alone.")
        .Executes(BuildTelemCore);

    void BuildAutocmpCore()
    {
        var autocmpPath = DevPath / "pyRevitLabs" / "pyRevitCLIAutoComplete";
        var outputExe = BinPath / "pyrevit-autocomplete.exe";
        BinPath.CreateDirectory();
        RunProcess("go", "get ./...", (string)autocmpPath, captureOutput: true, unsetProxy: true);
        RunProcess("go", $"build -o \"{outputExe}\" .", (string)autocmpPath, captureOutput: true, unsetProxy: true);
    }

    Target BuildAutocmp => _ => _
        .Description("Build CLI shell autocomplete (Go) to bin/pyrevit-autocomplete.exe. Uses checked-in pyrevit-autocomplete.go; to regenerate from UsagePatterns.txt run: pipenv run pyrevit build autocmp.")
        .Executes(BuildAutocmpCore);

    Target BuildProducts => _ => _
        .Description("Full build: BuildDeps → BuildLabs → BuildLoaders → BuildRuntime → DeployLibsToEngines → BuildTelem → BuildAutocmp.")
        .DependsOn(DeployLibsToEngines, BuildTelem, BuildAutocmp)
        .Executes(() => { });

    Target Check => _ => _
        .Description("Verify dotnet and go are on PATH.")
        .Executes(() =>
        {
            try
            {
                DotNet("--version");
                Serilog.Log.Information("[PASS] dotnet is ready");
            }
            catch (Exception ex)
            {
                throw new Exception("dotnet is required but not found or failed. Install .NET SDK and add to PATH.", ex);
            }

            try
            {
                RunProcess("go", "version");
                Serilog.Log.Information("[PASS] go is ready");
            }
            catch (Exception ex)
            {
                throw new Exception("go is required but not found or failed. Install Go and add to PATH.", ex);
            }
        });
}
