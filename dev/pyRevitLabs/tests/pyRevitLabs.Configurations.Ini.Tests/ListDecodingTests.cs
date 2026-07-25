using System;
using System.Collections.Generic;
using System.IO;
using pyRevitLabs.Configurations.Abstractions;

namespace pyRevitLabs.Configurations.Ini.Tests;

/// <summary>
/// Covers the list encodings that reach userextensions and environment.sources:
/// canonical JSON, JSON whose legacy Windows paths carry unescaped backslashes,
/// and the legacy Python single-quoted literal. Ported from the loader's
/// PythonListParser tests when that decode path moved into the Ini backend.
/// </summary>
public class ListDecodingTests
{
    // Injects the stored text directly, so the decode is exercised without the
    // INI file writer/parser round-trip in between.
    private static List<string> Decode(string stored)
    {
        IConfiguration config = IniConfiguration.Create(
            Path.Combine(Path.GetTempPath(), $"list_{Guid.NewGuid():N}.ini"));
        config.SetRawValue("core", "userextensions", stored);
        return config.GetValue<List<string>>("core", "userextensions");
    }

    [Fact]
    public void EscapedJsonList_Parses() =>
        Assert.Equal(new List<string> { @"C:\Users\ext", @"D:\ext2" },
            Decode(@"[""C:\\Users\\ext"",""D:\\ext2""]"));

    [Fact] // JSON form a legacy config left with unescaped Windows-path backslashes.
    public void UnescapedJsonList_LegacyWindowsPaths_Parses() =>
        Assert.Equal(new List<string> { @"C:\Users\ext", @"D:\ext2" },
            Decode(@"[""C:\Users\ext"",""D:\ext2""]"));

    [Fact]
    public void SingleQuotedList_UnescapedPaths_Parses() =>
        Assert.Equal(new List<string> { @"C:\Users\ext", @"D:\Program Files\x" },
            Decode(@"['C:\Users\ext','D:\Program Files\x']"));

    [Fact] // \t must stay two characters, not become a tab.
    public void SingleQuotedList_PathStartingWithEscapeLikeChar_IsNotInterpreted() =>
        Assert.Equal(new List<string> { @"C:\temp\new\ext" },
            Decode(@"['C:\temp\new\ext']"));

    [Fact] // Output of Python str() on a list of paths.
    public void SingleQuotedList_DoubledBackslashes_Parses() =>
        Assert.Equal(new List<string> { @"C:\Users\ext" },
            Decode(@"['C:\\Users\\ext']"));

    [Fact]
    public void SingleQuotedList_WithSpacesAfterCommas_Parses() =>
        Assert.Equal(new List<string> { @"C:\a", @"C:\b" },
            Decode(@"['C:\a', 'C:\b']"));

    [Fact]
    public void SingleQuotedList_EmbeddedApostrophe_IsKept() =>
        Assert.Equal(new List<string> { @"C:\Bob's Files\ext" },
            Decode(@"['C:\Bob's Files\ext']"));

    [Fact]
    public void SingleQuotedList_EscapedApostrophe_IsDecoded() =>
        Assert.Equal(new List<string> { @"C:\Bob's Files" },
            Decode(@"['C:\Bob\'s Files']"));

    [Fact]
    public void EmptyList_ParsesToEmpty() =>
        Assert.Empty(Decode("[]"));

    [Fact]
    public void NonListValue_ParsesToSingleItem() =>
        Assert.Equal(new List<string> { @"C:\Tools\ext" }, Decode(@"C:\Tools\ext"));

    [Fact]
    public void UnterminatedList_ParsesToEmpty() =>
        Assert.Empty(Decode(@"['C:\Users\ext"));
}
