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
        /// <summary>URL start info uses the shell, trims the URL and prefixes <c>http://</c> only when no HTTP scheme is present, in any case.</summary>
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

        /// <summary>Opening a null, empty or whitespace URL does nothing instead of throwing.</summary>
        [TestCase(null)]
        [TestCase("")]
        [TestCase("   ")]
        public void OpeningAMissingUrlDoesNotThrow(string? url) {
            Assert.DoesNotThrow(() => CommonUtils.OpenUrl(url));
        }

        /// <summary>Shell start info uses the shell and passes file paths, file URLs and mailto links through unchanged.</summary>
        [TestCase(@"C:\docs\help.html")]
        [TestCase("file:///C:/docs/help.html")]
        [TestCase("mailto:help@pyrevitlabs.io")]
        public void ShellStartInfoKeepsTheTargetUnchanged(string target) {
            var startInfo = CommonUtils.CreateShellStartInfo(target);

            Assert.That(startInfo.UseShellExecute, Is.True);
            Assert.That(startInfo.FileName, Is.EqualTo(target));
        }

        /// <summary>Opening a target the shell cannot open, such as a missing file, does not throw.</summary>
        [Test]
        public void OpeningATargetNoHandlerCanOpenDoesNotThrow() {
            var missing = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"), "missing.html");

            Assert.DoesNotThrow(() => CommonUtils.OpenWithShell(missing));
        }
    }
}
