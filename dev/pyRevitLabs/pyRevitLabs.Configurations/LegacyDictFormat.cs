using System.Text;

namespace pyRevitLabs.Configurations;

/// <summary>
/// Decodes the legacy Python single-quoted dict literal (e.g.
/// <c>{'dev': 'C:\a', 'main': 'C:\b'}</c>) that older pyRevit configs stored for
/// the environment.clones registry. The counterpart to
/// <see cref="LegacyListFormat"/>; delete when that format is no longer read
/// from any config in the wild.
/// </summary>
public static class LegacyDictFormat
{
    /// <summary>
    /// Parses a Python single-quoted dict literal without routing it through a
    /// JSON parser, so unescaped Windows-path backslashes survive; only the two
    /// escapes Python emits inside a single-quoted literal are decoded. Returns
    /// false when the value is not a single-quoted dict, so the caller can fall
    /// through — including when the caller already tried JSON and failed (a
    /// double quote means the value was meant to be JSON), and when the value is
    /// <c>"{}"</c>, which is also the canonical encoding of an empty dict and so
    /// must not be claimed as legacy, or the migrator would rewrite and back up
    /// an already-canonical config on every load — and when parsing yields no
    /// entries, since a literal that parses to nothing is malformed rather than
    /// empty (the empty case is <c>"{}"</c>, already declined above). Later
    /// duplicate keys win, matching how a dict literal evaluates.
    /// </summary>
    public static bool TryParseSingleQuoted(string value, out Dictionary<string, string>? items)
    {
        items = null;
        if (string.IsNullOrEmpty(value))
            return false;
        if (!value.StartsWith("{", StringComparison.Ordinal) || !value.EndsWith("}", StringComparison.Ordinal))
            return false;

        if (value.IndexOf('"') >= 0)
            return false;

        if (value.Equals("{}", StringComparison.Ordinal))
            return false;

        var result = new Dictionary<string, string>();
        int index = 1;
        int end = value.Length - 1;

        while (true)
        {
            SkipWhitespace(value, ref index, end);
            if (index >= end)
                break;

            if (value[index] != '\'')
                return false;
            if (!TryReadString(value, ref index, end, ':', false, out string? key))
                return false;

            SkipWhitespace(value, ref index, end);
            if (index >= end || value[index] != ':')
                return false;
            index++;

            SkipWhitespace(value, ref index, end);
            if (index >= end || value[index] != '\'')
                return false;
            if (!TryReadString(value, ref index, end, ',', true, out string? entry))
                return false;

            result[key!] = entry!;

            SkipWhitespace(value, ref index, end);
            if (index >= end)
                break;

            if (value[index] != ',')
                return false;
            index++;
        }

        if (result.Count == 0)
            return false;

        items = result;
        return true;
    }

    private static void SkipWhitespace(string value, ref int index, int end)
    {
        while (index < end && char.IsWhiteSpace(value[index]))
            index++;
    }

    private static bool TryReadString(
        string value, ref int index, int end, char terminator, bool endTerminates, out string? result)
    {
        result = null;
        var content = new StringBuilder();

        index++;
        while (index < end)
        {
            char current = value[index];

            if (current == '\\' && index + 1 < end && (value[index + 1] == '\\' || value[index + 1] == '\''))
            {
                content.Append(value[index + 1]);
                index += 2;
                continue;
            }

            if (current == '\'' && IsClosingDelimiter(value, index, end, terminator, endTerminates))
            {
                index++;
                result = content.ToString();
                return true;
            }

            content.Append(current);
            index++;
        }

        return false;
    }

    /// <summary>
    /// Whether the apostrophe at <paramref name="index"/> closes the current
    /// string. An apostrophe inside a value is a delimiter only when the next
    /// meaningful character is the one that ends this position in the literal.
    /// </summary>
    private static bool IsClosingDelimiter(
        string value, int index, int end, char terminator, bool endTerminates)
    {
        for (int i = index + 1; i < end; i++)
        {
            if (char.IsWhiteSpace(value[i]))
                continue;

            return value[i] == terminator;
        }

        return endTerminates;
    }
}
