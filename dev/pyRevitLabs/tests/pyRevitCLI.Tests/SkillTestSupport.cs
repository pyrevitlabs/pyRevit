using System.Diagnostics;

namespace pyRevitCLI.Tests;

/// <summary>
/// Creates directory junctions for the link tests and says whether that works on this machine.
/// </summary>
internal static class LinkSupport {
    private static readonly Lazy<bool> Probed = new Lazy<bool>(Probe);

    public static bool Available => Probed.Value;

    public static bool MakeJunction(string link, string target) {
        try {
            var start = new ProcessStartInfo("cmd.exe", $"/c mklink /J \"{link}\" \"{target}\"") { CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true };
            using var process = Process.Start(start);
            process.StandardOutput.ReadToEnd();
            process.WaitForExit();
            return process.ExitCode == 0 && Directory.Exists(link);
        }
        catch (Exception) {
            return false;
        }
    }

    private static bool Probe() {
        if (!OperatingSystem.IsWindows())
            return false;
        var root = Directory.CreateTempSubdirectory("pyrevit-link-probe-").FullName;
        try {
            var target = Directory.CreateDirectory(Path.Combine(root, "target")).FullName;
            var link = Path.Combine(root, "link");
            var made = MakeJunction(link, target);
            if (made)
                Directory.Delete(link);
            return made;
        }
        finally {
            Directory.Delete(root, recursive: true);
        }
    }
}

/// <summary>
/// A fact that is skipped when directory junctions cannot be created.
/// </summary>
public sealed class LinkFactAttribute : FactAttribute {
    public LinkFactAttribute() {
        if (!LinkSupport.Available)
            Skip = "Junctions cannot be created on this machine.";
    }
}

/// <summary>
/// A fact that is skipped off Windows, where open files block renaming their folder.
/// </summary>
public sealed class WindowsFactAttribute : FactAttribute {
    public WindowsFactAttribute() {
        if (!OperatingSystem.IsWindows())
            Skip = "Needs Windows file locking semantics.";
    }
}

/// <summary>
/// Finds the repository's own shipped skills folder from the test binary, not from the machine's clones.
/// </summary>
internal static class RepoSkills {
    public static string Directory { get; } = Find();

    private static string Find() {
        for (var directory = new DirectoryInfo(AppContext.BaseDirectory); directory != null; directory = directory.Parent) {
            var candidate = Path.Combine(directory.FullName, "pyrevitlib", "pyrevit", "agent", "skills");
            if (System.IO.Directory.Exists(candidate))
                return candidate;
        }
        return null;
    }
}

/// <summary>
/// A fact that is skipped when the repository's skills folder is not above the test binary.
/// </summary>
public sealed class RepoSkillsFactAttribute : FactAttribute {
    public RepoSkillsFactAttribute() {
        if (RepoSkills.Directory == null)
            Skip = "pyrevitlib/pyrevit/agent/skills was not found above the test binary.";
    }
}
