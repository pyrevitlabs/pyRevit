using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using NUnit.Framework;
using pyRevitAssemblyBuilder.UIManager.Buttons;
using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    /// <summary>
    /// Regression tests for #4047: link and invoke buttons resolve their assembly from their own
    /// folders and ancestor folders, never from a sibling bundle's <c>bin/</c>.
    /// </summary>
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
            catch (UnauthorizedAccessException)
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

        [Test]
        public void Resolve_UsesOwnBin_NotAnEarlierSiblingsBin()
        {
            var panel = _extension.Children[0].Children[0];
            var siblingDir = Path.Combine(panel.Directory, "A.linkbutton");
            var siblingBin = Path.Combine(siblingDir, "bin");
            Directory.CreateDirectory(siblingBin);
            File.WriteAllBytes(Path.Combine(siblingBin, "Commands.dll"), new byte[] { 0 });
            var ownBin = Path.Combine(_link.Directory, "bin");
            Directory.CreateDirectory(ownBin);
            File.WriteAllBytes(Path.Combine(ownBin, "Commands.dll"), new byte[] { 0 });
            panel.Children.Insert(0, new ParsedComponent
            {
                Type = CommandComponentType.LinkButton,
                Directory = siblingDir,
                TargetAssembly = "Commands",
                Children = new List<ParsedComponent>()
            });
            _link.TargetAssembly = "Commands";

            var resolved = LinkAssemblyPathResolver.Resolve(_link, _extension);

            Assert.That(resolved, Is.EqualTo(Path.Combine(ownBin, "Commands.dll")));
        }

        [Test]
        public void Resolve_IgnoresASiblingsBin_WhenOwnFoldersLackTheAssembly()
        {
            var panel = _extension.Children[0].Children[0];
            var siblingDir = Path.Combine(panel.Directory, "A.linkbutton");
            var siblingBin = Path.Combine(siblingDir, "bin");
            Directory.CreateDirectory(siblingBin);
            File.WriteAllBytes(Path.Combine(siblingBin, "OnlyInSibling.dll"), new byte[] { 0 });
            panel.Children.Insert(0, new ParsedComponent
            {
                Type = CommandComponentType.LinkButton,
                Directory = siblingDir,
                TargetAssembly = "OnlyInSibling",
                Children = new List<ParsedComponent>()
            });
            _link.TargetAssembly = "OnlyInSibling";

            Assert.That(LinkAssemblyPathResolver.Resolve(_link, _extension), Is.Null);
        }

        [Test]
        public void Resolve_IgnoresAnAssemblyAlreadyLoadedFromASiblingsBin()
        {
            var panel = _extension.Children[0].Children[0];
            var siblingBin = Path.Combine(panel.Directory, "A.linkbutton", "bin");
            Directory.CreateDirectory(siblingBin);
            var assemblyName = "SiblingOnly" + Guid.NewGuid().ToString("N");
            var siblingCopy = Path.Combine(siblingBin, assemblyName + ".dll");
            var compilation = CSharpCompilation.Create(
                assemblyName,
                new[] { CSharpSyntaxTree.ParseText("public class Marker { }") },
                new[] { MetadataReference.CreateFromFile(typeof(object).Assembly.Location) },
                new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary));
            Assert.That(compilation.Emit(siblingCopy).Success, Is.True);
            var loaded = Assembly.LoadFrom(siblingCopy);
            Assume.That(loaded.Location, Is.EqualTo(siblingCopy));
            _link.TargetAssembly = assemblyName;

            Assert.That(LinkAssemblyPathResolver.Resolve(_link, _extension), Is.Null);
        }

        [Test]
        public void Resolve_PrefersOwnBinOverExtensionBin()
        {
            var ownBin = Path.Combine(_link.Directory, "bin");
            Directory.CreateDirectory(ownBin);
            File.WriteAllBytes(Path.Combine(ownBin, "PyRevitLinkFixture.dll"), new byte[] { 0 });

            var resolved = LinkAssemblyPathResolver.Resolve(_link, _extension);

            Assert.That(resolved, Is.EqualTo(Path.Combine(ownBin, "PyRevitLinkFixture.dll")));
        }
    }
}
