using System.Diagnostics;
using System.Reflection;
using pyRevitLabs.Common;

namespace pyRevitCLI.Tests;

/// <summary>Exercises the built command-line entry point in an isolated process.</summary>
[Trait("Environment", "HostFree")]
[Trait("Level", "E2E")]
public class CliHelpTests {
    /// <summary>Help must work without a configured clone, network, or Revit installation.</summary>
    [Fact]
    public async Task HelpExitsSuccessfullyAndDescribesCommands() {
        var root = new DirectoryInfo(AppContext.BaseDirectory);
        while (root != null && !File.Exists(Path.Combine(root.FullName, "pyRevitfile")))
            root = root.Parent;
        Assert.NotNull(root);
        var configuration = typeof(CliHelpTests).Assembly.GetCustomAttribute<AssemblyConfigurationAttribute>()!.Configuration;
        var cliPath = Path.Combine(root.FullName, "dev", "pyRevitLabs", "pyRevitCLI", "bin", configuration, "net8.0-windows", "pyrevit.dll");
        Assert.True(File.Exists(cliPath), $"CLI build is missing: {cliPath}");
        var temporary = Directory.CreateTempSubdirectory("pyrevit-cli-help-").FullName;
        try {
            var start = new ProcessStartInfo("dotnet") {
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                WorkingDirectory = temporary,
            };
            start.ArgumentList.Add(cliPath);
            start.ArgumentList.Add("--help");
            start.Environment[PyRevitLabsConsts.PyRevitPathOverrideEnvVar] = Path.Combine(temporary, "user");
            start.Environment[PyRevitLabsConsts.PyRevitProgramDataPathOverrideEnvVar] = Path.Combine(temporary, "machine");
            using var process = Process.Start(start)!;
            var output = process.StandardOutput.ReadToEndAsync();
            var error = process.StandardError.ReadToEndAsync();
            using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(30));
            try {
                await process.WaitForExitAsync(timeout.Token);
            }
            finally {
                if (!process.HasExited) process.Kill(entireProcessTree: true);
            }
            Assert.True(process.ExitCode == 0, await error);
            Assert.Contains("pyrevit", await output, StringComparison.OrdinalIgnoreCase);
            Assert.Contains("Usage", await output, StringComparison.OrdinalIgnoreCase);
        }
        finally {
            Directory.Delete(temporary, recursive: true);
        }
    }
}
