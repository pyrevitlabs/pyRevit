using System.IO;
using pyRevitExtensionParser;
using pyRevitLabs.Configurations;
using pyRevitLabs.Configurations.Ini.Extensions;
using pyRevitLoader.Tests.TestSupport;

namespace pyRevitExtensionParser.Tests
{
    /// <summary>Authorization lookup includes the configured root as well as the bundle parent.</summary>
    [TestFixture]
    [Category("HostFree")]
    [Category("Integration")]
    public class ExtensionRegistryAuthTests : TempFileTestBase
    {
        /// <summary>Nested extensions inherit registry authorization from their configured root.</summary>
        [Test]
        [Category("Regression")]
        public void CollectDefinitionSourcePaths_NestedExtension_IncludesConfiguredRoot()
        {
            var root = CreateSubDirectory("extensions");
            var extension = CreateSubDirectory("extensions/nested/Fixture.extension");
            var config = CreateFile("lookup.ini", "[core]\nuserextensions = [\"" + root.Replace("\\", "\\\\") + "\"]\n");
            PyRevitConfigStore.SetFactory(() => new ConfigurationBuilder(false).AddIniConfiguration(config).Build());
            ExtensionParser.ClearAllCaches();

            var paths = ExtensionRegistryAuth.CollectDefinitionSourcePaths(extension);

            Assert.That(paths, Does.Contain(Path.Combine(root, "extensions.json")));
            Assert.That(paths, Does.Contain(Path.Combine(root, "nested", "extensions.json")));
        }
    }
}
