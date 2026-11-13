using System;
using System.Collections.Generic;
using System.IO;
using NUnit.Framework;
using pyRevitAssemblyBuilder.UIManager.Buttons;
using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    [Category("HostFree")]
    [Category("Unit")]
    public class LinkAssemblyPathResolverTests
    {
        private string _root;
        private string _extensionBin;
        private ParsedExtension _extension;
        private ParsedComponent _link;

        [SetUp]
        public void SetUp()
        {
            _root = Path.Combine(Path.GetTempPath(), "pyrevit_link_" + Guid.NewGuid().ToString("N"));
            var extensionDir = Path.Combine(_root, "Tools.extension");
            var tabDir = Path.Combine(extensionDir, "Tab.tab");
            var panelDir = Path.Combine(tabDir, "Panel.panel");
            var linkDir = Path.Combine(panelDir, "Open.linkbutton");
            _extensionBin = Path.Combine(extensionDir, "bin");
            Directory.CreateDirectory(_extensionBin);
            Directory.CreateDirectory(linkDir);
            File.WriteAllBytes(Path.Combine(_extensionBin, "PyRevitLinkFixture.dll"), new byte[] { 0 });

            _link = new ParsedComponent
            {
                Type = CommandComponentType.LinkButton,
                Directory = linkDir,
                TargetAssembly = "PyRevitLinkFixture",
                Children = new List<ParsedComponent>()
            };
            var panel = new ParsedComponent
            {
                Type = CommandComponentType.Panel,
                Directory = panelDir,
                Children = new List<ParsedComponent> { _link }
            };
            var tab = new ParsedComponent
            {
                Type = CommandComponentType.Tab,
                Directory = tabDir,
                Children = new List<ParsedComponent> { panel }
            };
            _extension = new ParsedExtension
            {
                Directory = extensionDir,
                Children = new List<ParsedComponent> { tab }
            };
        }

        [TearDown]
        public void TearDown()
        {
            try
            {
                Directory.Delete(_root, true);
            }
            catch (IOException)
            {
            }
        }

        [Test]
        public void Resolve_FindsAssemblyInExtensionBin_WhenExtensionIsPassed()
        {
            var resolved = LinkAssemblyPathResolver.Resolve(_link, _extension);

            Assert.That(resolved, Is.EqualTo(Path.Combine(_extensionBin, "PyRevitLinkFixture.dll")));
        }

        [Test]
        public void Resolve_ReturnsNull_WhenExtensionIsMissing()
        {
            Assert.That(LinkAssemblyPathResolver.Resolve(_link, null), Is.Null);
        }
    }
}
