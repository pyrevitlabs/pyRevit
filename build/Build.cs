using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.RegularExpressions;
using Nuke.Common;
using Nuke.Common.IO;
using Nuke.Common.Execution;
using Nuke.Common.Tools.DotNet;
using static Nuke.Common.Tools.DotNet.DotNetTasks;
using static Nuke.Common.IO.FileSystemTasks;

[UnsetVisualStudioEnvironmentVariables]
partial class Build : NukeBuild
{
    public static int Main() => Execute<Build>(x => x.BuildProducts);

    [Parameter("Configuration to build (Release or Debug)")]
    readonly string Configuration = "Release";

    [Parameter("Version for SetVersion (e.g. 4.9.0).")]
    readonly string? SetVersionVersion;

    [Parameter("If true, append -wip to version (SetVersion).")]
    readonly bool SetVersionWip;

    [Parameter("Arguments for RunPyRevit (e.g. 'set locales', 'report changelog').")]
    readonly string? RunPyRevitArgs;

    AbsolutePath DevPath => RootDirectory / "dev";
    AbsolutePath BinPath => RootDirectory / "bin";
    AbsolutePath ReleasePath => RootDirectory / "release";
    AbsolutePath DistPath => RootDirectory / "dist";
    AbsolutePath PyRevitModulePath => RootDirectory / "pyrevitlib" / "pyrevit";
    AbsolutePath LibsNetFx => DevPath / "libs" / "netfx";
    AbsolutePath LibsNetCore => DevPath / "libs" / "netcore";
    AbsolutePath Engines2NetFx => BinPath / "netfx" / "engines" / "IPY2712PR";
    AbsolutePath Engines2NetCore => BinPath / "netcore" / "engines" / "IPY2712PR";

    static readonly Regex VerFinder = new Regex(@"\d\.\d+\.\d+(\.[a-z0-9+-]+)?", RegexOptions.Compiled);
    const string WipSuffix = "-wip";

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

    void BuildAutocmpCore()
    {
        var autocmpPath = DevPath / "pyRevitLabs" / "pyRevitCLIAutoComplete";
        var outputExe = BinPath / "pyrevit-autocomplete.exe";
        BinPath.CreateDirectory();
        RunProcess("go", $"build -o \"{outputExe}\" .", (string)autocmpPath, captureOutput: true, unsetProxy: true);
    }

    Target BuildAutocmp => _ => _
        .Description("Build CLI shell autocomplete (Go) to bin/pyrevit-autocomplete.exe. Uses checked-in pyrevit-autocomplete.go; to regenerate from UsagePatterns.txt run: pipenv run pyrevit build autocmp.")
        .Executes(BuildAutocmpCore);

    Target BuildProducts => _ => _
        .Description("Full build: BuildDeps → BuildLabs → BuildLoaders → BuildRuntime → DeployLibsToEngines → BuildAutocmp (matches pipenv run pyrevit build products; telemetry server moved to another repo).")
        .DependsOn(DeployLibsToEngines, BuildAutocmp)
        .Executes(() => { });

    Target Check => _ => _
        .Description("Verify dotnet and go are on PATH (mirrors pipenv run pyrevit check).")
        .Executes(() =>
        {
            try { RunProcess("dotnet", "--version"); }
            catch (Exception ex) { throw new Exception("dotnet is required but not found or failed. Install .NET SDK and add to PATH.", ex); }
            try { RunProcess("go", "version"); }
            catch (Exception ex) { throw new Exception("go is required but not found or failed. Install Go and add to PATH.", ex); }
        });

    void ReplaceVersionInFiles(IEnumerable<AbsolutePath> files, string newVersion)
    {
        foreach (var f in files)
        {
            if (!f.FileExists()) continue;
            var text = File.ReadAllText(f);
            var newText = VerFinder.Replace(text, newVersion);
            if (text != newText) File.WriteAllText(f, newText);
        }
    }

    Target SetVersion => _ => _
        .Description("Set version number in all version/installer files. Use --set-version-version 4.9.0 [--set-version-wip].")
        .Executes(() =>
        {
            var ver = SetVersionVersion ?? throw new Exception("SetVersion requires --set-version-version <ver> (e.g. 4.9.0).");
            var m = Regex.Match(ver, @"^(\d\.\d+\.\d+)(\.[a-z0-9+-]+)?$");
            var buildVer = m.Success
                ? m.Groups[1].Value + "." + DateTime.Now.ToString("yy") + DateTime.Now.DayOfYear.ToString("000") + "+" + DateTime.Now.ToString("HHmm") + (m.Groups[2].Success ? m.Groups[2].Value : "") + (SetVersionWip ? WipSuffix : "")
                : ver + (SetVersionWip ? WipSuffix : "");
            var installVer = buildVer.Split('+')[0];

            var versionFiles = new[] { RootDirectory / "dev" / "Directory.Build.props", PyRevitModulePath / "version" };
            ReplaceVersionInFiles(versionFiles, buildVer);
            File.WriteAllText(ReleasePath / "version", installVer);

            var installerFiles = new[] { ReleasePath / "pyrevit.iss", ReleasePath / "pyrevit-cli.iss", ReleasePath / "pyrevit-admin.iss", ReleasePath / "pyrevit-cli-admin.iss" };
            ReplaceVersionInFiles(installerFiles, installVer);

            var msiProps = ReleasePath / "pyrevit-common.props";
            if (msiProps.FileExists())
            {
                var xml = File.ReadAllText(msiProps);
                xml = Regex.Replace(xml, @"<Version>[^<]*</Version>", $"<Version>{installVer}</Version>");
                File.WriteAllText(msiProps, xml);
            }

            var nuspec = ReleasePath / "choco" / "pyrevit-cli.nuspec";
            if (nuspec.FileExists())
            {
                var xml = File.ReadAllText(nuspec);
                xml = Regex.Replace(xml, @"<version>[^<]*</version>", $"<version>{installVer}</version>");
                var releaseNotes = "https://github.com/pyrevitlabs/pyRevit/releases/tag/v" + Uri.EscapeDataString(buildVer) + "/";
                xml = Regex.Replace(xml, @"<releaseNotes>[^<]*</releaseNotes>", $"<releaseNotes>{releaseNotes}</releaseNotes>");
                File.WriteAllText(nuspec, xml);
            }
        });

    Target SetYear => _ => _
        .Description("Update copyright year to current year in Directory.Build.props, versionmgr/about.py, README, .iss, MSI, choco.")
        .Executes(() =>
        {
            var now = DateTime.Now;
            var year = now.Year;
            var nextJan1 = new DateTime(year + 1, 1, 1);
            var threshold = nextJan1.AddDays(-30);
            if (now >= threshold) year++;
            var newCopyright = $"2014-{year}";
            var cpFinder = new Regex(@"2014-\d{4}", RegexOptions.Compiled);

            var files = new[] { RootDirectory / "dev" / "Directory.Build.props", PyRevitModulePath / "versionmgr" / "about.py", RootDirectory / "README.md",
                ReleasePath / "pyrevit.iss", ReleasePath / "pyrevit-cli.iss", ReleasePath / "pyrevit-admin.iss", ReleasePath / "pyrevit-cli-admin.iss" };
            foreach (var f in files)
            {
                if (!f.FileExists()) continue;
                var text = File.ReadAllText(f);
                var newText = cpFinder.Replace(text, newCopyright);
                if (text != newText) File.WriteAllText(f, newText);
            }

            var msiProps = ReleasePath / "pyrevit-common.props";
            if (msiProps.FileExists())
            {
                var xml = File.ReadAllText(msiProps);
                xml = Regex.Replace(xml, @"<Copyright>[^<]*</Copyright>", $"<Copyright>Copyright © {newCopyright}</Copyright>");
                File.WriteAllText(msiProps, xml);
            }

            var nuspec = ReleasePath / "choco" / "pyrevit-cli.nuspec";
            if (nuspec.FileExists())
            {
                var xml = File.ReadAllText(nuspec);
                xml = Regex.Replace(xml, @"<copyright>[^<]*</copyright>", $"<copyright>Copyright © {newCopyright}</copyright>", RegexOptions.IgnoreCase);
                File.WriteAllText(nuspec, xml);
            }
        });

    Target SetNextVersion => _ => _
        .Description("Increment patch in pyrevitlib/pyrevit/version and release/version, then git add and commit 'Next Version'.")
        .Executes(() =>
        {
            var verFile = PyRevitModulePath / "version";
            var line = File.ReadAllText(verFile).Trim();
            var m = Regex.Match(line, @"^(\d)\.(\d+)\.(\d+)(.*)$");
            if (!m.Success) throw new Exception("Version file format not recognized.");
            var nextVer = $"{m.Groups[1].Value}.{m.Groups[2].Value}.{int.Parse(m.Groups[3].Value) + 1}{m.Groups[4].Value}";
            File.WriteAllText(verFile, nextVer);
            File.WriteAllText(ReleasePath / "version", nextVer);
            RunProcess("git", $"add \"{verFile}\" \"{ReleasePath / "version"}\"", (string)RootDirectory);
            RunProcess("git", "commit -m \"Next Version\"", (string)RootDirectory);
        });

    Target BuildInstallers => _ => _
        .Description("Build Inno Setup (.iss) and MSI (.wixproj) installers. Requires iscc and msbuild on PATH.")
        .Executes(() =>
        {
            var issFiles = new[] { ReleasePath / "pyrevit.iss", ReleasePath / "pyrevit-cli.iss", ReleasePath / "pyrevit-admin.iss", ReleasePath / "pyrevit-cli-admin.iss" };
            foreach (var iss in issFiles)
            {
                if (!iss.FileExists()) continue;
                RunProcess("iscc", $"\"{iss}\"", (string)RootDirectory, captureOutput: true);
            }
            var wixproj = ReleasePath / "pyrevit-cli.wixproj";
            if (wixproj.FileExists())
                RunProcess("dotnet", $"build \"{wixproj}\" -c Release", (string)RootDirectory, captureOutput: true);
            DistPath.CreateDirectory();
            var nuspec = ReleasePath / "choco" / "pyrevit-cli.nuspec";
            if (nuspec.FileExists())
                RunProcess("choco", $"pack \"{nuspec}\" --outdir \"{DistPath}\"", (string)RootDirectory, captureOutput: true);
        });

    Target ReportSloc => _ => _
        .Description("Count SLOC (pygount). Requires pygount: pip install pygount.")
        .Executes(() =>
        {
            var srcDirs = $"\"{PyRevitModulePath}\" \"{DevPath}\"";
            RunProcess("pygount", $"--format=summary --suffix=cs,py,go --folders-to-skip modules {srcDirs}", (string)RootDirectory);
        });

    Target CommitAndTagBuild => _ => _
        .Description("Git add version/autocomp/release files, commit 'Publish!', tag v<version> and cli-v<version>.")
        .Executes(() =>
        {
            var verFile = PyRevitModulePath / "version";
            var ver = File.ReadAllText(verFile).Trim();
            RunProcess("git", "add dev/pyRevitLabs/pyRevitCLIAutoComplete/pyrevit-autocomplete.go dev/Directory.Build.props pyrevitlib/pyrevit/version pyrevitlib/pyrevit/versionmgr/about.py docs/conf.py README.md release/ bin/", (string)RootDirectory);
            RunProcess("git", "commit -m \"Publish!\"", (string)RootDirectory);
            RunProcess("git", $"tag v{ver}", (string)RootDirectory);
            RunProcess("git", $"tag cli-v{ver}", (string)RootDirectory);
        });

    Target SetProducts => _ => _
        .Description("Generate new MSI ProductCode, update release props and bin/pyrevit-products.json. Run before build installers for new version.")
        .Executes(() =>
        {
            var newGuid = Guid.NewGuid().ToString("B");
            var cliProps = ReleasePath / "pyrevit-cli.props";
            if (cliProps.FileExists())
            {
                var xml = File.ReadAllText(cliProps);
                xml = Regex.Replace(xml, @"<ProductIdCode>[^<]*</ProductIdCode>", $"<ProductIdCode>{newGuid}</ProductIdCode>");
                File.WriteAllText(cliProps, xml);
            }
            var verFile = PyRevitModulePath / "version";
            var ver = File.ReadAllText(verFile).Trim();
            var productsFile = BinPath / "pyrevit-products.json";
            BinPath.CreateDirectory();
            var list = productsFile.FileExists()
                ? JsonSerializer.Deserialize<List<Dictionary<string, JsonElement>>>(File.ReadAllText(productsFile)) ?? new List<Dictionary<string, JsonElement>>()
                : new List<Dictionary<string, JsonElement>>();
            var newEntry = new Dictionary<string, object> { ["product"] = "pyRevit CLI MSI", ["release"] = ver, ["version"] = ver, ["key"] = newGuid };
            var insertIdx = list.FindIndex(d => d.TryGetValue("product", out var p) && p.GetString()?.Contains("CLI") == true);
            if (insertIdx < 0) insertIdx = list.Count;
            var newElem = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(JsonSerializer.Serialize(newEntry));
            if (newElem != null) list.Insert(insertIdx, newElem);
            File.WriteAllText(productsFile, JsonSerializer.Serialize(list, new JsonSerializerOptions { WriteIndented = true }));
        });

    Target RunPyRevit => _ => _
        .Description("Run dev/pyrevit.py via pipenv. Use --run-pyrevit-args 'set locales' or 'report changelog', etc.")
        .Executes(() =>
        {
            var subArgs = string.IsNullOrWhiteSpace(RunPyRevitArgs) ? "help" : RunPyRevitArgs;
            RunProcess("pipenv", $"run pyrevit {subArgs}", (string)(RootDirectory / "dev"), captureOutput: true);
        });
}
