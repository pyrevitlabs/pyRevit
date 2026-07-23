using System.IO;
using System.Linq;
using System.Reflection;
using pyRevitAssemblyBuilder.SessionManager;
using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;
using NUnit.Framework;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTester
{
    [TestFixture]
    public class ExtensionAuthUsersTests : TempFileTestBase
    {
        [TearDown]
        public void ResetParserConfig()
        {
            PyRevitConfig.ClearCache();
            ClearAllCaches();
        }

        private void UseTestPyRevitConfig(string iniContent)
        {
            var configPath = Path.Combine(TestTempDir, "pyRevit_config.ini");
            File.WriteAllText(configPath, iniContent);
            var cfg = PyRevitConfig.Load(configPath);
            ClearAllCaches();
            var field = typeof(PyRevitConfig).GetField(
                "_defaultInstance",
                BindingFlags.Static | BindingFlags.NonPublic);
            Assert.That(field, Is.Not.Null);
            field!.SetValue(null, cfg);
        }

        [Test]
        public void ParseExtension_ReadsAuthUsersFromExtensionJson()
        {
            var extPath = TestExtensionBuilder.CreateMinimalExtension(TestTempDir, "AuthFromManifest");
            File.WriteAllText(
                Path.Combine(extPath, "extension.json"),
                "{\"authusers\": [\"TestUser\"]}");

            ClearAllCaches();
            var extension = ParseInstalledExtensions(extPath).Single();

            Assert.That(extension.AuthorizedUsers, Is.EquivalentTo(new[] { "TestUser" }));
        }

        [Test]
        public void ParseExtension_ReadsAuthUsersFromExtensionsRegistry()
        {
            var extPath = TestExtensionBuilder.CreateMinimalExtension(TestTempDir, "RegistryAuthExt");
            var registryPath = Path.Combine(TestTempDir, "extensions.json");
            File.WriteAllText(
                registryPath,
                @"{
  ""extensions"": [
    {
      ""name"": ""RegistryAuthExt"",
      ""type"": ""extension"",
      ""authusers"": [""TestUser""]
    }
  ]
}");

            ClearAllCaches();
            var extension = ParseInstalledExtensions(extPath).Single();

            Assert.That(extension.AuthorizedUsers, Is.EquivalentTo(new[] { "TestUser" }));
        }

        [Test]
        public void ParseExtension_MergesAuthUsersFromManifestAndRegistry()
        {
            var extPath = TestExtensionBuilder.CreateMinimalExtension(TestTempDir, "MergedAuthExt");
            File.WriteAllText(
                Path.Combine(extPath, "extension.json"),
                "{\"name\": \"MergedAuthExt\", \"authusers\": [\"ManifestUser\"]}");
            File.WriteAllText(
                Path.Combine(TestTempDir, "extensions.json"),
                @"{
  ""extensions"": [
    {
      ""name"": ""MergedAuthExt"",
      ""type"": ""extension"",
      ""authusers"": [""RegistryUser""]
    }
  ]
}");

            ClearAllCaches();
            var extension = ParseInstalledExtensions(extPath).Single();

            Assert.That(
                extension.AuthorizedUsers,
                Is.EquivalentTo(new[] { "ManifestUser", "RegistryUser" }));
        }

        [Test]
        public void ParseExtension_ReadsAuthUsersFromConfiguredLookupSource()
        {
            var extPath = TestExtensionBuilder.CreateMinimalExtension(TestTempDir, "LookupAuthExt");
            var lookupPath = Path.Combine(TestTempDir, "custom-registry.json");
            File.WriteAllText(
                lookupPath,
                @"{
  ""extensions"": [
    {
      ""name"": ""LookupAuthExt"",
      ""type"": ""extension"",
      ""authusers"": [""LookupUser""]
    }
  ]
}");
            UseTestPyRevitConfig(
                "[environment]\n" +
                "sources = [\"" + lookupPath.Replace("\\", "\\\\") + "\"]\n");

            // UseTestPyRevitConfig already clears the parser caches before injecting
            // the test config; clearing again here would drop that injected config.
            var extension = ParseInstalledExtensions(extPath).Single();

            Assert.That(extension.AuthorizedUsers, Is.EquivalentTo(new[] { "LookupUser" }));
        }

        [Test]
        public void GetInstalledUIExtensions_ExcludesExtensionsRestrictedByRegistryAuth()
        {
            var extPath = TestExtensionBuilder.CreateMinimalExtension(TestTempDir, "UnauthorizedRegistryExt");
            File.WriteAllText(
                Path.Combine(TestTempDir, "extensions.json"),
                @"{
  ""extensions"": [
    {
      ""name"": ""UnauthorizedRegistryExt"",
      ""type"": ""extension"",
      ""authusers"": [""SomeoneElse""]
    }
  ]
}");

            ClearAllCaches();
            var parsed = ParseInstalledExtensions(extPath).Single();
            var service = new ExtensionManagerService();

            Assert.That(parsed.AuthorizedUsers, Is.EquivalentTo(new[] { "SomeoneElse" }));
            Assert.That(InvokeIsExtensionAllowed(service, parsed), Is.False);
        }

        private static bool InvokeIsExtensionAllowed(
            ExtensionManagerService service,
            ParsedExtension extension)
        {
            var method = typeof(ExtensionManagerService).GetMethod(
                "IsExtensionAllowed",
                BindingFlags.Instance | BindingFlags.NonPublic);
            Assert.That(method, Is.Not.Null);
            return (bool)method!.Invoke(service, new object[] { extension })!;
        }
    }
}
