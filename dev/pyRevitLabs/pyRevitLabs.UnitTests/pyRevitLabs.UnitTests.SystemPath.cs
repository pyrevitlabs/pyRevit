using System;

using Microsoft.VisualStudio.TestTools.UnitTesting;
using Microsoft.Win32;

using pyRevitLabs.Common;

namespace pyRevitLabs.UnitTests {
    [TestClass]
    public class SystemPathTests {
        private const string TestDir = @"C:\Program Files\pyRevit-Master\bin";

        [TestMethod]
        public void TokenizeDropsEmptyAndPaddedTokens() {
            var tokens = SystemPath.Tokenize(";C:\\a;;  C:\\b  ;;");
            Assert.AreEqual(2, tokens.Count);
            Assert.AreEqual("C:\\a", tokens[0]);
            Assert.AreEqual("C:\\b", tokens[1]);
        }

        [TestMethod]
        public void TokenizeHandlesNullAndEmpty() {
            Assert.AreEqual(0, SystemPath.Tokenize(null).Count);
            Assert.AreEqual(0, SystemPath.Tokenize(string.Empty).Count);
        }

        [TestMethod]
        public void NormalizeTokenStripsTrailingSeparatorButKeepsDriveRoot() {
            Assert.AreEqual(@"C:\a\b", SystemPath.NormalizeToken(@"C:\a\b\"));
            Assert.AreEqual(@"C:\a\b", SystemPath.NormalizeToken(@"  C:\a\b  "));
            Assert.AreEqual(@"C:\", SystemPath.NormalizeToken(@"C:\"));
            Assert.AreEqual(string.Empty, SystemPath.NormalizeToken(null));
        }

        [TestMethod]
        public void HasEntryIgnoresCaseAndTrailingSeparator() {
            Assert.IsTrue(SystemPath.HasEntry(@"C:\a;" + TestDir, TestDir));
            Assert.IsTrue(SystemPath.HasEntry(@"C:\a;" + TestDir + ";", TestDir));
            Assert.IsTrue(SystemPath.HasEntry(@"C:\a;" + TestDir.ToUpperInvariant(), TestDir));
            Assert.IsTrue(SystemPath.HasEntry(@"C:\a;" + TestDir + @"\", TestDir));
        }

        [TestMethod]
        public void HasEntryRejectsSubstringOfAnotherToken() {
            Assert.IsFalse(SystemPath.HasEntry(@"C:\a;" + TestDir + @"-old", TestDir));
            Assert.IsFalse(SystemPath.HasEntry(TestDir.Substring(0, TestDir.Length - 4), TestDir));
        }

        [TestMethod]
        public void HasEntryIsFalseWhenAbsentAndForEmptyEntry() {
            Assert.IsFalse(SystemPath.HasEntry(@"C:\a;C:\b", TestDir));
            Assert.IsFalse(SystemPath.HasEntry(null, TestDir));
            Assert.IsFalse(SystemPath.HasEntry(TestDir, string.Empty));
        }

        [TestMethod]
        public void CountEntryReportsEveryOccurrence() {
            Assert.AreEqual(3, SystemPath.CountEntry(
                TestDir + ";C:\\a;" + TestDir.ToUpperInvariant() + ";" + TestDir, TestDir));
            Assert.AreEqual(0, SystemPath.CountEntry(@"C:\a", TestDir));
        }

        [TestMethod]
        public void AddEntryAppendsWhenAbsentAndPreservesOrder() {
            var result = SystemPath.AddEntry(@"C:\a;C:\b", TestDir);
            Assert.AreEqual(@"C:\a;C:\b;" + TestDir, result);
        }

        [TestMethod]
        public void AddEntryIsIdempotent() {
            var current = @"C:\a;" + TestDir;
            Assert.AreEqual(current, SystemPath.AddEntry(current, TestDir));
        }

        [TestMethod]
        public void AddEntryDoesNotNormalizeExistingDuplicates() {
            var current = TestDir + ";" + TestDir;
            Assert.AreEqual(current, SystemPath.AddEntry(current, TestDir));
        }

        [TestMethod]
        public void AddEntryNeverProducesLeadingSeparator() {
            Assert.AreEqual(TestDir, SystemPath.AddEntry(null, TestDir));
            Assert.AreEqual(TestDir, SystemPath.AddEntry(string.Empty, TestDir));
            Assert.AreEqual(TestDir, SystemPath.AddEntry(";", TestDir));
        }

        [TestMethod]
        public void AddEntryPreservesExistingTextByteForByte() {
            var current = @"C:\a; C:\b ;%USERPROFILE%\c;";
            Assert.AreEqual(@"C:\a; C:\b ;%USERPROFILE%\c;" + TestDir,
                SystemPath.AddEntry(current, TestDir));
        }

        [TestMethod]
        public void AddEntryNeverIntroducesASeamOfSeparators() {
            foreach (var current in new[] { @"C:\a", @"C:\a;", @"C:\a; ", @"C:\a;;", @"C:\a; ;" })
                Assert.AreEqual(@"C:\a;" + TestDir, SystemPath.AddEntry(current, TestDir),
                    "unexpected result for input \"{0}\"", current);
        }

        [TestMethod]
        public void RemoveEntryDropsEveryOccurrence() {
            var current = TestDir + ";C:\\a;" + TestDir.ToUpperInvariant() + ";" + TestDir;
            Assert.AreEqual("C:\\a", SystemPath.RemoveEntry(current, TestDir));
        }

        [TestMethod]
        public void RemoveEntryKeepsOtherEntriesIntact() {
            var current = @"C:\a;C:\b";
            Assert.AreEqual(current, SystemPath.RemoveEntry(current, TestDir));
        }

        [TestMethod]
        public void GetDuplicateEntriesReportsEachDuplicateOnce() {
            var current = TestDir + ";C:\\a;" + TestDir + ";C:\\b;" + TestDir;
            var duplicates = SystemPath.GetDuplicateEntries(current);
            Assert.AreEqual(1, duplicates.Count);
            Assert.AreEqual(TestDir, duplicates[0]);
        }

        [TestMethod]
        public void GetDuplicateEntriesIsEmptyForCleanPath() {
            Assert.AreEqual(0, SystemPath.GetDuplicateEntries(@"C:\a;C:\b").Count);
            Assert.AreEqual(0, SystemPath.GetDuplicateEntries(null).Count);
        }

        [TestMethod]
        public void TryParseScopeAcceptsUserAndMachine() {
            Assert.IsTrue(SystemPath.TryParseScope("user", out var userScope));
            Assert.AreEqual(EnvironmentVariableTarget.User, userScope);

            Assert.IsTrue(SystemPath.TryParseScope("MACHINE", out var machineScope));
            Assert.AreEqual(EnvironmentVariableTarget.Machine, machineScope);
        }

        [TestMethod]
        public void TryParseScopeRejectsUnknownScope() {
            Assert.IsFalse(SystemPath.TryParseScope("session", out _));
            Assert.IsFalse(SystemPath.TryParseScope(null, out _));
        }

        [TestMethod]
        public void ProcessScopeHasNoRegistryBacking() {
            Assert.ThrowsException<ArgumentOutOfRangeException>(
                () => SystemPath.GetPathEntries(EnvironmentVariableTarget.Process));
        }

        [TestMethod]
        public void RawValueWriteKeepsExpandStringKindAndUnexpandedText() {
            var subKey = @"Software\pyRevitLabs\UnitTests\SystemPath";
            try {
                using (var key = Registry.CurrentUser.CreateSubKey(subKey)) {
                    SystemPath.WriteRawPathValue(key, @"%USERPROFILE%\bin;" + TestDir);

                    Assert.AreEqual(RegistryValueKind.ExpandString, key.GetValueKind("Path"));
                    Assert.AreEqual(@"%USERPROFILE%\bin;" + TestDir,
                        SystemPath.ReadRawPathValue(key));
                }
            }
            finally {
                Registry.CurrentUser.DeleteSubKeyTree(subKey, throwOnMissingSubKey: false);
            }
        }

        [TestMethod]
        public void RawValueWriteDoesNotDowngradeExistingStringKind() {
            var subKey = @"Software\pyRevitLabs\UnitTests\SystemPath";
            try {
                using (var key = Registry.CurrentUser.CreateSubKey(subKey)) {
                    key.SetValue("Path", @"C:\a", RegistryValueKind.String);
                    SystemPath.WriteRawPathValue(key, @"C:\a;" + TestDir);

                    Assert.AreEqual(RegistryValueKind.String, key.GetValueKind("Path"));
                }
            }
            finally {
                Registry.CurrentUser.DeleteSubKeyTree(subKey, throwOnMissingSubKey: false);
            }
        }

        [TestMethod]
        public void RawValueReadOfMissingValueIsNull() {
            var subKey = @"Software\pyRevitLabs\UnitTests\SystemPath";
            try {
                using (var key = Registry.CurrentUser.CreateSubKey(subKey))
                    Assert.IsNull(SystemPath.ReadRawPathValue(key));
            }
            finally {
                Registry.CurrentUser.DeleteSubKeyTree(subKey, throwOnMissingSubKey: false);
            }
        }
    }
}
