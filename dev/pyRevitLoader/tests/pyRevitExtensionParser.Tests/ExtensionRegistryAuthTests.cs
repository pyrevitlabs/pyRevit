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

        [Test]
        public void ApplyRegistryAuthorization_ReadsRegistriesOfAllConfiguredRoots_RegardlessOfOrder()
        {
            var rootA = Path.Combine(TestTempDir, "rootA");
            var rootB = Path.Combine(TestTempDir, "rootB");
            var extA = TestExtensionBuilder.CreateMinimalExtension(rootA, "FirstExt");
            var extB = TestExtensionBuilder.CreateMinimalExtension(rootB, "SecondExt");
            File.WriteAllText(
                Path.Combine(rootB, "extensions.json"),
                @"{
  ""extensions"": [
    {
      ""name"": ""FirstExt"",
      ""type"": ""extension"",
      ""authusers"": [""FirstExtUser""]
    },
    {
      ""name"": ""SecondExt"",
      ""type"": ""extension"",
      ""authusers"": [""SomeoneElse""]
    }
  ]
}");
            var config = CreateFile(
                "pyRevit_config.ini",
                "[core]\nuserextensions = [\"" + rootA.Replace("\\", "\\\\") + "\",\"" + rootB.Replace("\\", "\\\\") + "\"]\n");
            PyRevitConfigStore.SetFactory(() => new ConfigurationBuilder(false).AddIniConfiguration(config).Build());
            ExtensionParser.ClearAllCaches();

            List<string>? usersA = null;
            List<string>? groupsA = null;
            List<string>? usersB = null;
            List<string>? groupsB = null;
            ExtensionRegistryAuth.ApplyRegistryAuthorization(extA, "FirstExt", null, ref usersA, ref groupsA);
            ExtensionRegistryAuth.ApplyRegistryAuthorization(extB, "SecondExt", null, ref usersB, ref groupsB);

            Assert.That(usersA, Is.EquivalentTo(new[] { "FirstExtUser" }));
            Assert.That(usersB, Is.EquivalentTo(new[] { "SomeoneElse" }));
        }
    }
}
