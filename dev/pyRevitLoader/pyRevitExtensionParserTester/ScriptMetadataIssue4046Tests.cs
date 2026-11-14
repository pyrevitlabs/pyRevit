using System.Collections.Generic;
using System.IO;
using System.Linq;
using NUnit.Framework;
using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;

namespace pyRevitExtensionParserTest
{
    /// <summary>Regression coverage for #4046 script metadata and extension path parsing.</summary>
    [TestFixture]
    [Category("HostFree")]
    [Category("Integration")]
    [Category("Regression")]
    public class ScriptMetadataIssue4046Tests : TempFileTestBase
    {
        private const string ButtonName = "Probe";

        /// <summary>A trailing comment after a one-line __title__ dict keeps every locale entry.</summary>
        [Test]
        public void Title_DictWithTrailingComment_ParsesLocalizedTitles()
        {
            var button = ParseButton("__title__ = {\"en_us\": \"Doors\", \"fr_fr\": \"Portes\"}  # note\n");

            Assert.That(button.Title, Is.EqualTo("Doors"));
            Assert.That(button.GetLocalizedTitle("fr_fr"), Is.EqualTo("Portes"));
        }

        /// <summary>A trailing comment after a one-line __context__ list keeps its entries.</summary>
        [Test]
        public void Context_ListWithTrailingComment_KeepsEntries()
        {
            var button = ParseButton("__context__ = [\"OST_Doors\", \"OST_Walls\"]  # note\n");

            Assert.That(button.Context, Is.EqualTo("(OST_Doors&OST_Walls)"));
        }

        /// <summary>A comment marker inside a quoted dict value is not a comment.</summary>
        [Test]
        public void Title_DictWithHashInsideQuotes_KeepsTheHash()
        {
            var button = ParseButton("__title__ = {\"en_us\": \"Door #1\"}  # note\n");

            Assert.That(button.Title, Is.EqualTo("Door #1"));
        }

        /// <summary>A trailing comment after a boolean flag does not turn it off.</summary>
        [Test]
        public void BooleanFlags_WithTrailingComment_AreRead()
        {
            var button = ParseButton("__beta__ = True  # note\n__cleanengine__ = True  # needed\n");

            Assert.That(button.IsBeta, Is.True);
            var metadata = ExtensionParser.ReadScriptMetadata(
                Path.Combine(TestTempDir, "Probe.extension", "Tab.tab", "Panel.panel", ButtonName + ".pushbutton", "script.py"));
            Assert.That(((IDictionary<string, object>)metadata["engine"])["clean"], Is.EqualTo(true));
        }

        /// <summary>A closing quote after an escaped backslash ends the string before the comment.</summary>
        [Test]
        public void Title_DictEndingWithEscapedBackslashBeforeComment_ParsesEntries()
        {
            var button = ParseButton("__title__ = {\"en_us\": \"Doors\", \"fr_fr\": \"C:\\\\\"}  # note\n");

            Assert.That(button.Title, Is.EqualTo("Doors"));
            Assert.That(button.GetLocalizedTitle("fr_fr"), Does.StartWith("C:"));
        }

        /// <summary>A plain string __authors__ takes precedence over __author__.</summary>
        [Test]
        public void Author_AuthorsAsPlainString_WinsOverAuthor()
        {
            var button = ParseButton("__author__ = \"Ann\"\n__authors__ = \"Bob\"\n");

            Assert.That(button.Author, Is.EqualTo("Bob"));
        }

        /// <summary>An empty __authors__ string keeps the author set by __author__, in either order.</summary>
        [TestCase("__author__ = \"Ann\"\n__authors__ = \"\"\n")]
        [TestCase("__authors__ = \"\"\n__author__ = \"Ann\"\n")]
        public void Author_EmptyAuthors_KeepsAuthor(string script)
        {
            var button = ParseButton(script);

            Assert.That(button.Author, Is.EqualTo("Ann"));
        }

        /// <summary>An empty __authors__ string alone leaves no author.</summary>
        [Test]
        public void Author_EmptyAuthorsAlone_LeavesNoAuthor()
        {
            var button = ParseButton("__authors__ = \"\"\n");

            Assert.That(button.Author, Is.Null.Or.Empty);
        }

        /// <summary>A docstring closing quote at column zero does not remain in the tooltip.</summary>
        [Test]
        public void Doc_ClosingQuoteAtColumnZero_IsNotKept()
        {
            var button = ParseButton("__doc__ = \"\"\"First line\nSecond line\n\"\"\"\nprint('x')\n");

            Assert.That(button.Tooltip, Does.Not.Contain("\"\"\""));
            Assert.That(button.Tooltip, Does.StartWith("First line\nSecond line"));
        }

        /// <summary>An extension path ending in a directory separator is still parsed.</summary>
        [TestCase("\\")]
        [TestCase("/")]
        public void ParseInstalledExtensions_PathWithTrailingSeparator_ParsesExtension(string separator)
        {
            var extensionPath = CreateExtension("Probe.extension", "print('x')\n");

            var single = ExtensionParser.ParseInstalledExtensions(extensionPath + separator).ToList();
            var listed = ExtensionParser.ParseInstalledExtensions(new[] { extensionPath + separator }).ToList();

            Assert.That(single, Has.Count.EqualTo(1));
            Assert.That(listed, Has.Count.EqualTo(1));
        }

        /// <summary>Clearing user_locale returns DefaultLocale to en_us without a restart.</summary>
        [Test]
        public void DefaultLocale_UserLocaleCleared_ResetsToEnUs()
        {
            var previous = ExtensionParser.DefaultLocale;
            try
            {
                WriteUserLocale("fr_fr");
                LoadLocaleFromConfig();
                Assert.That(ExtensionParser.DefaultLocale, Is.EqualTo("fr_fr"));

                WriteUserLocale("");
                LoadLocaleFromConfig();

                Assert.That(ExtensionParser.DefaultLocale, Is.EqualTo("en_us"));
            }
            finally
            {
                ExtensionParser.DefaultLocale = previous;
            }
        }

        private void WriteUserLocale(string locale)
        {
            var configPath = Path.Combine(TestTempDir, "pyRevit_config.ini");
            File.WriteAllText(configPath, "[core]\nread_script_metadata = true\nuser_locale = " + locale + "\n");
        }

        private static void LoadLocaleFromConfig()
        {
            ExtensionParser.ClearAllCaches();
            using var enumerator = ExtensionParser.ParseInstalledExtensions().GetEnumerator();
            enumerator.MoveNext();
        }

        private string CreateExtension(string extensionName, string script)
        {
            var extensionPath = Path.Combine(TestTempDir, extensionName);
            var buttonDirectory = Path.Combine(extensionPath, "Tab.tab", "Panel.panel", ButtonName + ".pushbutton");
            Directory.CreateDirectory(buttonDirectory);
            File.WriteAllText(Path.Combine(buttonDirectory, "script.py"), script);
            return extensionPath;
        }

        private ParsedComponent ParseButton(string script)
        {
            var extensionPath = CreateExtension("Probe.extension", script);
            var extension = ExtensionParser.ParseInstalledExtensions(new[] { extensionPath }).Single();
            return extension.CollectCommandComponents().Single(c => c.Name == ButtonName);
        }
    }
}
