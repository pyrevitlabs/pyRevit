using System.Text.RegularExpressions;
using IniParser.Model;
using IniParser.Parser;
using pyRevitLabs.Common;
using pyRevitLabs.Configurations.Abstractions;

namespace pyRevitLabs.Configurations.Ini;

/// <summary>
/// Raw agent-host settings an administrator pinned in the machine-wide config.
/// A null member means the key is not pinned.
/// </summary>
/// <remarks>
/// Values are kept as the strings found in the file; interpreting them (and failing
/// closed on malformed ones) is the consumer's job because it owns the accepted
/// value sets.
/// </remarks>
public sealed class AgentAdminPolicy {
    /// <summary>INI section holding the pinned keys. Written only by the admin lock command.</summary>
    public const string SectionName = PyRevitInstallScope.AgentAdminSectionName;

    /// <summary>Key pinning whether the agent host runs.</summary>
    public const string EnabledKey = "enabled";

    /// <summary>Key capping what agent runs may do.</summary>
    public const string PolicyKey = "policy";

    /// <summary>Key pinning the default script engine.</summary>
    public const string EngineKey = "engine";

    /// <summary>Key pinning whether user-authored skills load.</summary>
    public const string UserSkillsKey = "user_skills";

    private static readonly object CacheLock = new();
    private static AgentAdminPolicy? cached;
    private static string? cachedPath;
    private static DateTime cachedStamp;
    private static string? pathOverride;

    private AgentAdminPolicy() { }

    /// <summary>The raw <c>enabled</c> pin, or null when not pinned.</summary>
    public string? Enabled { get; private set; }

    /// <summary>The raw <c>policy</c> ceiling, or null when not pinned.</summary>
    public string? Policy { get; private set; }

    /// <summary>The raw <c>engine</c> pin, or null when not pinned.</summary>
    public string? Engine { get; private set; }

    /// <summary>The raw <c>user_skills</c> pin, or null when not pinned.</summary>
    public string? UserSkills { get; private set; }

    /// <summary>True when no key is pinned.</summary>
    public bool IsEmpty => Enabled == null && Policy == null && Engine == null && UserSkills == null;

    /// <summary>
    /// True when the machine config exists but could not be read, so the pins are the strictest
    /// ones rather than what the file says.
    /// </summary>
    public bool ReadFailed { get; private set; }

    /// <summary>
    /// The pins currently in force, read from the machine config and cached by its
    /// modification time so a lock applied while Revit runs is seen on the next read.
    /// </summary>
    /// <remarks>
    /// Important: the machine config is located from the OS common-application-data folder,
    /// never from <c>PYREVIT_PROGRAMDATA_PATH_OVERRIDE</c>. Honoring that variable would let any
    /// user point the lock at an empty folder.
    /// A missing file pins nothing. A file that exists but cannot be read, for example because
    /// another process holds it open exclusively, fails closed (see <see cref="Load"/>) and is
    /// not cached, so the next read tries again.
    /// </remarks>
    public static AgentAdminPolicy Current {
        get {
            string path = MachineConfigPath;
            DateTime stamp = SafeLastWriteUtc(path);
            lock (CacheLock) {
                if (cached != null && cachedPath == path && cachedStamp == stamp)
                    return cached;

                AgentAdminPolicy loaded = Load(path);
                if (loaded.ReadFailed) {
                    cached = null;
                    return loaded;
                }

                cached = loaded;
                cachedPath = path;
                cachedStamp = stamp;
                return loaded;
            }
        }
    }

    /// <summary>
    /// Reads the pins from <paramref name="configPath"/>. Only the <c>[agent.admin]</c> section
    /// counts: a plain <c>[agent]</c> section in the machine config is a seeded copy of someone's
    /// settings, not a lock.
    /// </summary>
    /// <remarks>
    /// Important: a file that exists but cannot be read fails closed, as <c>enabled = false</c>,
    /// <c>policy = readonly</c> and <c>user_skills = false</c>. Treating it as "nothing pinned"
    /// would let anyone who can read the file but not write it, which is every standard user, lift
    /// the lock by holding the file open while Revit starts.
    /// </remarks>
    public static AgentAdminPolicy Load(string configPath) {
        var policy = new AgentAdminPolicy();
        if (string.IsNullOrEmpty(configPath) || !File.Exists(configPath))
            return policy;

        try {
            IniData data = ParseIni(ReadAllText(configPath));
            policy.Enabled = Read(data, EnabledKey);
            policy.Policy = Read(data, PolicyKey);
            policy.Engine = Read(data, EngineKey);
            policy.UserSkills = Read(data, UserSkillsKey);
        }
        catch (Exception ex) {
            ConfigurationDiagnostics.ReportWarning(
                "Could not read agent admin settings from " + configPath + ": " + ex.Message);
            return FailedRead();
        }
        return policy;
    }

    /// <summary>
    /// Reads the file text itself instead of going through <see cref="IniConfiguration"/>, which
    /// treats a file it cannot read as empty. That fallback is right for a user config and wrong
    /// here, where an empty read would lift the lock.
    /// </summary>
    private static string ReadAllText(string configPath) {
        using var stream = new FileStream(
            configPath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
        using var reader = new StreamReader(stream, IniConfiguration.DefaultFileEncoding, true);
        return reader.ReadToEnd();
    }

    private static IniData ParseIni(string text) {
        var parser = new IniDataParser();
        parser.Configuration.CaseInsensitive = true;
        parser.Configuration.CommentRegex = new Regex(@"^\s*[#;](.*)", RegexOptions.Compiled);
        parser.Configuration.SkipInvalidLines = false;
        parser.Configuration.AllowDuplicateSections = true;
        parser.Configuration.AllowDuplicateKeys = true;
        parser.Configuration.OverrideDuplicateKeys = true;
        return parser.Parse(text);
    }

    private static AgentAdminPolicy FailedRead() => new AgentAdminPolicy {
        Enabled = "false",
        Policy = "readonly",
        UserSkills = "false",
        ReadFailed = true,
    };

    /// <summary>The machine config path the lock is read from.</summary>
    public static string ResolveMachineConfigPath() {
        string directory = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData),
            PyRevitLabsConsts.AppdataDirName);
        return PyRevitInstallScope.FindConfigIniInDirectory(directory)
            ?? Path.Combine(directory, PyRevitLabsConsts.DefaultConfigsFileName);
    }

    /// <summary>The machine config the lock is read from and written to.</summary>
    public static string MachineConfigPath => pathOverride ?? ResolveMachineConfigPath();

    /// <summary>
    /// Pins <paramref name="key"/> to <paramref name="value"/> in the machine config, creating the
    /// file when missing. The caller validates the value.
    /// </summary>
    /// <remarks>
    /// Side effects: rewrites the machine config. A file carrying the ReadOnly attribute (a seeded
    /// admin lock) is unlocked for the write and locked again afterwards.
    /// The caller is responsible for requiring elevation.
    /// </remarks>
    /// <exception cref="ArgumentException"><paramref name="key"/> is not a lockable key.</exception>
    public static void SetPin(string key, string value) {
        EnsureKnownKey(key);
        EditPins(configuration => configuration.SetValue(SectionName, key, value));
    }

    /// <summary>Removes the pin on <paramref name="key"/>. Does nothing when it is not pinned.</summary>
    /// <inheritdoc cref="SetPin" path="/remarks"/>
    /// <exception cref="ArgumentException"><paramref name="key"/> is not a lockable key.</exception>
    public static void ClearPin(string key) {
        EnsureKnownKey(key);
        if (!File.Exists(MachineConfigPath))
            return;
        EditPins(configuration => configuration.RemoveOption(SectionName, key));
    }

    /// <summary>Removes every pin. Does nothing when the machine config does not exist.</summary>
    /// <inheritdoc cref="SetPin" path="/remarks"/>
    public static void ClearAllPins() {
        if (!File.Exists(MachineConfigPath))
            return;
        EditPins(configuration => configuration.RemoveSection(SectionName));
    }

    private static void EnsureKnownKey(string key) {
        if (key != EnabledKey && key != PolicyKey && key != EngineKey && key != UserSkillsKey)
            throw new ArgumentException("Not a lockable agent setting: " + key, nameof(key));
    }

    private static void EditPins(Action<IConfiguration> edit) {
        string path = MachineConfigPath;
        bool wasReadOnly = PyRevitInstallScope.HasReadOnlyAttribute(path);
        if (wasReadOnly)
            File.SetAttributes(path, File.GetAttributes(path) & ~FileAttributes.ReadOnly);
        try {
            IConfiguration configuration = IniConfiguration.Create(path);
            edit(configuration);
            configuration.SaveConfiguration();
        }
        finally {
            if (wasReadOnly)
                File.SetAttributes(path, File.GetAttributes(path) | FileAttributes.ReadOnly);
            lock (CacheLock)
                cached = null;
        }
    }

    internal static void OverrideMachineConfigPath(string? path) {
        lock (CacheLock) {
            pathOverride = path;
            cached = null;
        }
    }

    private static string? Read(IniData data, string key) {
        if (!data.Sections.ContainsSection(SectionName))
            return null;
        string? value = data[SectionName][key]?.Trim().Trim('"').Trim();
        return string.IsNullOrEmpty(value) ? null : value;
    }

    private static DateTime SafeLastWriteUtc(string path) {
        try {
            return File.Exists(path) ? File.GetLastWriteTimeUtc(path) : DateTime.MinValue;
        }
        catch {
            return DateTime.MinValue;
        }
    }
}
