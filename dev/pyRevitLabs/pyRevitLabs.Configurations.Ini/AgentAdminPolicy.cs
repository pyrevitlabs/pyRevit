using System.Text.RegularExpressions;
using IniParser.Model;
using IniParser.Parser;
using pyRevitLabs.Common;
using pyRevitLabs.Configurations.Abstractions;

namespace pyRevitLabs.Configurations.Ini;

/// <summary>
/// Agent-host settings an administrator pinned in the machine-wide config.
/// A null member means the key is not pinned.
/// </summary>
/// <remarks>
/// <see cref="Load"/> keeps the strings found in one file. <see cref="Current"/> combines every
/// config file in the machine config folder into the strictest value per key, so which file
/// pyRevit happens to treat as "the" machine config does not matter.
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
    private static string? cachedKey;
    private static string? pathOverride;
    private static string? directoryOverride;

    private AgentAdminPolicy() { }

    /// <summary>The <c>enabled</c> pin, or null when not pinned. Empty when the key is present but blank.</summary>
    public string? Enabled { get; private set; }

    /// <summary>The <c>policy</c> ceiling, or null when not pinned. Empty when the key is present but blank.</summary>
    public string? Policy { get; private set; }

    /// <summary>The <c>engine</c> pin, or null when not pinned. Empty when the key is present but blank.</summary>
    public string? Engine { get; private set; }

    /// <summary>The <c>user_skills</c> pin, or null when not pinned. Empty when the key is present but blank.</summary>
    public string? UserSkills { get; private set; }

    /// <summary>True when no key is pinned.</summary>
    public bool IsEmpty => Enabled == null && Policy == null && Engine == null && UserSkills == null;

    /// <summary>
    /// True when a machine config file could not be read, so the pins are the strictest
    /// ones rather than what the files say.
    /// </summary>
    public bool ReadFailed { get; private set; }

    /// <summary>
    /// The pins currently in force, combined from every config file in the machine config folder
    /// and cached by their modification times, so a lock applied while Revit runs is seen on the
    /// next read.
    /// </summary>
    /// <remarks>
    /// Important: the folder is the OS common-application-data one, never
    /// <c>PYREVIT_PROGRAMDATA_PATH_OVERRIDE</c>. Honoring that variable would let any user point the
    /// lock at an empty folder.
    /// Invariant: every config-named ini in the folder counts, not only the one pyRevit's lookup
    /// prefers. Otherwise a user who can create files there could add a file the lookup prefers and
    /// hide the real one. Per key the strictest value wins, so an extra file can only tighten.
    /// A missing folder or file pins nothing. A file that cannot be read or parsed, or a folder that
    /// cannot be listed, fails closed (see <see cref="Load"/>) and is not cached, so the next read
    /// tries again.
    /// </remarks>
    public static AgentAdminPolicy Current {
        get {
            List<string> paths;
            try {
                paths = CandidatePaths();
            }
            catch (Exception ex) {
                ConfigurationDiagnostics.ReportWarning(
                    "Could not list the machine config folder for agent admin settings: " + ex.Message);
                return FailedRead();
            }

            string key = string.Join("|", paths.Select(path => path + "@" + SafeStamp(path)));
            lock (CacheLock) {
                if (cached != null && cachedKey == key)
                    return cached;

                AgentAdminPolicy loaded = LoadAll(paths);
                if (loaded.ReadFailed) {
                    cached = null;
                    return loaded;
                }

                cached = loaded;
                cachedKey = key;
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
    /// Important: a file that exists but cannot be read or parsed fails closed, as
    /// <c>enabled = false</c>, <c>policy = readonly</c> and <c>user_skills = false</c>. Treating it
    /// as "nothing pinned" would let anyone who can read the file but not write it, which is every
    /// standard user, lift the lock by holding the file open while Revit starts.
    /// A key that is present but blank (<c>enabled =</c>, as an unset template variable leaves it)
    /// is a pin with an invalid value, not an absent pin, so it fails closed too: it is returned as
    /// an empty string and the consumer reads it as the strictest value.
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

    private static AgentAdminPolicy LoadAll(IReadOnlyList<string> paths) {
        var loaded = new List<AgentAdminPolicy>();
        foreach (string path in paths) {
            AgentAdminPolicy policy = Load(path);
            if (policy.ReadFailed)
                return policy;
            loaded.Add(policy);
        }
        return Merge(loaded);
    }

    private static AgentAdminPolicy Merge(List<AgentAdminPolicy> policies) => new AgentAdminPolicy {
        Enabled = Combine(policies.Select(policy => policy.Enabled), StrictestFlag),
        Policy = Combine(policies.Select(policy => policy.Policy), StrictestPolicy),
        Engine = Combine(policies.Select(policy => policy.Engine), StrictestEngine),
        UserSkills = Combine(policies.Select(policy => policy.UserSkills), StrictestFlag),
    };

    private static string? Combine(IEnumerable<string?> values, Func<List<string>, string> strictest) {
        List<string> present = values.Where(value => value != null).Select(value => value!).ToList();
        return present.Count == 0 ? null : strictest(present);
    }

    private static string StrictestFlag(List<string> values) =>
        values.All(value => bool.TryParse(value, out bool flag) && flag) ? "true" : "false";

    private static string StrictestPolicy(List<string> values) =>
        values.Select(NormalizePolicy).OrderBy(PolicyRank).First();

    private static string NormalizePolicy(string value) {
        string normalized = value.Trim().ToLowerInvariant();
        return normalized == "ask" || normalized == "auto" ? normalized : "readonly";
    }

    private static int PolicyRank(string policy) => policy == "readonly" ? 0 : policy == "ask" ? 1 : 2;

    private static string StrictestEngine(List<string> values) {
        List<string> distinct = values.Select(value => value.Trim().ToLowerInvariant()).Distinct().ToList();
        bool agreed = distinct.Count == 1 && (distinct[0] == "ironpython" || distinct[0] == "cpython");
        return agreed ? distinct[0] : "ironpython";
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

    private static string RealMachineConfigDirectory => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData),
        PyRevitLabsConsts.AppdataDirName);

    /// <summary>The machine config path pyRevit's own lookup resolves to.</summary>
    public static string ResolveMachineConfigPath() =>
        PyRevitInstallScope.FindConfigIniInDirectory(RealMachineConfigDirectory)
        ?? Path.Combine(RealMachineConfigDirectory, PyRevitLabsConsts.DefaultConfigsFileName);

    private static string MachineConfigDirectory => directoryOverride ?? RealMachineConfigDirectory;

    /// <summary>
    /// The machine config file new pins are written to: the one pyRevit's own lookup resolves to,
    /// or the default file name when the folder has none.
    /// </summary>
    public static string MachineConfigPath =>
        pathOverride
        ?? PyRevitInstallScope.FindConfigIniInDirectory(MachineConfigDirectory)
        ?? Path.Combine(MachineConfigDirectory, PyRevitLabsConsts.DefaultConfigsFileName);

    /// <summary>
    /// Every file that can carry a pin: all config-named inis in the machine config folder, or the
    /// default config path when the folder holds none.
    /// </summary>
    private static List<string> CandidatePaths() {
        if (pathOverride != null)
            return new List<string> { pathOverride };

        List<string> found = PyRevitInstallScope.FindAllConfigIniInDirectory(MachineConfigDirectory).ToList();
        return found.Count > 0 ? found : new List<string> { MachineConfigPath };
    }

    /// <summary>
    /// Pins <paramref name="key"/> to <paramref name="value"/> in <see cref="MachineConfigPath"/>,
    /// creating the file when missing, and removes the same pin from any other config file in the
    /// folder so the value written is the one in force. The caller validates the value.
    /// </summary>
    /// <remarks>
    /// Side effects: rewrites machine config files. A file carrying the ReadOnly attribute (a seeded
    /// admin lock) is unlocked for the write and locked again afterwards.
    /// The caller is responsible for requiring elevation.
    /// </remarks>
    /// <exception cref="ArgumentException"><paramref name="key"/> is not a lockable key.</exception>
    /// <exception cref="InvalidDataException">
    /// A machine config file cannot be read or parsed. Nothing is written, so no setting in it is lost.
    /// </exception>
    public static void SetPin(string key, string value) {
        EnsureKnownKey(key);
        string target = MachineConfigPath;
        List<string> others = ExistingCandidates().Where(path => !SamePath(path, target)).ToList();
        foreach (string path in others)
            RequireParseable(path);
        if (File.Exists(target))
            RequireParseable(target);

        foreach (string path in others.Where(path => HasPin(path, key)))
            EditFile(path, configuration => configuration.RemoveOption(SectionName, key));
        EditFile(target, configuration => configuration.SetValue(SectionName, key, value));
    }

    /// <summary>Removes the pin on <paramref name="key"/> from every machine config file.</summary>
    /// <inheritdoc cref="SetPin" path="/remarks"/>
    /// <exception cref="ArgumentException"><paramref name="key"/> is not a lockable key.</exception>
    /// <exception cref="InvalidDataException">
    /// A machine config file cannot be read or parsed. Nothing is written.
    /// </exception>
    public static void ClearPin(string key) {
        EnsureKnownKey(key);
        List<string> files = ExistingCandidates();
        foreach (string path in files)
            RequireParseable(path);
        foreach (string path in files.Where(path => HasPin(path, key)))
            EditFile(path, configuration => configuration.RemoveOption(SectionName, key));
    }

    /// <summary>Removes every pin from every machine config file.</summary>
    /// <inheritdoc cref="SetPin" path="/remarks"/>
    /// <exception cref="InvalidDataException">
    /// A machine config file cannot be read or parsed. Nothing is written.
    /// </exception>
    public static void ClearAllPins() {
        List<string> files = ExistingCandidates();
        foreach (string path in files)
            RequireParseable(path);
        foreach (string path in files.Where(path => ParseIni(ReadAllText(path)).Sections.ContainsSection(SectionName)))
            EditFile(path, configuration => configuration.RemoveSection(SectionName));
    }

    private static List<string> ExistingCandidates() =>
        CandidatePaths().Where(File.Exists).ToList();

    private static bool SamePath(string first, string second) =>
        string.Equals(Path.GetFullPath(first), Path.GetFullPath(second), StringComparison.OrdinalIgnoreCase);

    private static bool HasPin(string path, string key) => Read(ParseIni(ReadAllText(path)), key) != null;

    private static void EnsureKnownKey(string key) {
        if (key != EnabledKey && key != PolicyKey && key != EngineKey && key != UserSkillsKey)
            throw new ArgumentException("Not a lockable agent setting: " + key, nameof(key));
    }

    /// <summary>
    /// <see cref="IniConfiguration"/> moves a file it cannot parse aside and starts empty, so saving
    /// after that would replace the whole machine config with only the new pin. Parse strictly first.
    /// </summary>
    private static void RequireParseable(string path) {
        try {
            ParseIni(ReadAllText(path));
        }
        catch (Exception ex) {
            throw new InvalidDataException(
                "The machine config \"" + path + "\" can't be read or parsed (" + ex.Message + "). "
                + "Fix or remove it before changing agent locks, so nothing in it is lost.", ex);
        }
    }

    /// <summary>
    /// Applies <paramref name="edit"/> and swaps the result in with a single replace, so a reader
    /// never sees a half-written file: a truncated one would parse as "nothing pinned".
    /// </summary>
    /// <remarks>
    /// <see cref="File.Replace(string, string, string?)"/> keeps the replaced file's permissions and
    /// attributes, which is what keeps the restricted ACL <c>lock</c> applied.
    /// </remarks>
    private static void EditFile(string path, Action<IConfiguration> edit) {
        bool wasReadOnly = PyRevitInstallScope.HasReadOnlyAttribute(path);
        if (wasReadOnly)
            File.SetAttributes(path, File.GetAttributes(path) & ~FileAttributes.ReadOnly);
        string temporary = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
        try {
            IConfiguration configuration = IniConfiguration.Create(path);
            edit(configuration);
            configuration.SaveConfiguration(temporary);
            if (File.Exists(path))
                File.Replace(temporary, path, null);
            else
                File.Move(temporary, path);
        }
        finally {
            if (File.Exists(temporary))
                File.Delete(temporary);
            if (wasReadOnly)
                File.SetAttributes(path, File.GetAttributes(path) | FileAttributes.ReadOnly);
            lock (CacheLock)
                cached = null;
        }
    }

    internal static void OverrideMachineConfigPath(string? path) {
        lock (CacheLock) {
            pathOverride = path;
            directoryOverride = null;
            cached = null;
        }
    }

    internal static void OverrideMachineConfigDirectory(string? directory) {
        lock (CacheLock) {
            directoryOverride = directory;
            pathOverride = null;
            cached = null;
        }
    }

    private static string? Read(IniData data, string key) {
        if (!data.Sections.ContainsSection(SectionName) || !data[SectionName].ContainsKey(key))
            return null;
        return (data[SectionName][key] ?? string.Empty).Trim().Trim('"').Trim();
    }

    /// <summary>
    /// Modification time and length, so a read that lands between a writer's truncate and its last
    /// write, and so sees a shorter file, can't be cached under the key of the finished file.
    /// </summary>
    private static string SafeStamp(string path) {
        try {
            return File.Exists(path)
                ? File.GetLastWriteTimeUtc(path).Ticks + ":" + new FileInfo(path).Length
                : "missing";
        }
        catch {
            return "unknown";
        }
    }
}
