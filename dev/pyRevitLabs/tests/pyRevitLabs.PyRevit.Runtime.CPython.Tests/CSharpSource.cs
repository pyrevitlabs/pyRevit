namespace PyRevitLabs.PyRevit.Runtime.CPython.Tests;

/// <summary>
/// Structural reads over a C# source file, for the few pyRevit-side invariants that cannot be
/// exercised without a live Revit session.
/// </summary>
internal static class CSharpSource {
    private static string? _cached;

    public static string CPythonEngine {
        get {
            if (_cached is null) {
                string path = Path.Combine(AppContext.BaseDirectory, "Sources", "CPythonEngine.cs");
                Assert.True(File.Exists(path), $"engine source fixture missing: {path}");
                _cached = File.ReadAllText(path);
            }

            return _cached;
        }
    }

    /// <summary>
    /// Returns the brace-matched body of the member declared by <paramref name="declaration"/>,
    /// with comments and literals blanked out so brace counting cannot be thrown off by them.
    /// </summary>
    public static string MemberBody(string source, string declaration) {
        string code = BlankNonCode(source);
        int declared = code.IndexOf(declaration, StringComparison.Ordinal);
        Assert.True(declared >= 0, $"member not found: {declaration}");

        int open = code.IndexOf('{', declared);
        Assert.True(open >= 0, $"member has no body: {declaration}");
        int close = MatchingBrace(code, open);
        return code.Substring(open, close - open + 1);
    }

    /// <summary>
    /// Whether <paramref name="statement"/> sits inside the block that
    /// <paramref name="blockHeader"/> opens, rather than after or outside it.
    /// </summary>
    public static bool IsInBlockOf(string memberBody, string blockHeader, string statement) {
        int header = memberBody.IndexOf(blockHeader, StringComparison.Ordinal);
        if (header < 0)
            return false;

        int open = memberBody.IndexOf('{', header);
        int close = MatchingBrace(memberBody, open);
        int target = memberBody.IndexOf(statement, StringComparison.Ordinal);
        return target > open && target < close;
    }

    private static int MatchingBrace(string code, int open) {
        int depth = 0;
        for (int i = open; i < code.Length; i++) {
            if (code[i] == '{')
                depth++;
            else if (code[i] == '}' && --depth == 0)
                return i;
        }

        throw new InvalidOperationException("unbalanced braces");
    }

    private static string BlankNonCode(string source) {
        var blanked = new System.Text.StringBuilder(source.Length);
        for (int i = 0; i < source.Length; i++) {
            char c = source[i];
            if (c == '/' && i + 1 < source.Length && source[i + 1] == '/') {
                while (i < source.Length && source[i] != '\n')
                    i++;
                blanked.Append('\n');
            }
            else if (c == '/' && i + 1 < source.Length && source[i + 1] == '*') {
                while (i + 1 < source.Length && !(source[i] == '*' && source[i + 1] == '/'))
                    i++;
                i++;
            }
            else if (c == '"' || c == '\'') {
                char quote = c;
                while (++i < source.Length && source[i] != quote) {
                    if (source[i] == '\\')
                        i++;
                }
                blanked.Append(' ');
            }
            else {
                blanked.Append(c);
            }
        }

        return blanked.ToString();
    }
}
