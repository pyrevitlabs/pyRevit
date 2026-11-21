using NUnit.Framework;

using pyRevitLabs.Common.Extensions;

namespace pyRevitLabs.Common.Tests {
    /// <summary>
    /// A clone source such as <c>https://user:pw@host/x.git</c> must not reach a log file with its password.
    /// </summary>
    [TestFixture]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [Category("HostFree")]
    [Category("Unit")]
    [Category("Regression")]
    public class UrlCredentialRedactionTests {
        /// <summary>Redaction replaces the whole user info of a URL with <c>***</c> and leaves URLs without credentials and local paths unchanged.</summary>
        [TestCase("https://user:pw@github.com/org/repo.git", "https://***@github.com/org/repo.git")]
        [TestCase("https://token@github.com/org/repo.git", "https://***@github.com/org/repo.git")]
        [TestCase("https://user:top secret@github.com/org/repo.git", "https://***@github.com/org/repo.git")]
        [TestCase("https://user:p@ss@github.com/org/repo.git", "https://***@github.com/org/repo.git")]
        [TestCase("https://user:ab/cd@github.com/org/repo.git", "https://***@github.com/org/repo.git")]
        [TestCase("https://github.com/org/repo.git", "https://github.com/org/repo.git")]
        [TestCase(@"C:\repos\pyrevit", @"C:\repos\pyrevit")]
        [TestCase("https://github.com/org/repo.git/@mention", "https://github.com/org/repo.git/@mention")]
        public void RedactUrlCredentials_HidesTheUserInfoOnly(string source, string expected) {
            Assert.That(source.RedactUrlCredentials(), Is.EqualTo(expected));
        }

        /// <summary>Redacting a null or empty string returns it unchanged.</summary>
        [Test]
        public void RedactUrlCredentials_KeepsNullAndEmpty() {
            string? nothing = null;
            Assert.That(nothing.RedactUrlCredentials(), Is.Null);
            Assert.That(string.Empty.RedactUrlCredentials(), Is.EqualTo(string.Empty));
        }
    }
}
