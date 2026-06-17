using System.Diagnostics;

namespace Build.Helpers;

public static class ToolResolutionHelper
{
    public static string? ResolveOnPath(string command)
    {
        var pathValue = Environment.GetEnvironmentVariable("PATH") ?? string.Empty;
        var extensions = OperatingSystem.IsWindows()
            ? (Environment.GetEnvironmentVariable("PATHEXT") ?? ".EXE;.CMD;.BAT").Split(';')
            : [string.Empty];

        foreach (var folder in pathValue.Split(Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries))
        {
            foreach (var extension in extensions)
            {
                var candidate = Path.Combine(folder.Trim(), command + extension);
                if (File.Exists(candidate))
                {
                    return candidate;
                }
            }
        }

        return null;
    }

    public static string ResolvePowerShellExecutable()
    {
        var candidates = new[]
        {
            ResolveOnPath("pwsh"),
            OperatingSystem.IsWindows()
                ? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System), "WindowsPowerShell", "v1.0", "powershell.exe")
                : null,
            ResolveOnPath("powershell"),
        };

        foreach (var candidate in candidates)
        {
            if (!string.IsNullOrWhiteSpace(candidate) && File.Exists(candidate))
            {
                return candidate;
            }
        }

        throw new FileNotFoundException("PowerShell was not found. Install PowerShell 7 (pwsh) or ensure Windows PowerShell is available.");
    }

    public static string? ResolveMsBuildExecutable()
    {
        var onPath = ResolveOnPath("msbuild");
        if (!string.IsNullOrWhiteSpace(onPath))
        {
            return onPath;
        }

        var vswhere = ResolveVsWhereExecutable();
        if (string.IsNullOrWhiteSpace(vswhere))
        {
            return null;
        }

        foreach (var arguments in new[]
        {
            "-latest -requires Microsoft.Component.MSBuild -find MSBuild\\**\\Bin\\MSBuild.exe",
            "-latest -prerelease -requires Microsoft.Component.MSBuild -find MSBuild\\**\\Bin\\MSBuild.exe",
        })
        {
            var msbuild = ResolveMsBuildWithVsWhere(vswhere, arguments);
            if (!string.IsNullOrWhiteSpace(msbuild))
            {
                return msbuild;
            }
        }

        return null;
    }

    private static string? ResolveVsWhereExecutable()
    {
        var candidates = new[]
        {
            ResolveOnPath("vswhere"),
            OperatingSystem.IsWindows()
                ? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), "Microsoft Visual Studio", "Installer", "vswhere.exe")
                : null,
            OperatingSystem.IsWindows()
                ? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "Microsoft Visual Studio", "Installer", "vswhere.exe")
                : null,
        };

        return candidates.FirstOrDefault(candidate => !string.IsNullOrWhiteSpace(candidate) && File.Exists(candidate));
    }

    private static string? ResolveMsBuildWithVsWhere(string vswhere, string arguments)
    {
        var startInfo = new ProcessStartInfo(vswhere)
        {
            Arguments = arguments,
            RedirectStandardOutput = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };

        using var process = Process.Start(startInfo);
        if (process is null)
        {
            return null;
        }

        var output = process.StandardOutput.ReadToEnd().Trim();
        process.WaitForExit();
        var firstLine = output.Split(['\r', '\n'], StringSplitOptions.RemoveEmptyEntries).FirstOrDefault();
        return !string.IsNullOrWhiteSpace(firstLine) && File.Exists(firstLine) ? firstLine : null;
    }
}
