using System;
using System.Collections.Generic;
using System.IO;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Ini.Extensions;
using pyRevitLabs.Configurations.Sections;

namespace pyRevitLabs.Configurations.Ini.Tests;

/// <summary>
/// Golden-file fidelity corpus: loads real-world config shapes from Fixtures/
/// and asserts read and round-trip behavior. The Acceptance_* tests pin the
/// intended string-encoding contract: string values round-trip decoded, not
/// JSON-quoted.
/// </summary>
public class GoldenFileFidelityTests
{
    private static string FixtureDir => Path.Combine(AppContext.BaseDirectory, "Fixtures");

    private static IConfiguration Load(string name) =>
        IniConfiguration.Create(Path.Combine(FixtureDir, name));

    private static string TempCopy(string name)
    {
        var dst = Path.Combine(Path.GetTempPath(), $"fidelity_{Guid.NewGuid():N}.ini");
        File.Copy(Path.Combine(FixtureDir, name), dst, true);
        return dst;
    }

    // ---- read fidelity, tolerance, and defaults ----

    [Fact]
    public void Bool_ReadsCorrectly()
    {
        var cfg = Load("populated.ini");
        Assert.True(cfg.GetValue<bool>("core", "rocketmode"));
        Assert.False(cfg.GetValue<bool>("core", "checkupdates"));
    }

    [Fact]
    public void Int_ReadsCorrectly()
    {
        var cfg = Load("populated.ini");
        Assert.Equal(10, cfg.GetValue<int>("core", "startuplogtimeout"));
    }

    [Fact]
    public void StringList_ReadsCorrectly()
    {
        var cfg = Load("populated.ini");
        var exts = cfg.GetValue<List<string>>("core", "userextensions");
        Assert.Equal(2, exts.Count);
        Assert.Equal(@"C:\Tools\ext1", exts[0]);
        Assert.Equal(@"D:\ext2", exts[1]);
    }

    [Fact]
    public void CorruptValue_DoesNotThrow_FallsBackToDefault()
    {
        var cfg = Load("corrupted_clones.ini");
        var clones = cfg.GetValueOrDefault(
            "environment", "clones", new Dictionary<string, string>());
        Assert.Empty((Dictionary<string, string>)clones!);
    }

    [Fact]
    public void CorruptFixture_OtherKeysStillReadable()
    {
        var cfg = Load("corrupted_clones.ini");
        Assert.True(cfg.GetValue<bool>("core", "rocketmode"));
    }

    [Fact]
    public void LegacyValues_DoNotThrowOnLoadOrDefaultRead()
    {
        var cfg = Load("legacy_values.ini");
        // bare/non-JSON string read back as raw (tolerated, not crashing)
        Assert.NotNull(cfg.GetValueOrDefault<string>("core", "outputstylesheet", ""));
    }

    [Fact] // Python-style "True"/"False" predate the JSON encoding and must still read.
    public void LegacyCapitalizedBool_ReadsCorrectly()
    {
        var cfg = Load("legacy_values.ini");
        Assert.True(cfg.GetValue<bool>("core", "rocketmode"));
        Assert.False(cfg.GetValue<bool>("core", "checkupdates"));
    }

    [Fact] // Windows paths in a legacy list carry backslashes that are not JSON escapes.
    public void LegacyUnescapedPathList_ReadsCorrectly()
    {
        var cfg = Load("legacy_values.ini");
        var exts = cfg.GetValue<List<string>>("core", "userextensions");

        Assert.Equal(
            new List<string> { @"C:\Tools\ext1", @"D:\Program Files\ext2", @"C:\temp\new" },
            exts);
    }

    [Fact] // \t and \n are valid JSON escapes; in a path they must stay literal.
    public void LegacyUnescapedPathList_DoesNotInterpretEscapeSequences()
    {
        var cfg = Load("legacy_values.ini");
        var exts = cfg.GetValue<List<string>>("core", "userextensions");

        Assert.DoesNotContain(exts, item => item.Contains('\t') || item.Contains('\n'));
    }

    [Fact] // The clone registry is a map with the same unescaped-path problem.
    public void LegacyUnescapedPathMap_ReadsCorrectly()
    {
        var cfg = Load("legacy_values.ini");
        var clones = cfg.GetValue<Dictionary<string, string>>("environment", "clones");

        Assert.Equal(@"C:\Users\u\pyRevit-Master", clones["master"]);
    }

    [Fact] // Readable legacy containers must survive migration, not be reset.
    public void Migration_KeepsLegacyUnescapedPathList()
    {
        var path = TempCopy("legacy_values.ini");
        try
        {
            var service = new ConfigurationBuilder(false)
                .AddIniConfiguration(path)
                .Build();

            var result = ConfigurationMigrator.Migrate(service);
            Assert.DoesNotContain("core.userextensions", result.ResetKeys);
            Assert.DoesNotContain("environment.clones", result.ResetKeys);

            var reread = IniConfiguration.Create(path);
            Assert.True(reread.HasSectionKey("core", "userextensions"));
            Assert.Equal(
                new List<string> { @"C:\Tools\ext1", @"D:\Program Files\ext2", @"C:\temp\new" },
                reread.GetValue<List<string>>("core", "userextensions"));
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact] // A capitalized bool is a readable value, so migration must not drop it.
    public void Migration_KeepsLegacyCapitalizedBool()
    {
        var path = TempCopy("legacy_values.ini");
        try
        {
            var service = new ConfigurationBuilder(false)
                .AddIniConfiguration(path)
                .Build();

            var result = ConfigurationMigrator.Migrate(service);
            Assert.DoesNotContain("core.rocketmode", result.ResetKeys);
            Assert.DoesNotContain("core.checkupdates", result.ResetKeys);

            var reread = IniConfiguration.Create(path);
            Assert.True(reread.HasSectionKey("core", "rocketmode"));
            Assert.True(reread.GetValue<bool>("core", "rocketmode"));
            Assert.False(reread.GetValue<bool>("core", "checkupdates"));
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact]
    public void MissingKey_OrDefault_ReturnsDefault()
    {
        var cfg = Load("empty.ini");
        Assert.Equal("fallback", cfg.GetValueOrDefault<string>("core", "user_locale", "fallback"));
    }

    [Fact] // Large hex telemetry flags round-trip as a string (no 32-bit overflow).
    public void TelemetryEventFlags_LargeHex_ReadsAsString()
    {
        var cfg = Load("populated.ini");
        Assert.Equal("0x4000400004003", cfg.GetValue<string>("telemetry", "apptelemetry_event_flags"));
    }

    // ---- string-encoding contract ----

    [Fact] // GetValue<string> returns the decoded value, not the JSON-quoted raw string.
    public void Acceptance_GetString_ReturnsDecoded()
    {
        var cfg = Load("populated.ini");
        Assert.Equal("en_us", cfg.GetValue<string>("core", "user_locale"));
    }

    [Fact] // Writing then re-reading a string yields the same value, with no quote/escape accumulation.
    public void Acceptance_StringRoundTrip_IsIdempotent()
    {
        var path = TempCopy("populated.ini");
        try
        {
            var cfg = IniConfiguration.Create(path);
            cfg.SetValue("core", "user_locale", "fr_fr");
            cfg.SaveConfiguration();

            var reread = IniConfiguration.Create(path);
            Assert.Equal("fr_fr", reread.GetValue<string>("core", "user_locale"));
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact] // After SaveSection, the same service instance's typed snapshot reflects the write (shared-cache freshness).
    public void SaveSection_RefreshesTypedSnapshot_OnSameInstance()
    {
        var path = TempCopy("populated.ini");
        try
        {
            var service = new ConfigurationBuilder(false)
                .AddIniConfiguration(path).Build();

            Assert.NotEqual(99, service.Core.StartupLogTimeout);
            service.SaveSection(
                new CoreSection { StartupLogTimeout = 99 });

            // Without rebuilding the service, the snapshot must show the saved value.
            Assert.Equal(99, service.Core.StartupLogTimeout);
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact] // Saving one property via a sparse section POCO must not clobber sibling keys.
    public void SaveSection_SingleProperty_DoesNotClobberSiblings()
    {
        var path = TempCopy("populated.ini");
        try
        {
            var service = new ConfigurationBuilder(false)
                .AddIniConfiguration(path).Build();

            service.SaveSection(
                new CoreSection { StartupLogTimeout = 99 });

            var reread = IniConfiguration.Create(path);
            var exts = reread.GetValue<List<string>>("core", "userextensions");
            Assert.Equal(2, exts.Count);                          // sibling list preserved
            Assert.Equal(99, reread.GetValue<int>("core", "startuplogtimeout")); // intended write applied
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact] // Explicitly setting a property to its own default value still persists (not skipped as "unset").
    public void SaveSection_SetToDefaultValue_StillWrites()
    {
        // rocketmode default is true; start from a file that has it false.
        var path = Path.Combine(Path.GetTempPath(), $"settodefault_{Guid.NewGuid():N}.ini");
        File.WriteAllText(path, "[core]\nrocketmode = false\n");
        try
        {
            var service = new ConfigurationBuilder(false)
                .AddIniConfiguration(path).Build();

            service.SaveSection(
                new CoreSection { RocketMode = true });

            var reread = IniConfiguration.Create(path);
            Assert.True(reread.GetValue<bool>("core", "rocketmode"));
        }
        finally
        {
            File.Delete(path);
        }
    }

    /// <summary>
    /// Section defaults still apply on read for keys absent from the file. One
    /// case per CLR type the materializer handles, plus one per section
    /// </summary>
    [Fact]
    public void Defaults_MaterializePerTypeAndSection_WhenKeyAbsent()
    {
        var service = new ConfigurationBuilder(false)
            .AddIniConfiguration(Path.Combine(FixtureDir, "empty.ini")).Build();

        // one per type path
        Assert.True(service.Core.RocketMode);                       // bool, default true
        Assert.False(service.Core.CheckUpdates);                    // bool, default false
        Assert.Equal(10, service.Core.StartupLogTimeout);           // int
        Assert.Equal(0L, service.Core.MinHostDriveFreeSpace);       // long
        Assert.Equal(string.Empty, service.Core.RequiredHostBuild); // string

        // no declared default: unset means auto-detect from the Revit UI language,
        // so this must stay null rather than collapse to string.Empty
        Assert.Null(service.Core.UserLocale);

        // one per section, so materialization is not proven on CoreSection alone
        Assert.Equal(48884, service.Routes.Port);
        Assert.Equal(string.Empty, service.Telemetry.TelemetryFileDir);
        Assert.NotNull(service.Environment.Clones);                 // empty-collection default
        Assert.Empty(service.Environment.Clones!);
    }

    // ---- migration ----

    [Fact] // A value that no longer parses to its declared type is dropped, and the schema version is stamped.
    public void Migration_RepairsCorruptValue_AndStampsVersion()
    {
        var path = TempCopy("corrupted_clones.ini");
        try
        {
            var service = new ConfigurationBuilder(false)
                .AddIniConfiguration(path)
                .Build();

            var result = ConfigurationMigrator.Migrate(service);
            Assert.True(result.Migrated);
            Assert.Contains("environment.clones", result.ResetKeys);

            var reread = IniConfiguration.Create(path);
            Assert.False(reread.HasSectionKey("environment", "clones"));
            Assert.Equal(ConfigurationMigrator.CurrentVersion, reread.GetValue<int>("core", "config_version"));
            Assert.True(reread.GetValue<bool>("core", "rocketmode"));
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact] // Re-running migration on an already-stamped config does nothing.
    public void Migration_IsIdempotent()
    {
        var path = TempCopy("populated.ini");
        try
        {
            var first = new ConfigurationBuilder(false)
                .AddIniConfiguration(path).Build();
            Assert.True(ConfigurationMigrator.Migrate(first).Migrated);

            var second = new ConfigurationBuilder(false)
                .AddIniConfiguration(path).Build();
            Assert.False(ConfigurationMigrator.Migrate(second).Migrated);
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact] // A corrupt value is repaired even when the config is already at the current version.
    public void Migration_SelfHeals_WhenAlreadyStamped()
    {
        var path = Path.Combine(Path.GetTempPath(), $"selfheal_{Guid.NewGuid():N}.ini");
        File.WriteAllText(path,
            "[core]\nconfig_version = 1\nrocketmode = true\n\n[environment]\nclones = \"oops\"\n");
        try
        {
            var service = new ConfigurationBuilder(false)
                .AddIniConfiguration(path).Build();

            var result = ConfigurationMigrator.Migrate(service);
            Assert.True(result.Migrated);
            Assert.Contains("environment.clones", result.ResetKeys);

            var reread = IniConfiguration.Create(path);
            Assert.False(reread.HasSectionKey("environment", "clones"));
        }
        finally
        {
            File.Delete(path);
        }
    }
}
