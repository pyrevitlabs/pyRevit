using System;
using System.Collections.Generic;
using System.IO;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Exceptions;

namespace pyRevitLabs.Configurations.Ini.Tests;

/// <summary>
/// Covers the list encodings that reach userextensions and environment.sources:
/// canonical JSON, JSON whose legacy Windows paths carry unescaped backslashes,
/// and the legacy Python single-quoted literal.
/// </summary>
public class ListDecodingTests
{
    /// <summary>
    /// Injects the stored text directly, so the decode is exercised without the
    /// INI file writer/parser round-trip in between.
    /// </summary>
    private static List<string> Decode(string stored) =>
        Store(stored).GetValue<List<string>>("core", "userextensions");

    private static IConfiguration Store(string stored)
    {
        IConfiguration config = IniConfiguration.Create(
            Path.Combine(Path.GetTempPath(), $"list_{Guid.NewGuid():N}.ini"));
        config.SetRawValue("core", "userextensions", stored);
        return config;
    }

    [Fact]
    public void EscapedJsonList_Parses() =>
        Assert.Equal(new List<string> { @"C:\Users\ext", @"D:\ext2" },
            Decode(@"[""C:\\Users\\ext"",""D:\\ext2""]"));

    /// <summary>
    /// JSON form a legacy config left with unescaped Windows-path backslashes.
    /// </summary>
    [Fact]
    public void UnescapedJsonList_LegacyWindowsPaths_Parses() =>
        Assert.Equal(new List<string> { @"C:\Users\ext", @"D:\ext2" },
            Decode(@"[""C:\Users\ext"",""D:\ext2""]"));

    [Fact]
    public void SingleQuotedList_UnescapedPaths_Parses() =>
        Assert.Equal(new List<string> { @"C:\Users\ext", @"D:\Program Files\x" },
            Decode(@"['C:\Users\ext','D:\Program Files\x']"));

    /// <summary>
    /// \t must stay two characters, not become a tab.
    /// </summary>
    [Fact]
    public void SingleQuotedList_PathStartingWithEscapeLikeChar_IsNotInterpreted() =>
        Assert.Equal(new List<string> { @"C:\temp\new\ext" },
            Decode(@"['C:\temp\new\ext']"));

    /// <summary>
    /// Output of Python str() on a list of paths.
    /// </summary>
    [Fact]
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

    /// <summary>
    /// An undecodable value must not pass for "no extensions configured".
    /// </summary>
    [Fact]
    public void UndecodableList_Throws() =>
        Assert.Throws<ConfigurationException>(() => Decode(@"['C:\Users\ext"));

    [Fact]
    public void UndecodableList_TolerantRead_FallsBackToDefault() =>
        Assert.Empty(Store(@"['C:\Users\ext")
            .GetValueOrDefault("core", "userextensions", new List<string>())!);

    /// <summary>
    /// The migrator finds it through the same failure, and can then repair it.
    /// </summary>
    [Fact]
    public void UndecodableList_IsReportedAsUnreadable()
    {
        var warnings = new List<string>();
        Action<string>? previous = ConfigurationDiagnostics.Warn;
        ConfigurationDiagnostics.Warn = warnings.Add;
        try
        {
            Store(@"['C:\Users\ext").GetValueOrDefault<List<string>>("core", "userextensions");
        }
        finally
        {
            ConfigurationDiagnostics.Warn = previous;
        }

        Assert.Contains(warnings, message => message.Contains("userextensions"));
    }
}
