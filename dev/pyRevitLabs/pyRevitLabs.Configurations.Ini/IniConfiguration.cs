using System.Text;
using System.Text.RegularExpressions;
using IniParser;
using IniParser.Model;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Exceptions;
using pyRevitLabs.Json;

namespace pyRevitLabs.Configurations.Ini;

/// <summary>
/// INI-backed <see cref="IConfiguration"/>. Values are stored as canonical JSON
/// text, and reads tolerate the older encodings pyRevit configs carry in the
/// wild: Python-style booleans, hex integers, bare unquoted strings, and
/// single-quoted Python list literals. Parsing is deliberately forgiving —
/// see <see cref="Create"/>.
/// </summary>
public sealed class IniConfiguration : ConfigurationBase
{
    /// <summary>File extension used for pyRevit configuration files.</summary>
    public static readonly string DefaultFileExtension = ".ini";

    /// <summary>
    /// Encoding used to read and write configuration files: UTF-8 without a
    /// byte-order mark, so Python's configparser can read the same file.
    /// </summary>
    public static readonly Encoding DefaultFileEncoding = new UTF8Encoding(false);

    private readonly IniData _iniFile;
    private readonly FileIniDataParser _parser;

    // pyRevit configs are also written and hand-edited as Python configparser
    // files, which treat both '#' and ';' as comment markers.
    private static readonly Regex CommentPrefixRegex = new(@"^\s*[#;](.*)", RegexOptions.Compiled);

    /// <summary>
    /// Reads the file at <paramref name="configurationPath"/>, or starts empty
    /// when it does not exist.
    /// </summary>
    /// <param name="configurationPath">Path to the INI file.</param>
    /// <param name="readOnly">True to discard writes instead of persisting them.</param>
    private IniConfiguration(string configurationPath, bool readOnly)
        : base(configurationPath, readOnly)
    {
        _parser = new FileIniDataParser();
        ConfigureTolerantParsing(_parser);
        _iniFile = !File.Exists(configurationPath)
            ? new IniData()
            : _parser.ReadFile(_configurationPath, DefaultFileEncoding);
    }

    // A config file in the wild is user- and history-shaped: it may carry '#'
    // comments, a stray line, or a repeated key or section. Refusing to parse it
    // would take down every reader of the file (loader, CLI, script engines) at
    // construction, before the migrator ever gets a chance to repair it, so a
    // malformed entry is dropped and the last value of a repeated key wins.
    private static void ConfigureTolerantParsing(FileIniDataParser parser)
    {
        var configuration = parser.Parser.Configuration;
        configuration.CaseInsensitive = true;
        configuration.CommentRegex = CommentPrefixRegex;
        configuration.SkipInvalidLines = true;
        configuration.AllowDuplicateSections = true;
        configuration.AllowDuplicateKeys = true;
        configuration.OverrideDuplicateKeys = true;
    }

    /// <summary>
    /// Opens an INI-backed configuration, reading the file if it exists and
    /// starting empty if it does not — so a fresh install can save settings
    /// before any file is on disk.
    /// <para>
    /// Parsing never fails on a malformed file: unparseable lines are dropped
    /// and the last value of a repeated key wins. A config that refused to load
    /// would take down the loader, CLI, and script engines at once, and would
    /// never reach the migrator that repairs it.
    /// </para>
    /// </summary>
    /// <param name="configurationPath">Path to the INI file. It need not exist.</param>
    /// <param name="readOnly">True to discard writes instead of persisting them.</param>
    /// <returns>A configuration over that file.</returns>
    /// <exception cref="ArgumentNullException"><paramref name="configurationPath"/> is null.</exception>
    public static IConfiguration Create(string configurationPath, bool readOnly = default)
    {
        if (configurationPath is null)
            throw new ArgumentNullException(nameof(configurationPath));

        return new IniConfiguration(configurationPath, readOnly);
    }

    /// <inheritdoc />
    protected override void SaveConfigurationImpl()
    {
        SaveConfigurationImpl(_configurationPath);
    }

    /// <inheritdoc />
    protected override void SaveConfigurationImpl(string configurationPath)
    {
        string? directory = Path.GetDirectoryName(configurationPath);
        if (!string.IsNullOrEmpty(directory))
            Directory.CreateDirectory(directory);

        _parser.WriteFile(configurationPath, _iniFile, DefaultFileEncoding);
    }

    /// <inheritdoc />
    protected override bool HasSectionImpl(string sectionName)
    {
        return _iniFile.Sections.ContainsSection(sectionName);
    }

    /// <inheritdoc />
    protected override bool HasSectionKeyImpl(string sectionName, string keyName)
    {
        return HasSection(sectionName)
               && _iniFile.Sections[sectionName].ContainsKey(keyName);
    }

    /// <inheritdoc />
    protected override IEnumerable<string> GetSectionNamesImpl()
    {
        return _iniFile.Sections.Select(item => item.SectionName);
    }

    /// <inheritdoc />
    protected override IEnumerable<string> GetSectionOptionNamesImpl(string sectionName)
    {
        return _iniFile.Sections[sectionName].Select(item => item.KeyName);
    }

    /// <inheritdoc />
    protected override bool AddSectionImpl(string sectionName)
    {
        return _iniFile.Sections.AddSection(sectionName);
    }

    /// <inheritdoc />
    protected override bool RemoveSectionImpl(string sectionName)
    {
        return _iniFile.Sections.RemoveSection(sectionName);
    }

    /// <inheritdoc />
    protected override bool RemoveOptionImpl(string sectionName, string keyName)
    {
        return _iniFile[sectionName].RemoveKey(keyName);
    }

    /// <inheritdoc />
    protected override void SetValueImpl<T>(string sectionName, string keyName, T value)
    {
        if (!HasSection(sectionName))
        {
            _iniFile.Sections.AddSection(sectionName);
        }

        if (!HasSectionKey(sectionName, keyName))
        {
            _iniFile[sectionName].AddKey(keyName);
        }

        _iniFile[sectionName][keyName] = JsonConvert.SerializeObject(value);
    }

    private static readonly Regex HexIntegerRegex = new(@"^\s*0[xX][0-9a-fA-F]+\s*$", RegexOptions.Compiled);

    /// <inheritdoc />
    protected override object GetValueImpl(Type typeObject, string sectionName, string keyName)
    {
        string raw = _iniFile[sectionName][keyName];
        Type targetType = Nullable.GetUnderlyingType(typeObject) ?? typeObject;

        // Unwrap the JSON string quotes so the legacy-form checks below see the
        // bare value (e.g. "0x0" as 0x0).
        string valueToParse = raw;
        if (valueToParse.Length >= 2 && valueToParse.StartsWith("\"", StringComparison.Ordinal) && valueToParse.EndsWith("\"", StringComparison.Ordinal))
            valueToParse = valueToParse.Substring(1, valueToParse.Length - 2);

        // JSON does not allow hex literals (e.g. "0x0"); legacy INI may store ints as hex
        if ((targetType == typeof(int) || targetType == typeof(long)) && HexIntegerRegex.IsMatch(valueToParse))
        {
            long hexValue = Convert.ToInt64(valueToParse.Trim(), 16);
            if (typeObject == typeof(int))
                return checked((int)hexValue);
            if (typeObject == typeof(int?))
                return (int?)checked((int)hexValue);
            if (typeObject == typeof(long))
                return hexValue;
            if (typeObject == typeof(long?))
                return (long?)hexValue;
        }

        // JSON booleans are lowercase; legacy INI stored Python-style "True"/"False".
        if (targetType == typeof(bool) && bool.TryParse(valueToParse, out bool boolValue))
            return boolValue;

        // Tolerate legacy bare (unquoted) string values.
        if (targetType == typeof(string))
        {
            try
            {
                return JsonConvert.DeserializeObject(raw, typeObject) ?? raw;
            }
            catch (JsonException)
            {
                return raw;
            }
        }

        // List<string> spans several historical encodings (canonical JSON, JSON
        // whose legacy Windows paths carry unescaped backslashes, and the older
        // Python single-quoted literal); decode them uniformly so every reader
        // agrees on the parsed paths.
        if (targetType == typeof(List<string>))
            return DecodeStringList(raw, sectionName, keyName);

        try
        {
            return JsonConvert.DeserializeObject(raw, typeObject)
                   ?? throw new ConfigurationException("Cannot deserialize value using the specified key.");
        }
        catch (JsonException) when (IsContainerLiteral(valueToParse))
        {
            // Legacy configs stored lists and maps as Python literals, whose
            // Windows paths carry unescaped backslashes that JSON rejects as bad
            // escape sequences.
            return JsonConvert.DeserializeObject(EscapeBackslashes(raw), typeObject)
                   ?? throw new ConfigurationException("Cannot deserialize value using the specified key.");
        }
    }

    private static bool IsContainerLiteral(string value)
    {
        string trimmed = value.TrimStart();
        return trimmed.StartsWith("[", StringComparison.Ordinal)
               || trimmed.StartsWith("{", StringComparison.Ordinal);
    }

    // Reached only after a strict parse has already failed, so no well-formed
    // escape can be doubled here.
    private static string EscapeBackslashes(string value) => value.Replace("\\", "\\\\");

    // Decodes a stored List<string> across every list encoding pyRevit has
    // written. A bare (unbracketed) value is taken as a one-element list, which is
    // how userextensions and environment.sources spell a single path. A value
    // no encoding accounts for throws like any other undecodable value, so the
    // tolerant readers log it and fall back and the migrator can repair the key;
    // silently yielding an empty list would drop every configured extension.
    private static List<string> DecodeStringList(string raw, string sectionName, string keyName)
    {
        if (string.IsNullOrEmpty(raw))
            return new List<string>();

        string trimmed = raw.Trim();
        if (!trimmed.StartsWith("[", StringComparison.Ordinal))
            return new List<string> { trimmed };

        // An empty literal carries no quotes for either reader to key off, and both
        // encodings spell it the same way.
        if (IsEmptyListLiteral(trimmed))
            return new List<string>();

        if (TryJsonStringList(raw, out List<string>? jsonList))
            return jsonList!;

        if (LegacyListFormat.TryParseSingleQuoted(trimmed, out List<string>? legacyList))
        {
            // A read-only config never reaches the migrator's canonicalization, so
            // surface the legacy read to flag configs still carrying the old form.
            ConfigurationDiagnostics.ReportInfo(
                "Config value [" + sectionName + "] " + keyName + " was read using a legacy list format.");
            return legacyList!;
        }

        throw new ConfigurationException(
            "Config value [" + sectionName + "] " + keyName + " is not a readable list value.");
    }

    private static bool IsEmptyListLiteral(string trimmed) =>
        trimmed.Length >= 2
        && trimmed.EndsWith("]", StringComparison.Ordinal)
        && trimmed.Substring(1, trimmed.Length - 2).Trim().Length == 0;

    private static bool TryJsonStringList(string raw, out List<string>? list)
    {
        list = null;

        // A literal without double quotes is a Python single-quoted list, not JSON.
        if (raw.IndexOf('"') < 0)
            return false;

        try
        {
            list = JsonConvert.DeserializeObject<List<string>>(raw);
            return list != null;
        }
        catch (JsonException)
        {
        }

        try
        {
            // Legacy Windows paths store unescaped backslashes that JSON rejects.
            list = JsonConvert.DeserializeObject<List<string>>(EscapeBackslashes(raw));
            return list != null;
        }
        catch (JsonException)
        {
            return false;
        }
    }

    // The Python single-quoted list form is decoded by LegacyListFormat (shared
    // with the migrator) so both interpret it identically.

    /// <inheritdoc />
    protected override string GetRawValueImpl(string sectionName, string keyName)
    {
        return _iniFile[sectionName][keyName];
    }

    /// <inheritdoc />
    protected override void SetRawValueImpl(string sectionName, string keyName, string rawValue)
    {
        if (!HasSection(sectionName))
            _iniFile.Sections.AddSection(sectionName);

        if (!HasSectionKey(sectionName, keyName))
            _iniFile[sectionName].AddKey(keyName);

        _iniFile[sectionName][keyName] = rawValue;
    }
}
