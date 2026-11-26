using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using pyRevitAssemblyBuilder.UIManager;
using pyRevitExtensionParser;
using pyRevitLoader.Tests.TestSupport;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitAssemblyBuilder.Tests
{
    /// <summary>
    /// Regression coverage for #4276: a <c>layout</c> list decides what reaches the ribbon.
    /// Bundles it does not list are hidden, but their commands are still built.
    /// </summary>
    [TestFixture]
    [Category("HostFree")]
    [Category("Integration")]
    [Category("Regression")]
    public class LayoutAllowlistTests : TempFileTestBase
    {
        [Test]
        public void UnlistedPanel_IsHidden_WhenTheTabHasALayout()
        {
            var builder = new TestExtensionBuilder(TestTempDir, "UnlistedPanel");
            builder.Create();
            var tab = builder.AddTab("Tab");
            tab.AddPanel("Start").AddPushButton("Hello");
            tab.AddPanel("Hidden").AddPushButton("Ghost");
            TestExtensionBuilder.WriteBundleYaml(tab.TabPath, @"layout:
  - Start[beforeall:]");

            var extension = Parse(builder);

            Assert.That(VisibleChildNames(extension, "Tab"), Is.EqualTo(new[] { "Start" }));
        }

        [Test]
        public void UnlistedButtons_AreHidden_InPanelsAndButtonGroups()
        {
            var builder = new TestExtensionBuilder(TestTempDir, "UnlistedButtons");
            builder.Create();
            var panel = builder.AddTab("Tab").AddPanel("Panel");
            panel.AddPushButton("Listed");
            panel.AddPushButton("Unlisted");
            var pulldown = panel.AddPulldown("Pulldown");
            pulldown.AddPushButton("First");
            pulldown.AddPushButton("Second");
            pulldown.AddPushButton("Extra");
            pulldown.WithBundleYaml(@"layout:
  - First
  - -----
  - Second");
            panel.WithBundleYaml(@"layout:
  - Listed
  - Pulldown");

            var extension = Parse(builder);

            Assert.That(VisibleChildNames(extension, "Panel"), Is.EqualTo(new[] { "Listed", "Pulldown" }));
            Assert.That(VisibleChildNames(extension, "Pulldown"), Is.EqualTo(new[] { "First", "---", "Second" }));
        }

        [Test]
        public void ListedButton_IsVisible_WhenItsNameContainsTheSeparatorMarker()
        {
            var builder = new TestExtensionBuilder(TestTempDir, "MarkerInName");
            builder.Create();
            var panel = builder.AddTab("Tab").AddPanel("Panel");
            panel.AddPushButton("First");
            panel.AddPushButton("Export---CSV");
            panel.WithBundleYaml(@"layout:
  - Export---CSV
  - First");

            var extension = Parse(builder);

            Assert.That(VisibleChildNames(extension, "Panel"), Is.EqualTo(new[] { "Export---CSV", "First" }));
        }

        [Test]
        public void EveryButton_IsVisible_WhenTheContainerHasNoLayout()
        {
            var builder = new TestExtensionBuilder(TestTempDir, "NoLayout");
            builder.Create();
            var panel = builder.AddTab("Tab").AddPanel("Panel");
            panel.AddPushButton("First");
            panel.AddPushButton("Second");

            var extension = Parse(builder);

            Assert.That(VisibleChildNames(extension, "Panel"), Is.EquivalentTo(new[] { "First", "Second" }));
        }

        [Test]
        public void UnlistedCommands_AreStillCollectedForTheCommandAssembly()
        {
            var builder = new TestExtensionBuilder(TestTempDir, "UnlistedCommands");
            builder.Create();
            var panel = builder.AddTab("Tab").AddPanel("Panel");
            panel.AddPushButton("Listed");
            panel.AddPushButton("Unlisted");
            panel.WithBundleYaml(@"layout:
  - Listed");

            var extension = Parse(builder);

            Assert.That(
                extension.CollectCommandComponents().Select(command => command.DisplayName),
                Is.EquivalentTo(new[] { "Listed", "Unlisted" }));
        }

        [Test]
        public void DirectiveTargetingAnUnlistedSibling_IsAppliedToTheRibbonInstead()
        {
            var builder = new TestExtensionBuilder(TestTempDir, "DirectiveAtUnlisted");
            builder.Create();
            var tab = builder.AddTab("Tab");
            tab.AddPanel("First").AddPushButton("A");
            tab.AddPanel("Second").AddPushButton("B");
            tab.AddPanel("Modify").AddPushButton("C");
            TestExtensionBuilder.WriteBundleYaml(tab.TabPath, @"layout:
  - First
  - Second[before:Modify]");

            var extension = Parse(builder);

            Assert.That(VisibleChildNames(extension, "Tab"), Is.EqualTo(new[] { "First", "Second" }));
            Assert.That(
                extension.ExternalLayoutDirectives.Select(directive => (directive.ComponentName, directive.Target)),
                Is.EqualTo(new[] { ("Second", "Modify") }));
        }

        private static ParsedExtension Parse(TestExtensionBuilder builder)
        {
            return ParseInstalledExtensions(new[] { builder.ExtensionPath }).Single();
        }

        private static List<string> VisibleChildNames(ParsedComponent root, string containerName)
        {
            var container = FindComponent(root, containerName);
            Assert.That(container, Is.Not.Null, $"'{containerName}' should be parsed");
            return container!.Children
                .Where(child => ComponentSupportUtils.IsSupported(child, "2025", loadBeta: false))
                .Select(child => child.DisplayName)
                .ToList();
        }

        private static ParsedComponent? FindComponent(ParsedComponent root, string displayName)
        {
            if (root.DisplayName == displayName)
                return root;

            return (root.Children ?? new List<ParsedComponent>())
                .Select(child => FindComponent(child, displayName))
                .FirstOrDefault(found => found != null);
        }
    }
}
