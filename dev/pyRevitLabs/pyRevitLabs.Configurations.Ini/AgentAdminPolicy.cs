using pyRevitLabs.Common;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Ini.Extensions;

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
    public const string SectionName = "agent.admin";

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
    /// The pins currently in force, read from the machine config and cached by its
    /// modification time so a lock applied while Revit runs is seen on the next read.
    /// </summary>
    /// <remarks>
    /// Important: the machine config is located from the OS common-application-data folder,
    /// never from <c>PYREVIT_PROGRAMDATA_PATH_OVERRIDE</c>. Honoring that variable would let any
    /// user point the lock at an empty folder.
    /// A missing or unreadable file pins nothing.
    /// </remarks>
    public static AgentAdminPolicy Current {
        get {
            string path = pathOverride ?? ResolveMachineConfigPath();
            DateTime stamp = SafeLastWriteUtc(path);
            lock (CacheLock) {
                if (cached == null || cachedPath != path || cachedStamp != stamp) {
                    cached = Load(path);
                    cachedPath = path;
                    cachedStamp = stamp;
                }
                return cached;
            }
        }
    }

    /// <summary>
    /// Reads the pins from <paramref name="configPath"/>. Only the <c>[agent.admin]</c> section
    /// counts: a plain <c>[agent]</c> section in the machine config is a seeded copy of someone's
    /// settings, not a lock.
    /// </summary>
    public static AgentAdminPolicy Load(string configPath) {
        var policy = new AgentAdminPolicy();
        if (string.IsNullOrEmpty(configPath) || !File.Exists(configPath))
            return policy;

        try {
            IConfigurationService service = new ConfigurationBuilder(true)
                .AddIniConfiguration(configPath, true)
                .Build();
            policy.Enabled = Read(service, EnabledKey);
            policy.Policy = Read(service, PolicyKey);
            policy.Engine = Read(service, EngineKey);
            policy.UserSkills = Read(service, UserSkillsKey);
        }
        catch (Exception ex) {
            ConfigurationDiagnostics.ReportWarning(
                "Could not read agent admin settings from " + configPath + ": " + ex.Message);
            return new AgentAdminPolicy();
        }
        return policy;
    }

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

    private static string? Read(IConfigurationService service, string key) {
        string? value = service.GetSectionKeyValueOrDefault<string>(SectionName, key, null);
        return value == null || value.Trim().Length == 0 ? null : value.Trim();
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
