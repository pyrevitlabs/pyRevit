using System;
using System.IO;

using NUnit.Framework;

namespace pyRevitLabs.Common.Tests {
    /// <summary>
    ///     Verifies URLs are started through the shell so they open on .NET 8 and later (#4050).
    /// </summary>
    [TestFixture]
    [Category("HostFree")]
    [Category("Unit")]
    public class OpenUrlTests {
        [TestCase("https://pyrevitlabs.io", "https://pyrevitlabs.io")]
        [TestCase("http://pyrevitlabs.io/docs", "http://pyrevitlabs.io/docs")]
        [TestCase("pyrevitlabs.io", "http://pyrevitlabs.io")]
        [TestCase("HTTPS://pyrevitlabs.io", "HTTPS://pyrevitlabs.io")]
        [TestCase("  pyrevitlabs.io  ", "http://pyrevitlabs.io")]
        public void UrlStartInfoUsesTheShellAndAnHttpUrl(string url, string expected) {
            var startInfo = CommonUtils.CreateUrlStartInfo(url);

            Assert.That(startInfo.UseShellExecute, Is.True);
            Assert.That(startInfo.FileName, Is.EqualTo(expected));
        }

        [TestCase(null)]
        [TestCase("")]
        [TestCase("   ")]
        public void OpeningAMissingUrlDoesNotThrow(string? url) {
            Assert.DoesNotThrow(() => CommonUtils.OpenUrl(url));
        }

        [TestCase(@"C:\docs\help.html")]
        [TestCase("file:///C:/docs/help.html")]
        [TestCase("mailto:help@pyrevitlabs.io")]
        public void ShellStartInfoKeepsTheTargetUnchanged(string target) {
            var startInfo = CommonUtils.CreateShellStartInfo(target);

            Assert.That(startInfo.UseShellExecute, Is.True);
            Assert.That(startInfo.FileName, Is.EqualTo(target));
        }

        [Test]
        public void OpeningATargetNoHandlerCanOpenDoesNotThrow() {
            var missing = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"), "missing.html");

            Assert.DoesNotThrow(() => CommonUtils.OpenWithShell(missing));
        }
    }
}
