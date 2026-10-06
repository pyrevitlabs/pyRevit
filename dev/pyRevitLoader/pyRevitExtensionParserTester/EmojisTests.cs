using System.Text.RegularExpressions;

using NUnit.Framework;
using pyRevitLabs.Emojis;

namespace pyRevitExtensionParserTester
{
    [TestFixture]
    public class EmojisTests
    {
        private static int CountEmojiImages(string html)
        {
            return Regex.Matches(html, "class=\"emoji\"").Count;
        }

        [Test]
        public void ShortCodeAloneBecomesAnImage()
        {
            var html = Emojis.Emojize("pyRevit Rocket Mode enabled. :rocket:");

            Assert.That(CountEmojiImages(html), Is.EqualTo(1));
            Assert.That(html, Does.StartWith("pyRevit Rocket Mode enabled. <span>"));
            Assert.That(html, Does.Contain("title=\":rocket:\""));
        }

        [Test]
        public void ShortCodeAfterALabelColonBecomesAnImage()
        {
            var html = Emojis.Emojize("Load time: 13.62 seconds :thumbs_up:");

            Assert.That(CountEmojiImages(html), Is.EqualTo(1));
            Assert.That(html, Does.StartWith("Load time: 13.62 seconds <span>"));
            Assert.That(html, Does.Not.Contain(":thumbs_up:<"));
        }

        [Test]
        public void ShortCodeBetweenOtherColonsBecomesAnImage()
        {
            var html = Emojis.Emojize(
                "pyRevit version: 7.0.0 - </> with :growing_heart: in ['pdx', 'sea']");

            Assert.That(CountEmojiImages(html), Is.EqualTo(1));
            Assert.That(html, Does.StartWith("pyRevit version: 7.0.0 - </> with <span>"));
            Assert.That(html, Does.EndWith("</span> in ['pdx', 'sea']"));
        }

        [Test]
        public void AdjacentShortCodesBothBecomeImages()
        {
            var html = Emojis.Emojize(":rocket::thumbs_up:");

            Assert.That(CountEmojiImages(html), Is.EqualTo(2));
        }

        [Test]
        public void TextWithoutShortCodesIsUnchanged()
        {
            const string text = "12:30:45 INFO [pyrevit.loader] ratio 3:4, url http://host:8080/";

            Assert.That(Emojis.Emojize(text), Is.EqualTo(text));
        }

        [Test]
        public void UnknownShortCodeIsKeptVerbatim()
        {
            Assert.That(Emojis.Emojize("a :not_an_emoji_code: b"), Is.EqualTo("a :not_an_emoji_code: b"));
        }

        [Test]
        public void NullAndEmptyInputArePassedThrough()
        {
            Assert.That(Emojis.Emojize(null!), Is.Null);
            Assert.That(Emojis.Emojize(string.Empty), Is.EqualTo(string.Empty));
        }
    }
}
