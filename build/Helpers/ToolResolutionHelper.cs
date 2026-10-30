using System.Diagnostics;

namespace Build.Helpers;

public static class ToolResolutionHelper
{
    public static string? ResolveOnPath(string command) => ResolveAllOnPath(command).FirstOrDefault();

    /// <summary>Every executable matching <paramref name="command"/> on PATH, in PATH order.</summary>
    public static IEnumerable<string> ResolveAllOnPath(string command)
    {
        var pathValue = Environment.GetEnvironmentVariable("PATH") ?? string.Empty;
        var extensions = OperatingSystem.IsWindows()
            ? (Environment.GetEnvironmentVariable("PATHEXT") ?? ".EXE;.CMD;.BAT").Split(';')
            : [string.Empty];
        var seen = new HashSet<string>(
            OperatingSystem.IsWindows() ? StringComparer.OrdinalIgnoreCase : StringComparer.Ordinal);

        foreach (var folder in pathValue.Split(Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries))
        {
            var trimmedFolder = folder.Trim().Trim('"');
            if (trimmedFolder.Length == 0)
            {
                continue;
            }

            foreach (var extension in extensions)
            {
                string candidate;
                try
                {
                    candidate = Path.Combine(trimmedFolder, command + extension);
                }
                catch (ArgumentException)
                {
                    continue;
                }

                if (File.Exists(candidate) && seen.Add(candidate))
                {
                    yield return candidate;
                }
            }
        }
    }

    public static string ResolveWingetCreateExecutable(string configuredExe)
    {
        if (string.IsNullOrWhiteSpace(configuredExe))
        {
            configuredExe = "wingetcreate.exe";
        }

        var isPath = Path.IsPathRooted(configuredExe)
            || configuredExe.Contains(Path.DirectorySeparatorChar)
            || configuredExe.Contains(Path.AltDirectorySeparatorChar);

        if (isPath)
        {
            var fullPath = Path.GetFullPath(configuredExe);
            if (File.Exists(fullPath))
            {
                return fullPath;
            }
        }

        var onPath = ResolveOnPath(Path.GetFileNameWithoutExtension(configuredExe));
        if (!string.IsNullOrWhiteSpace(onPath))
        {
            return onPath;
        }

        throw new FileNotFoundException(
            "wingetcreate.exe is required for WinGet publishing but was not found at the configured path and was not found on PATH. "
            + "Install it from https://aka.ms/wingetcreate/latest or set Publish__WingetCreateExe to a valid path.",
            configuredExe);
    }

    /// <summary>
    /// Finds the first Python launcher on PATH that is at least version 3.10.
    /// </summary>
    public static string ResolvePythonExecutable()
    {
        var python = new[] { "python", "python3", "py" }
            .Select(ResolveOnPath)
            .FirstOrDefault(candidate => !string.IsNullOrWhiteSpace(candidate) && IsPython310OrNewer(candidate));
        return python ?? throw new FileNotFoundException(
            "Python 3.10 or newer is required for the Revit API compatibility lint but was not found on PATH.");
    }

    private static bool IsPython310OrNewer(string executable)
    {
        var startInfo = new ProcessStartInfo(executable)
        {
            Arguments = "-c \"import sys; print(int(sys.version_info >= (3, 10)))\"",
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };

        try
        {
            using var process = Process.Start(startInfo);
            if (process is null)
            {
                return false;
            }

            var output = process.StandardOutput.ReadToEnd().Trim();
            process.WaitForExit();
            return process.ExitCode == 0 && output == "1";
        }
        catch (System.ComponentModel.Win32Exception)
        {
            return false;
        }
    }

    /// <summary>
    /// Resolves the PowerShell host for build scripts.
    /// </summary>
    /// <param name="minimumPwshVersion">
    /// Minimum version for a <c>pwsh</c> candidate. The version is read from the launched host, not from the
    /// launcher's file metadata, so a PATH shim does not hide a usable installation. Windows PowerShell is an
    /// accepted fallback; set this only when 5.1 is also acceptable (it supports <c>Remove-Item -DeleteKey</c>
    /// even though it is older).
    /// </param>
    public static string ResolvePowerShellExecutable(Version? minimumPwshVersion = null)
    {
        var pwshCandidates = ResolveAllOnPath("pwsh").ToArray();
        if (minimumPwshVersion is null)
        {
            var pwsh = pwshCandidates.FirstOrDefault();
            if (pwsh is not null)
            {
                return pwsh;
            }
        }
        else
        {
            var supported = pwshCandidates.FirstOrDefault(
                candidate => MeetsMinimumVersion(candidate, minimumPwshVersion));
            if (supported is not null)
            {
                return supported;
            }
        }

        var windowsPowerShell = OperatingSystem.IsWindows()
            ? Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.System),
                "WindowsPowerShell",
                "v1.0",
                "powershell.exe")
            : null;

        foreach (var fallback in new[] { windowsPowerShell, ResolveOnPath("powershell") })
        {
            if (!string.IsNullOrWhiteSpace(fallback) && File.Exists(fallback))
            {
                return fallback;
            }
        }

        throw new FileNotFoundException(
            minimumPwshVersion is null
                ? "PowerShell was not found. Install PowerShell 7 (pwsh) or ensure Windows PowerShell is available."
                : $"PowerShell {minimumPwshVersion} or later was not found, and Windows PowerShell is not available.");
    }

    private static bool MeetsMinimumVersion(string executable, Version minimum)
    {
        var startInfo = new ProcessStartInfo(executable)
        {
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        startInfo.ArgumentList.Add("-NoProfile");
        startInfo.ArgumentList.Add("-NonInteractive");
        startInfo.ArgumentList.Add("-Command");
        startInfo.ArgumentList.Add("$PSVersionTable.PSVersion.ToString()");

        try
        {
            using var process = Process.Start(startInfo);
            if (process is null)
            {
                return false;
            }

            var stdout = process.StandardOutput.ReadToEndAsync();
            _ = process.StandardError.ReadToEndAsync();
            if (!process.WaitForExit(TimeSpan.FromSeconds(15)))
            {
                process.Kill(entireProcessTree: true);
                process.WaitForExit();
                return false;
            }

            if (process.ExitCode != 0)
            {
                return false;
            }

            var versionText = stdout.GetAwaiter().GetResult().Trim();
            var prereleaseMarker = versionText.IndexOf('-');
            if (prereleaseMarker >= 0)
            {
                versionText = versionText[..prereleaseMarker];
            }

            return Version.TryParse(versionText, out var version) && version >= minimum;
        }
        catch (Exception)
        {
            return false;
        }
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
