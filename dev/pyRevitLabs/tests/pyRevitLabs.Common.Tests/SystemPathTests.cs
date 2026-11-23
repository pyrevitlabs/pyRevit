using System;

using NUnit.Framework;
using Microsoft.Win32;

using pyRevitLabs.Common;

namespace pyRevitLabs.Common.Tests {
    /// <summary>Covers PATH editing: entries are matched case- and separator-insensitively, edits preserve existing text and order, and denied registry access raises instead of reading as empty.</summary>
    [TestFixture]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [NonParallelizable]
    [Category("HostFree")]
    [Category("Unit")]
    public class SystemPathTests {
        private const string TestDir = @"C:\Program Files\pyRevit-Master\bin";

        /// <summary>Splitting a PATH string drops empty tokens and trims whitespace around the rest.</summary>
        [Test]
        public void TokenizeDropsEmptyAndPaddedTokens() {
            var tokens = SystemPath.Tokenize(";C:\\a;;  C:\\b  ;;");
            Assert.That(tokens.Count, Is.EqualTo(2));
            Assert.That(tokens[0], Is.EqualTo("C:\\a"));
            Assert.That(tokens[1], Is.EqualTo("C:\\b"));
        }

        /// <summary>Splitting a null or empty PATH string yields no tokens.</summary>
        [Test]
        public void TokenizeHandlesNullAndEmpty() {
            Assert.That(SystemPath.Tokenize(null).Count, Is.EqualTo(0));
            Assert.That(SystemPath.Tokenize(string.Empty).Count, Is.EqualTo(0));
        }

        /// <summary>Normalizing trims whitespace and a trailing separator, keeps a drive root intact and maps null to an empty string.</summary>
        [Test]
        public void NormalizeTokenStripsTrailingSeparatorButKeepsDriveRoot() {
            Assert.That(SystemPath.NormalizeToken(@"C:\a\b\"), Is.EqualTo(@"C:\a\b"));
            Assert.That(SystemPath.NormalizeToken(@"  C:\a\b  "), Is.EqualTo(@"C:\a\b"));
            Assert.That(SystemPath.NormalizeToken(@"C:\"), Is.EqualTo(@"C:\"));
            Assert.That(SystemPath.NormalizeToken(null), Is.EqualTo(string.Empty));
        }

        /// <summary>An entry is found regardless of case, a trailing separator or a trailing semicolon.</summary>
        [Test]
        public void HasEntryIgnoresCaseAndTrailingSeparator() {
            Assert.That(SystemPath.HasEntry(@"C:\a;" + TestDir, TestDir), Is.True);
            Assert.That(SystemPath.HasEntry(@"C:\a;" + TestDir + ";", TestDir), Is.True);
            Assert.That(SystemPath.HasEntry(@"C:\a;" + TestDir.ToUpperInvariant(), TestDir), Is.True);
            Assert.That(SystemPath.HasEntry(@"C:\a;" + TestDir + @"\", TestDir), Is.True);
        }

        /// <summary>An entry is not found when it only matches part of another token.</summary>
        [Test]
        public void HasEntryRejectsSubstringOfAnotherToken() {
            Assert.That(SystemPath.HasEntry(@"C:\a;" + TestDir + @"-old", TestDir), Is.False);
            Assert.That(SystemPath.HasEntry(TestDir.Substring(0, TestDir.Length - 4), TestDir), Is.False);
        }

        /// <summary>An absent entry, a null PATH and an empty entry all report not found.</summary>
        [Test]
        public void HasEntryIsFalseWhenAbsentAndForEmptyEntry() {
            Assert.That(SystemPath.HasEntry(@"C:\a;C:\b", TestDir), Is.False);
            Assert.That(SystemPath.HasEntry(null, TestDir), Is.False);
            Assert.That(SystemPath.HasEntry(TestDir, string.Empty), Is.False);
        }

        /// <summary>Counting matches every case-insensitive occurrence and returns zero when the entry is absent.</summary>
        [Test]
        public void CountEntryReportsEveryOccurrence() {
            Assert.That(SystemPath.CountEntry(
                TestDir + ";C:\\a;" + TestDir.ToUpperInvariant() + ";" + TestDir, TestDir), Is.EqualTo(3));
            Assert.That(SystemPath.CountEntry(@"C:\a", TestDir), Is.EqualTo(0));
        }

        /// <summary>Adding an absent entry appends it after the existing entries in their original order.</summary>
        [Test]
        public void AddEntryAppendsWhenAbsentAndPreservesOrder() {
            var result = SystemPath.AddEntry(@"C:\a;C:\b", TestDir);
            Assert.That(result, Is.EqualTo(@"C:\a;C:\b;" + TestDir));
        }

        /// <summary>Adding an entry that is already present leaves the PATH unchanged.</summary>
        [Test]
        public void AddEntryIsIdempotent() {
            var current = @"C:\a;" + TestDir;
            Assert.That(SystemPath.AddEntry(current, TestDir), Is.EqualTo(current));
        }

        /// <summary>Adding an entry that already appears twice leaves both copies in place.</summary>
        [Test]
        public void AddEntryDoesNotNormalizeExistingDuplicates() {
            var current = TestDir + ";" + TestDir;
            Assert.That(SystemPath.AddEntry(current, TestDir), Is.EqualTo(current));
        }

        /// <summary>Adding to a null, empty or separator-only PATH yields just the entry.</summary>
        [Test]
        public void AddEntryNeverProducesLeadingSeparator() {
            Assert.That(SystemPath.AddEntry(null, TestDir), Is.EqualTo(TestDir));
            Assert.That(SystemPath.AddEntry(string.Empty, TestDir), Is.EqualTo(TestDir));
            Assert.That(SystemPath.AddEntry(";", TestDir), Is.EqualTo(TestDir));
        }

        /// <summary>Adding an entry keeps the existing text, including spaces and unexpanded variables, exactly as it was.</summary>
        [Test]
        public void AddEntryPreservesExistingTextByteForByte() {
            var current = @"C:\a; C:\b ;%USERPROFILE%\c;";
            Assert.That(SystemPath.AddEntry(current, TestDir), Is.EqualTo(@"C:\a; C:\b ;%USERPROFILE%\c;" + TestDir));
        }

        /// <summary>Adding after trailing semicolons or blank tokens joins the entry with a single separator.</summary>
        [Test]
        public void AddEntryNeverIntroducesASeamOfSeparators() {
            foreach (var current in new[] { @"C:\a", @"C:\a;", @"C:\a; ", @"C:\a;;", @"C:\a; ;" })
                Assert.That(SystemPath.AddEntry(current, TestDir), Is.EqualTo(@"C:\a;" + TestDir), string.Format("unexpected result for input \"{0}\"", current));
        }

        /// <summary>Prepending an absent entry puts it in front of the existing text, which is kept exactly as it was.</summary>
        [Test]
        public void PrependEntryPutsAbsentEntryInFrontOfUntouchedText() {
            var current = @"C:\a; C:\b ;%USERPROFILE%\c;";
            Assert.That(SystemPath.PrependEntry(current, TestDir), Is.EqualTo(TestDir + ";" + current));
        }

        /// <summary>Prepending an entry that is already present moves it to the front, ahead of an older install that shadowed it.</summary>
        [Test]
        public void PrependEntryMovesEntryAheadOfTheOneShadowingIt() {
            var olderInstall = @"C:\Users\me\AppData\Roaming\pyRevit-Master\bin";
            var current = @"C:\a;" + olderInstall + ";" + TestDir;
            Assert.That(SystemPath.PrependEntry(current, TestDir), Is.EqualTo(TestDir + @";C:\a;" + olderInstall));
        }

        /// <summary>Prepending removes every case- or separator-variant copy of the entry and keeps one at the front.</summary>
        [Test]
        public void PrependEntryCollapsesEveryCopyIntoTheFirstPosition() {
            var current = @"C:\a;" + TestDir + @"\;C:\b;" + TestDir.ToUpperInvariant();
            Assert.That(SystemPath.PrependEntry(current, TestDir), Is.EqualTo(TestDir + @";C:\a;C:\b"));
        }

        /// <summary>Prepending an entry that is already first leaves the PATH unchanged, and prepending twice equals prepending once.</summary>
        [Test]
        public void PrependEntryIsIdempotent() {
            foreach (var current in new[] { TestDir, TestDir + @"\;C:\a", " " + TestDir + @" ; C:\a ;" })
                Assert.That(SystemPath.PrependEntry(current, TestDir), Is.EqualTo(current), string.Format("unexpected result for input \"{0}\"", current));
            var once = SystemPath.PrependEntry(@"C:\a;C:\b", TestDir);
            Assert.That(SystemPath.PrependEntry(once, TestDir), Is.EqualTo(once));
        }

        /// <summary>Prepending to an empty or separator-only PATH yields just the entry, and leading empty tokens are dropped.</summary>
        [Test]
        public void PrependEntryNeverProducesStraySeparators() {
            foreach (var current in new[] { null, string.Empty, ";", " ; " })
                Assert.That(SystemPath.PrependEntry(current, TestDir), Is.EqualTo(TestDir), string.Format("unexpected result for input \"{0}\"", current));
            Assert.That(SystemPath.PrependEntry(@";;C:\a", TestDir), Is.EqualTo(TestDir + @";C:\a"));
        }

        /// <summary>Prepending an empty entry leaves the PATH unchanged.</summary>
        [Test]
        public void PrependEntryIgnoresEmptyEntry() {
            Assert.That(SystemPath.PrependEntry(@"C:\a", string.Empty), Is.EqualTo(@"C:\a"));
        }

        /// <summary>Matching files are returned in PATH resolution order across all the given PATH values.</summary>
        [Test]
        public void FindFileInPathValuesKeepsResolutionOrderAcrossValues() {
            var machineInstall = @"C:\Program Files\pyRevit-Master\bin";
            var userInstall = @"C:\Users\me\AppData\Local\Programs\pyRevit CLI\bin";
            var pathValues = new[] { @"C:\Windows;" + machineInstall + @"\", userInstall };

            var found = SystemPath.FindFileInPathValues(pathValues, "pyrevit.exe",
                file => !file.StartsWith(@"C:\Windows", StringComparison.OrdinalIgnoreCase));

            Assert.That(found, Is.EqualTo(new[] { machineInstall + @"\pyrevit.exe", userInstall + @"\pyrevit.exe" }));
        }

        /// <summary>Directories that do not contain the file are skipped.</summary>
        [Test]
        public void FindFileInPathValuesSkipsDirectoriesWithoutTheFile() {
            var found = SystemPath.FindFileInPathValues(
                new[] { @"C:\stale\bin;" + TestDir }, "pyrevit.exe",
                file => file.StartsWith(TestDir, StringComparison.OrdinalIgnoreCase));
            Assert.That(found.Count, Is.EqualTo(1));
            Assert.That(found[0], Is.EqualTo(TestDir + @"\pyrevit.exe"));
        }

        /// <summary>A directory listed several times, in different case, with a trailing separator or quoted, is reported once.</summary>
        [Test]
        public void FindFileInPathValuesReportsRepeatedDirectoryOnce() {
            var found = SystemPath.FindFileInPathValues(
                new[] { TestDir + ";" + TestDir.ToUpperInvariant() + @"\;""" + TestDir + "\"" },
                "pyrevit.exe", file => true);
            Assert.That(found.Count, Is.EqualTo(1));
        }

        /// <summary>Environment variables in PATH entries are expanded before looking for the file.</summary>
        [Test]
        public void FindFileInPathValuesExpandsEnvironmentVariables() {
            var systemRoot = Environment.GetEnvironmentVariable("SystemRoot");
            var found = SystemPath.FindFileInPathValues(
                new[] { @"%SystemRoot%\System32" }, "cmd.exe", file => true);
            Assert.That(found[0], Is.EqualTo(systemRoot + @"\System32\cmd.exe"));
        }

        /// <summary>An entry whose variable expands to several directories is split and searched in order.</summary>
        [Test]
        public void FindFileInPathValuesSplitsEntriesThatExpandToSeveralDirectories() {
            const string variable = "PYREVIT_UNITTEST_CLI_PATHS";
            var previousValue = Environment.GetEnvironmentVariable(variable);
            Environment.SetEnvironmentVariable(variable, @"C:\old-cli;C:\tools");
            try {
                var found = SystemPath.FindFileInPathValues(
                    new[] { "%" + variable + "%;" + TestDir }, "pyrevit.exe", file => true);

                Assert.That(found, Is.EqualTo(new[] {
                    @"C:\old-cli\pyrevit.exe",
                    @"C:\tools\pyrevit.exe",
                    TestDir + @"\pyrevit.exe",
                }));
            }
            finally {
                Environment.SetEnvironmentVariable(variable, previousValue);
            }
        }

        /// <summary>Null, empty, separator-only, invalid and empty quoted entries are ignored without error.</summary>
        [Test]
        public void FindFileInPathValuesIgnoresUnusableEntries() {
            var found = SystemPath.FindFileInPathValues(
                new[] { null, string.Empty, ";;", "C:\\bad|dir", "\"\"" }, "pyrevit.exe",
                file => true);
            Assert.That(found.Count, Is.EqualTo(0));
        }

        /// <summary>Removing an entry drops every occurrence of it, in any case.</summary>
        [Test]
        public void RemoveEntryDropsEveryOccurrence() {
            var current = TestDir + ";C:\\a;" + TestDir.ToUpperInvariant() + ";" + TestDir;
            Assert.That(SystemPath.RemoveEntry(current, TestDir), Is.EqualTo("C:\\a"));
        }

        /// <summary>Removing an absent entry leaves the PATH unchanged.</summary>
        [Test]
        public void RemoveEntryKeepsOtherEntriesIntact() {
            var current = @"C:\a;C:\b";
            Assert.That(SystemPath.RemoveEntry(current, TestDir), Is.EqualTo(current));
        }

        /// <summary>An entry repeated several times is reported as a duplicate exactly once.</summary>
        [Test]
        public void GetDuplicateEntriesReportsEachDuplicateOnce() {
            var current = TestDir + ";C:\\a;" + TestDir + ";C:\\b;" + TestDir;
            var duplicates = SystemPath.GetDuplicateEntries(current);
            Assert.That(duplicates.Count, Is.EqualTo(1));
            Assert.That(duplicates[0], Is.EqualTo(TestDir));
        }

        /// <summary>A PATH without repeats, or a null PATH, has no duplicates.</summary>
        [Test]
        public void GetDuplicateEntriesIsEmptyForCleanPath() {
            Assert.That(SystemPath.GetDuplicateEntries(@"C:\a;C:\b").Count, Is.EqualTo(0));
            Assert.That(SystemPath.GetDuplicateEntries(null).Count, Is.EqualTo(0));
        }

        /// <summary>The user and machine scope names parse case-insensitively to their environment targets.</summary>
        [Test]
        public void TryParseScopeAcceptsUserAndMachine() {
            Assert.That(SystemPath.TryParseScope("user", out var userScope), Is.True);
            Assert.That(userScope, Is.EqualTo(EnvironmentVariableTarget.User));

            Assert.That(SystemPath.TryParseScope("MACHINE", out var machineScope), Is.True);
            Assert.That(machineScope, Is.EqualTo(EnvironmentVariableTarget.Machine));
        }

        /// <summary>Unknown and null scope names fail to parse.</summary>
        [Test]
        public void TryParseScopeRejectsUnknownScope() {
            Assert.That(SystemPath.TryParseScope("session", out _), Is.False);
            Assert.That(SystemPath.TryParseScope(null, out _), Is.False);
        }

        /// <summary>Reading PATH entries for the process scope throws <c>ArgumentOutOfRangeException</c> because it has no registry key.</summary>
        [Test]
        public void ProcessScopeHasNoRegistryBacking() {
            Assert.Throws<ArgumentOutOfRangeException>(
                () => SystemPath.GetPathEntries(EnvironmentVariableTarget.Process));
        }

        /// <summary>A writable machine key that cannot be opened throws <c>UnauthorizedAccessException</c> mentioning that elevation may be required.</summary>
        [Test]
        public void DeniedKeyRaisesUnauthorizedAccessInsteadOfReturningEmpty() {
            var denied = Assert.Throws<UnauthorizedAccessException>(
                () => SystemPath.RequireEnvironmentKey(
                    null, EnvironmentVariableTarget.Machine, writable: true));
            Assert.That(denied.Message, Does.Contain("elevation may be required"));
        }

        /// <summary>A user key that cannot be opened for reading throws <c>UnauthorizedAccessException</c> naming the scope without an elevation hint.</summary>
        [Test]
        public void DeniedReadKeyIsNamedWithoutTheElevationHint() {
            var denied = Assert.Throws<UnauthorizedAccessException>(
                () => SystemPath.RequireEnvironmentKey(
                    null, EnvironmentVariableTarget.User, writable: false));
            Assert.That(denied.Message, Does.Contain("User"));
            Assert.That(denied.Message.Contains("elevation"), Is.False);
        }

        /// <summary>A key that was opened is returned as the same instance.</summary>
        [Test]
        [Category("Integration")]
        public void OpenKeyIsReturnedWhenItExists() {
            var subKey = @"Software\pyRevitLabs\Tests\SystemPathGuard\" + Guid.NewGuid().ToString("N");
            try {
                using (var key = Registry.CurrentUser.CreateSubKey(subKey)) {
                    Assert.That(SystemPath.RequireEnvironmentKey(key, EnvironmentVariableTarget.User, true), Is.SameAs(key));
                }
            }
            finally {
                Registry.CurrentUser.DeleteSubKeyTree(subKey, throwOnMissingSubKey: false);
            }
        }

        /// <summary>Writing a new raw PATH value stores it as <c>ExpandString</c> and reads back the unexpanded text.</summary>
        [Test]
        [Category("Integration")]
        public void RawValueWriteKeepsExpandStringKindAndUnexpandedText() {
            var subKey = @"Software\pyRevitLabs\Tests\SystemPath\" + Guid.NewGuid().ToString("N");
            try {
                using (var key = Registry.CurrentUser.CreateSubKey(subKey)) {
                    SystemPath.WriteRawPathValue(key, @"%USERPROFILE%\bin;" + TestDir);

                    Assert.That(key.GetValueKind("Path"), Is.EqualTo(RegistryValueKind.ExpandString));
                    Assert.That(SystemPath.ReadRawPathValue(key), Is.EqualTo(@"%USERPROFILE%\bin;" + TestDir));
                }
            }
            finally {
                Registry.CurrentUser.DeleteSubKeyTree(subKey, throwOnMissingSubKey: false);
            }
        }

        /// <summary>Writing a raw PATH value keeps an existing <c>String</c> value kind.</summary>
        [Test]
        [Category("Integration")]
        public void RawValueWriteDoesNotDowngradeExistingStringKind() {
            var subKey = @"Software\pyRevitLabs\Tests\SystemPath\" + Guid.NewGuid().ToString("N");
            try {
                using (var key = Registry.CurrentUser.CreateSubKey(subKey)) {
                    key.SetValue("Path", @"C:\a", RegistryValueKind.String);
                    SystemPath.WriteRawPathValue(key, @"C:\a;" + TestDir);

                    Assert.That(key.GetValueKind("Path"), Is.EqualTo(RegistryValueKind.String));
                }
            }
            finally {
                Registry.CurrentUser.DeleteSubKeyTree(subKey, throwOnMissingSubKey: false);
            }
        }

        /// <summary>Reading a raw PATH value that does not exist returns null.</summary>
        [Test]
        [Category("Integration")]
        public void RawValueReadOfMissingValueIsNull() {
            var subKey = @"Software\pyRevitLabs\Tests\SystemPath\" + Guid.NewGuid().ToString("N");
            try {
                using (var key = Registry.CurrentUser.CreateSubKey(subKey))
                    Assert.That(SystemPath.ReadRawPathValue(key), Is.Null);
            }
            finally {
                Registry.CurrentUser.DeleteSubKeyTree(subKey, throwOnMissingSubKey: false);
            }
        }
    }
}
