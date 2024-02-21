using System;
using System.Text.RegularExpressions;
using NUnit.Framework;
using pyRevitLabs.Emojis;

namespace pyRevitLabs.Emojis.Tests
{
    public class Tests
    {
        [SetUp]
        public void Setup()
        {
        }

        [Test]
        public void TestRepeatedEmojis()
        {
            var input = ":cross_mark: :cross_mark:";
            var rendered = Emojis.Emojize(input);
            var regex = new Regex("<span><img src=");
            var matches = regex.Matches(rendered);
            Assert.AreEqual(2, matches.Count);
        }
    }
}
