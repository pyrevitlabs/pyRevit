using System;

using NUnit.Framework;
using Microsoft.Win32;

using pyRevitLabs.Common;

namespace pyRevitLabs.Common.Tests {
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
