using Microsoft.VisualStudio.TestTools.UnitTesting;

using pyRevitLabs.Common.Extensions;

namespace pyRevitLabs.UnitTests {
    /// <summary>
    /// A clone source such as <c>https://user:pw@host/x.git</c> must not reach a log file with its password.
    /// </summary>
    [TestClass]
    [TestCategory("HostFree")]
    [TestCategory("Unit")]
    public class UrlCredentialRedactionTests {
        [DataTestMethod]
        [DataRow("https://user:pw@github.com/org/repo.git", "https://***@github.com/org/repo.git")]
        [DataRow("https://token@github.com/org/repo.git", "https://***@github.com/org/repo.git")]
        [DataRow("https://user:top secret@github.com/org/repo.git", "https://***@github.com/org/repo.git")]
        [DataRow("https://user:p@ss@github.com/org/repo.git", "https://***@github.com/org/repo.git")]
        [DataRow("https://user:ab/cd@github.com/org/repo.git", "https://***@github.com/org/repo.git")]
        [DataRow("https://github.com/org/repo.git", "https://github.com/org/repo.git")]
        [DataRow(@"C:\repos\pyrevit", @"C:\repos\pyrevit")]
        [DataRow("https://github.com/org/repo.git/@mention", "https://github.com/org/repo.git/@mention")]
        public void RedactUrlCredentials_HidesTheUserInfoOnly(string source, string expected) {
            Assert.AreEqual(expected, source.RedactUrlCredentials());
        }

        [TestMethod]
        public void RedactUrlCredentials_KeepsNullAndEmpty() {
            string nothing = null;
            Assert.IsNull(nothing.RedactUrlCredentials());
            Assert.AreEqual(string.Empty, string.Empty.RedactUrlCredentials());
        }
    }
}
