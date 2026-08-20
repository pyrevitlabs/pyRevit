using System.Text;

namespace pyRevitLabs.Configurations;

/// <summary>
/// Decodes the legacy Python single-quoted list literal (e.g. <c>['C:\a','C:\b']</c>)
/// that older pyRevit configs stored for keys such as userextensions and
/// environment.sources. Kept as one shared definition so the read path (the INI
/// backend) and the migrator interpret it identically; delete when that format is
/// no longer read from any config in the wild.
/// </summary>
public static class LegacyListFormat
{
    /// <summary>
    /// Parses a Python single-quoted list literal without routing it through a JSON
    /// parser, so unescaped Windows-path backslashes survive; only the two escapes
    /// Python emits inside a single-quoted literal are decoded. Returns false when
    /// the value is not a single-quoted list, so the caller can fall through —
    /// including when the caller already tried JSON and failed (a double quote
    /// means the value was meant to be JSON), and when the value is <c>"[]"</c>,
    /// which is also the canonical encoding of an empty list and so must not be
    /// claimed as legacy, or the migrator would rewrite and back up an
    /// already-canonical config on every load.
    /// </summary>
    public static bool TryParseSingleQuoted(string value, out List<string>? items)
    {
        items = null;
        if (string.IsNullOrEmpty(value))
            return false;
        if (!value.StartsWith("[", StringComparison.Ordinal) || !value.EndsWith("]", StringComparison.Ordinal))
            return false;

        if (value.IndexOf('"') >= 0)
            return false;

        if (value.Equals("[]", StringComparison.Ordinal))
            return false;

        var result = new List<string>();
        var item = new StringBuilder();
        int end = value.Length - 1;
        bool inString = false;

        for (int i = 1; i < end; i++)
        {
            char c = value[i];

            if (!inString)
            {
                if (c == '\'')
                {
                    inString = true;
                    item.Length = 0;
                }
                else if (c != ',' && !char.IsWhiteSpace(c))
                {
                    return false;
                }

                continue;
            }

            if (c == '\\' && i + 1 < end && (value[i + 1] == '\\' || value[i + 1] == '\''))
            {
                item.Append(value[i + 1]);
                i++;
            }
            else if (c == '\'' && IsClosingDelimiter(value, i, end))
            {
                inString = false;
                result.Add(item.ToString());
            }
            else
            {
                item.Append(c);
            }
        }

        if (inString)
            return false;

        items = result;
        return true;
    }

    /// <summary>
    /// Whether the apostrophe at <paramref name="index"/> closes the current
    /// item. An apostrophe inside a value is a delimiter only when the next
    /// meaningful character ends the item.
    /// </summary>
    private static bool IsClosingDelimiter(string value, int index, int end)
    {
        for (int i = index + 1; i < end; i++)
        {
            if (char.IsWhiteSpace(value[i]))
                continue;

            return value[i] == ',';
        }

        return true;
    }
}
