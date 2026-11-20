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

        [Test]
        public void TokenizeDropsEmptyAndPaddedTokens() {
            var tokens = SystemPath.Tokenize(";C:\\a;;  C:\\b  ;;");
            Assert.That(tokens.Count, Is.EqualTo(2));
            Assert.That(tokens[0], Is.EqualTo("C:\\a"));
            Assert.That(tokens[1], Is.EqualTo("C:\\b"));
        }

        [Test]
        public void TokenizeHandlesNullAndEmpty() {
            Assert.That(SystemPath.Tokenize(null).Count, Is.EqualTo(0));
            Assert.That(SystemPath.Tokenize(string.Empty).Count, Is.EqualTo(0));
        }

        [Test]
        public void NormalizeTokenStripsTrailingSeparatorButKeepsDriveRoot() {
            Assert.That(SystemPath.NormalizeToken(@"C:\a\b\"), Is.EqualTo(@"C:\a\b"));
            Assert.That(SystemPath.NormalizeToken(@"  C:\a\b  "), Is.EqualTo(@"C:\a\b"));
            Assert.That(SystemPath.NormalizeToken(@"C:\"), Is.EqualTo(@"C:\"));
            Assert.That(SystemPath.NormalizeToken(null), Is.EqualTo(string.Empty));
        }

        [Test]
        public void HasEntryIgnoresCaseAndTrailingSeparator() {
            Assert.That(SystemPath.HasEntry(@"C:\a;" + TestDir, TestDir), Is.True);
            Assert.That(SystemPath.HasEntry(@"C:\a;" + TestDir + ";", TestDir), Is.True);
            Assert.That(SystemPath.HasEntry(@"C:\a;" + TestDir.ToUpperInvariant(), TestDir), Is.True);
            Assert.That(SystemPath.HasEntry(@"C:\a;" + TestDir + @"\", TestDir), Is.True);
        }

        [Test]
        public void HasEntryRejectsSubstringOfAnotherToken() {
            Assert.That(SystemPath.HasEntry(@"C:\a;" + TestDir + @"-old", TestDir), Is.False);
            Assert.That(SystemPath.HasEntry(TestDir.Substring(0, TestDir.Length - 4), TestDir), Is.False);
        }

        [Test]
        public void HasEntryIsFalseWhenAbsentAndForEmptyEntry() {
            Assert.That(SystemPath.HasEntry(@"C:\a;C:\b", TestDir), Is.False);
            Assert.That(SystemPath.HasEntry(null, TestDir), Is.False);
            Assert.That(SystemPath.HasEntry(TestDir, string.Empty), Is.False);
        }

        [Test]
        public void CountEntryReportsEveryOccurrence() {
            Assert.That(SystemPath.CountEntry(
                TestDir + ";C:\\a;" + TestDir.ToUpperInvariant() + ";" + TestDir, TestDir), Is.EqualTo(3));
            Assert.That(SystemPath.CountEntry(@"C:\a", TestDir), Is.EqualTo(0));
        }

        [Test]
        public void AddEntryAppendsWhenAbsentAndPreservesOrder() {
            var result = SystemPath.AddEntry(@"C:\a;C:\b", TestDir);
            Assert.That(result, Is.EqualTo(@"C:\a;C:\b;" + TestDir));
        }

        [Test]
        public void AddEntryIsIdempotent() {
            var current = @"C:\a;" + TestDir;
            Assert.That(SystemPath.AddEntry(current, TestDir), Is.EqualTo(current));
        }

        [Test]
        public void AddEntryDoesNotNormalizeExistingDuplicates() {
            var current = TestDir + ";" + TestDir;
            Assert.That(SystemPath.AddEntry(current, TestDir), Is.EqualTo(current));
        }

        [Test]
        public void AddEntryNeverProducesLeadingSeparator() {
            Assert.That(SystemPath.AddEntry(null, TestDir), Is.EqualTo(TestDir));
            Assert.That(SystemPath.AddEntry(string.Empty, TestDir), Is.EqualTo(TestDir));
            Assert.That(SystemPath.AddEntry(";", TestDir), Is.EqualTo(TestDir));
        }

        [Test]
        public void AddEntryPreservesExistingTextByteForByte() {
            var current = @"C:\a; C:\b ;%USERPROFILE%\c;";
            Assert.That(SystemPath.AddEntry(current, TestDir), Is.EqualTo(@"C:\a; C:\b ;%USERPROFILE%\c;" + TestDir));
        }

        [Test]
        public void AddEntryNeverIntroducesASeamOfSeparators() {
            foreach (var current in new[] { @"C:\a", @"C:\a;", @"C:\a; ", @"C:\a;;", @"C:\a; ;" })
                Assert.That(SystemPath.AddEntry(current, TestDir), Is.EqualTo(@"C:\a;" + TestDir), string.Format("unexpected result for input \"{0}\"", current));
        }

        [Test]
        public void PrependEntryPutsAbsentEntryInFrontOfUntouchedText() {
            var current = @"C:\a; C:\b ;%USERPROFILE%\c;";
            Assert.That(SystemPath.PrependEntry(current, TestDir), Is.EqualTo(TestDir + ";" + current));
        }

        [Test]
        public void PrependEntryMovesEntryAheadOfTheOneShadowingIt() {
            var olderInstall = @"C:\Users\me\AppData\Roaming\pyRevit-Master\bin";
            var current = @"C:\a;" + olderInstall + ";" + TestDir;
            Assert.That(SystemPath.PrependEntry(current, TestDir), Is.EqualTo(TestDir + @";C:\a;" + olderInstall));
        }

        [Test]
        public void PrependEntryCollapsesEveryCopyIntoTheFirstPosition() {
            var current = @"C:\a;" + TestDir + @"\;C:\b;" + TestDir.ToUpperInvariant();
            Assert.That(SystemPath.PrependEntry(current, TestDir), Is.EqualTo(TestDir + @";C:\a;C:\b"));
        }

        [Test]
        public void PrependEntryIsIdempotent() {
            foreach (var current in new[] { TestDir, TestDir + @"\;C:\a", " " + TestDir + @" ; C:\a ;" })
                Assert.That(SystemPath.PrependEntry(current, TestDir), Is.EqualTo(current), string.Format("unexpected result for input \"{0}\"", current));
            var once = SystemPath.PrependEntry(@"C:\a;C:\b", TestDir);
            Assert.That(SystemPath.PrependEntry(once, TestDir), Is.EqualTo(once));
        }

        [Test]
        public void PrependEntryNeverProducesStraySeparators() {
            foreach (var current in new[] { null, string.Empty, ";", " ; " })
                Assert.That(SystemPath.PrependEntry(current, TestDir), Is.EqualTo(TestDir), string.Format("unexpected result for input \"{0}\"", current));
            Assert.That(SystemPath.PrependEntry(@";;C:\a", TestDir), Is.EqualTo(TestDir + @";C:\a"));
        }

        [Test]
        public void PrependEntryIgnoresEmptyEntry() {
            Assert.That(SystemPath.PrependEntry(@"C:\a", string.Empty), Is.EqualTo(@"C:\a"));
        }

        [Test]
        public void FindFileInPathValuesKeepsResolutionOrderAcrossValues() {
            var machineInstall = @"C:\Program Files\pyRevit-Master\bin";
            var userInstall = @"C:\Users\me\AppData\Local\Programs\pyRevit CLI\bin";
            var pathValues = new[] { @"C:\Windows;" + machineInstall + @"\", userInstall };

            var found = SystemPath.FindFileInPathValues(pathValues, "pyrevit.exe",
                file => !file.StartsWith(@"C:\Windows", StringComparison.OrdinalIgnoreCase));

            Assert.That(found, Is.EqualTo(new[] { machineInstall + @"\pyrevit.exe", userInstall + @"\pyrevit.exe" }));
        }

        [Test]
        public void FindFileInPathValuesSkipsDirectoriesWithoutTheFile() {
            var found = SystemPath.FindFileInPathValues(
                new[] { @"C:\stale\bin;" + TestDir }, "pyrevit.exe",
                file => file.StartsWith(TestDir, StringComparison.OrdinalIgnoreCase));
            Assert.That(found.Count, Is.EqualTo(1));
            Assert.That(found[0], Is.EqualTo(TestDir + @"\pyrevit.exe"));
        }

        [Test]
        public void FindFileInPathValuesReportsRepeatedDirectoryOnce() {
            var found = SystemPath.FindFileInPathValues(
                new[] { TestDir + ";" + TestDir.ToUpperInvariant() + @"\;""" + TestDir + "\"" },
                "pyrevit.exe", file => true);
            Assert.That(found.Count, Is.EqualTo(1));
        }

        [Test]
        public void FindFileInPathValuesExpandsEnvironmentVariables() {
            var systemRoot = Environment.GetEnvironmentVariable("SystemRoot");
            var found = SystemPath.FindFileInPathValues(
                new[] { @"%SystemRoot%\System32" }, "cmd.exe", file => true);
            Assert.That(found[0], Is.EqualTo(systemRoot + @"\System32\cmd.exe"));
        }

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

        [Test]
        public void FindFileInPathValuesIgnoresUnusableEntries() {
            var found = SystemPath.FindFileInPathValues(
                new[] { null, string.Empty, ";;", "C:\\bad|dir", "\"\"" }, "pyrevit.exe",
                file => true);
            Assert.That(found.Count, Is.EqualTo(0));
        }

        [Test]
        public void RemoveEntryDropsEveryOccurrence() {
            var current = TestDir + ";C:\\a;" + TestDir.ToUpperInvariant() + ";" + TestDir;
            Assert.That(SystemPath.RemoveEntry(current, TestDir), Is.EqualTo("C:\\a"));
        }

        [Test]
        public void RemoveEntryKeepsOtherEntriesIntact() {
            var current = @"C:\a;C:\b";
            Assert.That(SystemPath.RemoveEntry(current, TestDir), Is.EqualTo(current));
        }

        [Test]
        public void GetDuplicateEntriesReportsEachDuplicateOnce() {
            var current = TestDir + ";C:\\a;" + TestDir + ";C:\\b;" + TestDir;
            var duplicates = SystemPath.GetDuplicateEntries(current);
            Assert.That(duplicates.Count, Is.EqualTo(1));
            Assert.That(duplicates[0], Is.EqualTo(TestDir));
        }

        [Test]
        public void GetDuplicateEntriesIsEmptyForCleanPath() {
            Assert.That(SystemPath.GetDuplicateEntries(@"C:\a;C:\b").Count, Is.EqualTo(0));
            Assert.That(SystemPath.GetDuplicateEntries(null).Count, Is.EqualTo(0));
        }

        [Test]
        public void TryParseScopeAcceptsUserAndMachine() {
            Assert.That(SystemPath.TryParseScope("user", out var userScope), Is.True);
            Assert.That(userScope, Is.EqualTo(EnvironmentVariableTarget.User));

            Assert.That(SystemPath.TryParseScope("MACHINE", out var machineScope), Is.True);
            Assert.That(machineScope, Is.EqualTo(EnvironmentVariableTarget.Machine));
        }

        [Test]
        public void TryParseScopeRejectsUnknownScope() {
            Assert.That(SystemPath.TryParseScope("session", out _), Is.False);
            Assert.That(SystemPath.TryParseScope(null, out _), Is.False);
        }

        [Test]
        public void ProcessScopeHasNoRegistryBacking() {
            Assert.Throws<ArgumentOutOfRangeException>(
                () => SystemPath.GetPathEntries(EnvironmentVariableTarget.Process));
        }

        [Test]
        public void DeniedKeyRaisesUnauthorizedAccessInsteadOfReturningEmpty() {
            var denied = Assert.Throws<UnauthorizedAccessException>(
                () => SystemPath.RequireEnvironmentKey(
                    null, EnvironmentVariableTarget.Machine, writable: true));
            Assert.That(denied.Message, Does.Contain("elevation may be required"));
        }

        [Test]
        public void DeniedReadKeyIsNamedWithoutTheElevationHint() {
            var denied = Assert.Throws<UnauthorizedAccessException>(
                () => SystemPath.RequireEnvironmentKey(
                    null, EnvironmentVariableTarget.User, writable: false));
            Assert.That(denied.Message, Does.Contain("User"));
            Assert.That(denied.Message.Contains("elevation"), Is.False);
        }

        [Test]
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

        [Test]
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

        [Test]
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

        [Test]
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
