namespace pyRevitLabs.Configurations.Abstractions;

/// <summary>
/// A single configuration file: sections of key/value pairs, with values stored
/// as canonical JSON text and materialized to a requested CLR type on read.
/// Edits are held in memory until <see cref="SaveConfiguration()"/> writes them.
/// </summary>
public interface IConfiguration
{
    /// <summary>
    /// Full path to the backing file. The file need not exist yet; it is created
    /// on the first successful save.
    /// </summary>
    string ConfigurationPath { get; }

    /// <summary>
    /// True when the backing file is not writable, so <see cref="SaveConfiguration()"/>
    /// discards any pending change instead of persisting it.
    /// </summary>
    bool ReadOnly { get; }

    /// <summary>
    /// Advances on every mutation, so a holder of derived state can tell whether
    /// the store changed under it without comparing values.
    /// </summary>
    long Revision { get; }

    /// <summary>Whether a section with this name is present.</summary>
    /// <exception cref="ArgumentException"><paramref name="sectionName"/> is null or whitespace.</exception>
    bool HasSection(string sectionName);

    /// <summary>Whether the named key is present in the named section.</summary>
    /// <exception cref="ArgumentException"><paramref name="keyName"/> is null or whitespace.</exception>
    bool HasSectionKey(string sectionName, string keyName);

    /// <summary>Names of every section in the file, in file order.</summary>
    IEnumerable<string> GetSectionNames();

    /// <summary>
    /// Key names in the named section, or an empty sequence when the section is
    /// absent.
    /// </summary>
    IEnumerable<string> GetSectionOptionNames(string sectionName);

    /// <summary>
    /// Reads a value and converts it to <typeparamref name="T"/>. Use
    /// <see cref="GetValueOrDefault{T}"/> to tolerate absent or unreadable values.
    /// </summary>
    /// <exception cref="Exceptions.ConfigurationSectionNotFoundException">The section is absent.</exception>
    /// <exception cref="Exceptions.ConfigurationSectionKeyNotFoundException">The key is absent.</exception>
    /// <exception cref="Exceptions.ConfigurationException">The stored value cannot be decoded as <typeparamref name="T"/>.</exception>
    T GetValue<T>(string sectionName, string keyName);

    /// <summary>
    /// Reads a value, returning <paramref name="defaultValue"/> when the section
    /// or key is absent, or when the stored value cannot be decoded. A failed
    /// decode is reported through <see cref="ConfigurationDiagnostics"/> rather
    /// than thrown, so one malformed value does not fail a whole section load.
    /// </summary>
    T? GetValueOrDefault<T>(string sectionName, string keyName, T? defaultValue = default);

    /// <summary>
    /// Reflection-friendly overload of <see cref="GetValue{T}"/> for a type known
    /// only at runtime.
    /// </summary>
    /// <exception cref="Exceptions.ConfigurationSectionNotFoundException">The section is absent.</exception>
    /// <exception cref="Exceptions.ConfigurationSectionKeyNotFoundException">The key is absent.</exception>
    object GetValue(Type typeObject, string sectionName, string keyName);

    /// <summary>
    /// Reflection-friendly overload of <see cref="GetValueOrDefault{T}"/> for a
    /// type known only at runtime.
    /// </summary>
    object? GetValueOrDefault(Type typeObject, string sectionName, string keyName, object? defaultValue = default);

    /// <summary>
    /// Reads the stored value text (canonical JSON) without decoding it, or
    /// <paramref name="defaultValue"/> when the section or key is absent. Lets a
    /// caller that does its own (de)serialization round-trip a value with a
    /// single encode.
    /// </summary>
    string? GetRawValueOrDefault(string sectionName, string keyName, string? defaultValue = null);

    /// <summary>
    /// Stores value text verbatim, without encoding it. The caller owns the
    /// encoding, and a value written here is read back unchanged by
    /// <see cref="GetRawValueOrDefault"/>. Creates the section and key if absent.
    /// </summary>
    /// <exception cref="ArgumentNullException"><paramref name="rawValue"/> is null.</exception>
    void SetRawValue(string sectionName, string keyName, string rawValue);

    /// <summary>Adds an empty section. Returns false when it already exists.</summary>
    bool AddSection(string sectionName);

    /// <summary>Removes a section and its keys. Returns false when it is absent.</summary>
    bool RemoveSection(string sectionName);

    /// <summary>Removes a single key. Returns false when the section or key is absent.</summary>
    bool RemoveOption(string sectionName, string keyName);

    /// <summary>
    /// Encodes and stores a value, creating the section and key if absent. Pass a
    /// non-null value; use <see cref="RemoveOption"/> to clear a key.
    /// </summary>
    /// <exception cref="ArgumentNullException"><paramref name="value"/> is null.</exception>
    void SetValue<T>(string sectionName, string keyName, T? value);

    /// <summary>
    /// Writes pending changes to <see cref="ConfigurationPath"/>, creating the
    /// directory if needed. Does nothing when <see cref="ReadOnly"/> is true.
    /// </summary>
    void SaveConfiguration();

    /// <summary>
    /// Writes the current state to a different path, leaving
    /// <see cref="ConfigurationPath"/> untouched. Unlike
    /// <see cref="SaveConfiguration()"/> this writes even when
    /// <see cref="ReadOnly"/> is true, since the destination is not the
    /// protected file.
    /// </summary>
    /// <exception cref="ArgumentNullException"><paramref name="configurationPath"/> is null.</exception>
    void SaveConfiguration(string configurationPath);
}
