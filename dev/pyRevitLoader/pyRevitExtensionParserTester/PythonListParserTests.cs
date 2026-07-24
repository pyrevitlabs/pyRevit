using pyRevitExtensionParser;

namespace pyRevitExtensionParserTest
{
    /// <summary>
    /// Covers the list encodings that reach userextensions and environment.sources:
    /// the canonical JSON form and the legacy Python literal form, whose Windows
    /// paths carry backslashes that are not JSON escapes.
    /// </summary>
    [TestFixture]
    internal class PythonListParserTests
    {
        [Test]
        public void EscapedJsonList_Parses()
        {
            var result = PythonListParser.Parse(@"[""C:\\Users\\ext"",""D:\\ext2""]");

            Assert.That(result, Is.EqualTo(new List<string> { @"C:\Users\ext", @"D:\ext2" }));
        }

        [Test]
        public void SingleQuotedList_UnescapedPaths_Parses()
        {
            var result = PythonListParser.Parse(@"['C:\Users\ext','D:\Program Files\x']");

            Assert.That(result, Is.EqualTo(new List<string> { @"C:\Users\ext", @"D:\Program Files\x" }));
        }

        [Test] // \t must stay two characters, not become a tab.
        public void SingleQuotedList_PathStartingWithEscapeLikeChar_IsNotInterpreted()
        {
            var result = PythonListParser.Parse(@"['C:\temp\new\ext']");

            Assert.That(result, Is.EqualTo(new List<string> { @"C:\temp\new\ext" }));
        }

        [Test] // Output of Python str() on a list of paths.
        public void SingleQuotedList_DoubledBackslashes_Parses()
        {
            var result = PythonListParser.Parse(@"['C:\\Users\\ext']");

            Assert.That(result, Is.EqualTo(new List<string> { @"C:\Users\ext" }));
        }

        [Test]
        public void SingleQuotedList_WithSpacesAfterCommas_Parses()
        {
            var result = PythonListParser.Parse(@"['C:\a', 'C:\b']");

            Assert.That(result, Is.EqualTo(new List<string> { @"C:\a", @"C:\b" }));
        }

        [Test]
        public void SingleQuotedList_EmbeddedApostrophe_IsKept()
        {
            var result = PythonListParser.Parse(@"['C:\Bob's Files\ext']");

            Assert.That(result, Is.EqualTo(new List<string> { @"C:\Bob's Files\ext" }));
        }

        [Test]
        public void SingleQuotedList_EscapedApostrophe_IsDecoded()
        {
            var result = PythonListParser.Parse(@"['C:\Bob\'s Files']");

            Assert.That(result, Is.EqualTo(new List<string> { @"C:\Bob's Files" }));
        }

        [Test]
        public void EmptyList_ParsesToEmpty()
        {
            Assert.That(PythonListParser.Parse("[]"), Is.Empty);
        }

        [Test]
        public void NonListValue_ParsesToSingleItem()
        {
            Assert.That(PythonListParser.Parse(@"C:\Tools\ext"),
                Is.EqualTo(new List<string> { @"C:\Tools\ext" }));
        }

        [Test]
        public void UnterminatedList_ParsesToEmpty()
        {
            Assert.That(PythonListParser.Parse(@"['C:\Users\ext"), Is.Empty);
        }

        [Test]
        public void RoundTrip_ThroughListString_PreservesPaths()
        {
            var original = new List<string> { @"C:\Users\ext", @"D:\Program Files\x" };

            var result = PythonListParser.Parse(PythonListParser.ToPythonListString(original));

            Assert.That(result, Is.EqualTo(original));
        }
    }
}
