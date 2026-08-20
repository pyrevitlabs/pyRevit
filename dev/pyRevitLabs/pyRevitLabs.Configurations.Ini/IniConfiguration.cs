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

    /// <summary>
    /// Matches the comment prefix pyRevit configs use when hand-edited as Python
    /// configparser files, which treat both '#' and ';' as comment markers.
    /// </summary>
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
    /// <remarks>
    /// Unwraps JSON string quotes before matching the legacy-form checks below,
    /// so they see the bare value (e.g. <c>"0x0"</c> as <c>0x0</c>). A container
    /// value that fails strict JSON parsing falls back to a backslash-escaped
    /// re-parse, since a legacy Python literal's Windows paths carry unescaped
    /// backslashes that JSON treats as bad escape sequences.
    /// </remarks>
    protected override object GetValueImpl(Type typeObject, string sectionName, string keyName)
    {
        string raw = _iniFile[sectionName][keyName];
        Type targetType = Nullable.GetUnderlyingType(typeObject) ?? typeObject;

        string valueToParse = raw;
        if (valueToParse.Length >= 2 && valueToParse.StartsWith("\"", StringComparison.Ordinal) && valueToParse.EndsWith("\"", StringComparison.Ordinal))
            valueToParse = valueToParse.Substring(1, valueToParse.Length - 2);

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

        if (targetType == typeof(bool) && bool.TryParse(valueToParse, out bool boolValue))
            return boolValue;

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

        if (targetType == typeof(List<string>))
            return DecodeStringList(raw, sectionName, keyName);

        try
        {
            return JsonConvert.DeserializeObject(raw, typeObject)
                   ?? throw new ConfigurationException("Cannot deserialize value using the specified key.");
        }
        catch (JsonException) when (IsContainerLiteral(valueToParse))
        {
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

    private static readonly char[] SimpleJsonEscapeChars = { '"', '\\', '/', 'b', 'f', 'n', 'r', 't' };

    /// <summary>
    /// Doubles a backslash only when it is not already the start of a valid JSON
    /// escape sequence, so an already-correct escape elsewhere in the same value
    /// (e.g. one list entry among several) is left untouched. <c>\u</c> is only
    /// accepted when followed by 4 hex digits, so a legacy path like
    /// <c>"...\u\..."</c> (a literal "u" directory name, not a unicode escape)
    /// still gets doubled. Called only after a strict parse of the whole value
    /// has already failed.
    /// </summary>
    private static string EscapeBackslashes(string value)
    {
        var builder = new StringBuilder(value.Length);
        for (int i = 0; i < value.Length; i++)
        {
            char c = value[i];
            if (c != '\\')
            {
                builder.Append(c);
                continue;
            }

            if (i + 1 < value.Length && Array.IndexOf(SimpleJsonEscapeChars, value[i + 1]) >= 0)
            {
                builder.Append(c).Append(value[i + 1]);
                i++;
                continue;
            }

            if (i + 5 < value.Length && value[i + 1] == 'u' && IsHexDigit(value[i + 2])
                && IsHexDigit(value[i + 3]) && IsHexDigit(value[i + 4]) && IsHexDigit(value[i + 5]))
            {
                builder.Append(value, i, 6);
                i += 5;
                continue;
            }

            builder.Append("\\\\");
        }

        return builder.ToString();
    }

    private static bool IsHexDigit(char c) =>
        (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F');

    /// <summary>
    /// Decodes a stored <c>List&lt;string&gt;</c> across every list encoding
    /// pyRevit has written: canonical JSON, JSON with unescaped legacy
    /// Windows-path backslashes, the older Python single-quoted literal (whose
    /// use is reported through <see cref="ConfigurationDiagnostics"/>, since a
    /// read-only config never reaches the migrator that would otherwise
    /// canonicalize it), and a bare unbracketed value taken as a one-element
    /// list — how userextensions and environment.sources spell a single path.
    /// An empty bracket literal is decoded directly, since neither encoding
    /// carries a quote to distinguish it. A value no encoding accounts for
    /// throws like any other undecodable value, so the tolerant readers log it
    /// and fall back and the migrator can repair the key; silently yielding an
    /// empty list would drop every configured extension.
    /// </summary>
    private static List<string> DecodeStringList(string raw, string sectionName, string keyName)
    {
        if (string.IsNullOrEmpty(raw))
            return new List<string>();

        string trimmed = raw.Trim();
        if (!trimmed.StartsWith("[", StringComparison.Ordinal))
            return new List<string> { trimmed };

        if (IsEmptyListLiteral(trimmed))
            return new List<string>();

        if (TryJsonStringList(raw, out List<string>? jsonList))
            return jsonList!;

        if (LegacyListFormat.TryParseSingleQuoted(trimmed, out List<string>? legacyList))
        {
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

    /// <summary>
    /// Parses a JSON list literal, retrying with backslash-escaping when the
    /// first attempt fails, since a legacy Windows path stored unescaped carries
    /// backslashes JSON treats as bad escapes. Returns false for a value with no
    /// double quote at all, since that is the Python single-quoted form rather
    /// than JSON.
    /// </summary>
    private static bool TryJsonStringList(string raw, out List<string>? list)
    {
        list = null;

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
            list = JsonConvert.DeserializeObject<List<string>>(EscapeBackslashes(raw));
            return list != null;
        }
        catch (JsonException)
        {
            return false;
        }
    }

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
