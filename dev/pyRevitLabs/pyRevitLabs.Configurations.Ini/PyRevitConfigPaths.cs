using pyRevitLabs.Common;

namespace pyRevitLabs.Configurations.Ini;

/// <summary>
/// Thin adapter over pyRevitLabs.Common's install-scope and path helpers, so the
/// config store, the CLI, and the loader resolve the same per-user and all-users
/// paths from a single source of truth (<see cref="PyRevitLabsConsts"/> plus
/// <see cref="PyRevitInstallScope"/>). Honors the path-override env vars those
/// helpers read, which keeps discovery testable without touching real machine dirs.
/// </summary>
public static class PyRevitConfigPaths
{
    public static string DefaultConfigsFileName => PyRevitLabsConsts.DefaultConfigsFileName;

    public static string PyRevitAppDataPath => PyRevitLabsConsts.PyRevitPath;

    public static string PyRevitProgramDataPath => PyRevitLabsConsts.PyRevitProgramDataPath;

    /// <summary>
    /// Writable per-user config target: the first matching file under %APPDATA%,
    /// else the default file name there.
    /// </summary>
    public static string UserConfigFilePath =>
        FindConfigFileInDirectory(PyRevitAppDataPath)
        ?? Path.Combine(PyRevitAppDataPath, DefaultConfigsFileName);

    /// <summary>
    /// All-users config: the first matching file under %ProgramData%, else the
    /// default file name there.
    /// </summary>
    public static string AdminConfigFilePath =>
        FindConfigFileInDirectory(PyRevitProgramDataPath)
        ?? Path.Combine(PyRevitProgramDataPath, DefaultConfigsFileName);

    /// <summary>
    /// True when the install is machine-wide (all-users marker, a Program Files
    /// install root, or a scope override).
    /// </summary>
    public static bool IsInstallAllUsers() => PyRevitInstallScope.IsAllUsersInstall();

    /// <summary>
    /// Returns the first config-named file in <paramref name="directory"/>, or null.
    /// </summary>
    public static string? FindConfigFileInDirectory(string directory)
        => PyRevitInstallScope.FindConfigIniInDirectory(directory);
}
