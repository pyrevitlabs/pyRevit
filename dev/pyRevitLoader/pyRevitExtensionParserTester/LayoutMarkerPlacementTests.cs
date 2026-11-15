using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    /// <summary>
    /// Regression coverage for #3931: separators and slideout markers keep their place
    /// between the surrounding layout entries when an entry has no component to show.
    /// </summary>
    [TestFixture]
    [Category("HostFree")]
    [Category("Integration")]
    [Category("Regression")]
    public class LayoutMarkerPlacementTests : TempFileTestBase
    {
        /// <summary>The layout from #3931: the entry before the slideout marker has no bundle folder.</summary>
        [Test]
        public void SlideoutMarker_StaysInPlace_WhenAnEarlierEntryHasNoBundle()
        {
            var builder = new TestExtensionBuilder(TestTempDir, "MissingBundleBeforeSlideout");
            builder.Create();
            var panel = builder.AddTab("Tab").AddPanel("Panel");
            panel.AddPushButton("tools");
            panel.AddPushButton("About");
            panel.AddPushButton("Update");
            panel.AddPushButton("Settings");
            panel.WithBundleYaml(@"layout:
- tools
- Support pyRevit
- "">>>>>""
- About
- Update
- Settings");

            var children = ParseChildNames(builder.ExtensionPath, "Panel");

            Assert.That(children, Is.EqualTo(new[] { "tools", ">>>", "About", "Update", "Settings" }));
        }

        /// <summary>A component removed by its Revit version range must not move later separators.</summary>
        [Test]
        public void Separators_StayInPlace_WhenAnEarlierEntryIsOutsideItsRevitVersionRange()
        {
            var builder = new TestExtensionBuilder(TestTempDir, "VersionGatedBeforeSeparator");
            builder.Create();
            var pulldown = builder.AddTab("Tab").AddPanel("Panel").AddPulldown("Pulldown");
            pulldown.AddPushButton("First");
            pulldown.AddPushButton("NewerRevitOnly", "pass", "min_revit_version: \"2025\"");
            pulldown.AddPushButton("Second");
            pulldown.AddPushButton("Third");
            pulldown.AddPushButton("Fourth");
            pulldown.WithBundleYaml(@"layout:
  - First
  - NewerRevitOnly
  - -----
  - Second
  - Third
  - -----
  - Fourth");

            var children = ParseChildNames(builder.ExtensionPath, "Pulldown", revitYear: 2024);

            Assert.That(children, Is.EqualTo(new[] { "First", "---", "Second", "Third", "---", "Fourth" }));
        }

        /// <summary>An entry listed twice is placed once and must not move later markers.</summary>
        [Test]
        public void Separator_StaysInPlace_WhenAnEarlierEntryIsListedTwice()
        {
            var builder = new TestExtensionBuilder(TestTempDir, "DuplicateBeforeSeparator");
            builder.Create();
            var panel = builder.AddTab("Tab").AddPanel("Panel");
            panel.AddPushButton("First");
            panel.AddPushButton("Second");
            panel.WithBundleYaml(@"layout:
  - First
  - First
  - -----
  - Second");

            var children = ParseChildNames(builder.ExtensionPath, "Panel");

            Assert.That(children, Is.EqualTo(new[] { "First", "---", "Second" }));
        }

        /// <summary>Components missing from the layout still follow the laid out ones.</summary>
        [Test]
        public void UnlistedComponents_FollowTheLayout_WhenAnEarlierEntryHasNoBundle()
        {
            var builder = new TestExtensionBuilder(TestTempDir, "UnlistedAfterLayout");
            builder.Create();
            var panel = builder.AddTab("Tab").AddPanel("Panel");
            panel.AddPushButton("First");
            panel.AddPushButton("Second");
            panel.AddPushButton("Unlisted");
            panel.WithBundleYaml(@"layout:
  - First
  - Missing
  - -----
  - Second");

            var children = ParseChildNames(builder.ExtensionPath, "Panel");

            Assert.That(children, Is.EqualTo(new[] { "First", "---", "Second", "Unlisted" }));
        }

        private static List<string> ParseChildNames(string extensionPath, string containerName, int revitYear = 0)
        {
            var extension = ParseInstalledExtensions(new[] { extensionPath }, revitYear).Single();
            var container = FindComponent(extension, containerName);
            Assert.That(container, Is.Not.Null, $"'{containerName}' should be parsed");
            return container!.Children.Select(child => child.DisplayName).ToList();
        }

        private static ParsedComponent? FindComponent(ParsedComponent root, string displayName)
        {
            if (root.DisplayName == displayName)
                return root;

            foreach (var child in root.Children ?? new List<ParsedComponent>())
            {
                var found = FindComponent(child, displayName);
                if (found != null)
                    return found;
            }

            return null;
        }
    }
}
