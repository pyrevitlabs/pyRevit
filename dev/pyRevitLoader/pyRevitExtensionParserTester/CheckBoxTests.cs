using System.Collections.Generic;
using System.IO;
using System.Linq;
using NUnit.Framework;
using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    /// <summary>
    /// Tests for parsing .checkbox bundles.
    /// </summary>
    [TestFixture]
    [Category("HostFree")]
    [Category("Unit")]
    public class CheckBoxTests : TempFileTestBase
    {
        private const string HandlerScript = "def __chk_on_change__(sender, args, ctx):\n    pass\n";

        [Test]
        public void FromExtension_MapsCheckBoxSuffix()
        {
            Assert.That(CommandComponentTypeExtensions.FromExtension(".checkbox"), Is.EqualTo(CommandComponentType.CheckBox));
        }

        [Test]
        public void ToExtension_ReturnsCheckBoxSuffix()
        {
            Assert.That(CommandComponentType.CheckBox.ToExtension(), Is.EqualTo(".checkbox"));
        }

        [TestCase("checked: true", true)]
        [TestCase("checked: false", false)]
        [TestCase("tooltip: Without a checked key", false)]
        public void BundleYaml_ReadsCheckedKey(string yamlLine, bool expected)
        {
            var bundlePath = CreateFile("bundle.yaml", "title: Leader\n" + yamlLine + "\n");

            var bundle = BundleParser.BundleYamlParser.Parse(bundlePath);

            Assert.That(bundle.IsChecked, Is.EqualTo(expected));
        }

        [Test]
        public void ParsedExtension_CheckBoxBundleKeepsTypeAndCheckedState()
        {
            var extensionDir = CreateSubDirectory("CheckBoxTest.extension");
            var bundleDir = Path.Combine("CheckBoxTest.extension", "Test.tab", "Graphics.panel", "Leader.checkbox");
            CreateFile(Path.Combine(bundleDir, "bundle.yaml"), "title: Leader\nchecked: true\n");
            CreateFile(Path.Combine(bundleDir, "script.py"), HandlerScript);

            var extension = ParseInstalledExtensions(new[] { extensionDir }).Single();
            var checkBox = FindByDisplayName(extension.Children, "Leader");

            Assert.That(checkBox, Is.Not.Null);
            Assert.That(checkBox!.Type, Is.EqualTo(CommandComponentType.CheckBox));
            Assert.That(checkBox.IsChecked, Is.True);
        }

        [Test]
        public void ParsedExtension_StackOrdersCheckBoxChildrenByLayout()
        {
            var extensionDir = CreateSubDirectory("CheckBoxTest.extension");
            var stackDir = Path.Combine("CheckBoxTest.extension", "Test.tab", "Graphics.panel", "Leader Options.stack");
            CreateFile(Path.Combine(stackDir, "bundle.yaml"), "layout:\n- Shoulder\n- Leader\n");
            CreateFile(Path.Combine(stackDir, "Leader.checkbox", "script.py"), HandlerScript);
            CreateFile(Path.Combine(stackDir, "Shoulder.checkbox", "script.py"), HandlerScript);

            var extension = ParseInstalledExtensions(new[] { extensionDir }).Single();
            var stack = FindByDisplayName(extension.Children, "Leader Options");

            Assert.That(stack, Is.Not.Null);
            Assert.That(stack!.Type, Is.EqualTo(CommandComponentType.Stack));
            Assert.That(stack.Children!.Select(child => child.DisplayName), Is.EqualTo(new[] { "Shoulder", "Leader" }));
            Assert.That(stack.Children!.Select(child => child.Type), Is.All.EqualTo(CommandComponentType.CheckBox));
        }

        private static ParsedComponent? FindByDisplayName(IEnumerable<ParsedComponent>? components, string displayName)
        {
            foreach (var component in components ?? Enumerable.Empty<ParsedComponent>())
            {
                if (component.DisplayName == displayName)
                    return component;

                var nested = FindByDisplayName(component.Children, displayName);
                if (nested != null)
                    return nested;
            }

            return null;
        }
    }
}
