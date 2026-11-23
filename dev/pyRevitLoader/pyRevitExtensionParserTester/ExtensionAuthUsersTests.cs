using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using pyRevitAssemblyBuilder.SessionManager;
using pyRevitExtensionParser;
using pyRevitLabs.Configurations;
using pyRevitLabs.Configurations.Ini.Extensions;
using pyRevitExtensionParserTest.TestHelpers;
using NUnit.Framework;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTester
{
    [TestFixture]
    [Category("HostFree")]
    [Category("Unit")]
    public class ExtensionAuthUsersTests : TempFileTestBase
    {
        [TearDown]
        public void ResetParserConfig()
        {
            PyRevitConfigStore.Reset();
            PyRevitConfig.ClearCache();
            ClearAllCaches();
        }

        /// <summary>
        /// Points the process-wide store at a temp config, so every reader resolves
        /// it the way it resolves the real file and no machine config is touched.
        /// </summary>
        private void UseTestPyRevitConfig(string iniContent)
        {
            var configPath = Path.Combine(TestTempDir, "pyRevit_config.ini");
            File.WriteAllText(configPath, iniContent);

            PyRevitConfigStore.SetFactory(() =>
                new ConfigurationBuilder(false)
                    .AddIniConfiguration(configPath)
                    .Build());

            ClearAllCaches();
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

        /// <summary>
        /// UseTestPyRevitConfig already clears the parser caches before injecting the
        /// test config; clearing again after it would drop that injected config.
        /// </summary>
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

        [TestCase("{\"authusers\": [\"TestUser\"]")]
        [TestCase("{\"authgroups\": [\"S-1-5-32-544\"], oops}")]
        [TestCase("{\"authusers\": [\"\", \"  \"]}")]
        [TestCase("{\"authgroups\": [\"\"]}")]
        [TestCase("{\"authusers\": \"TestUser\"}")]
        public void IsExtensionAllowed_RejectsExtensionWhenAuthDefinitionIsUnreadable(string manifest)
        {
            var extPath = TestExtensionBuilder.CreateMinimalExtension(TestTempDir, "UnreadableAuthExt");
            File.WriteAllText(Path.Combine(extPath, "extension.json"), manifest);

            ClearAllCaches();
            var parsed = ParseInstalledExtensions(extPath).Single();
            var service = new ExtensionManagerService();

            Assert.That(parsed.AuthDefinitionUnreadable, Is.True);
            Assert.That(InvokeIsExtensionAllowed(service, parsed), Is.False);
        }

        [TestCase("{\"name\": \"Plain\", \"author\": \"someone\"}")]
        [TestCase("{\"authusers\": [], \"authgroups\": []}")]
        [TestCase("{\"authusers\": null}")]
        [TestCase("{\"name\": \"Plain\", ")]
        [TestCase("")]
        public void IsExtensionAllowed_AllowsExtensionWithoutAuthDefinition(string manifest)
        {
            var extPath = TestExtensionBuilder.CreateMinimalExtension(TestTempDir, "NoAuthExt");
            File.WriteAllText(Path.Combine(extPath, "extension.json"), manifest);

            ClearAllCaches();
            var parsed = ParseInstalledExtensions(extPath).Single();
            var service = new ExtensionManagerService();

            Assert.That(parsed.AuthDefinitionUnreadable, Is.False);
            Assert.That(InvokeIsExtensionAllowed(service, parsed), Is.True);
        }

        [Test]
        public void IsExtensionAllowed_AllowsListedUserWhenOtherEntriesAreEmpty()
        {
            var extPath = TestExtensionBuilder.CreateMinimalExtension(TestTempDir, "MixedAuthExt");
            var currentUser = typeof(ExtensionManagerService)
                .GetMethod("GetRevitUsername", BindingFlags.Static | BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public);
            Assert.That(currentUser, Is.Not.Null);
            var user = (string)currentUser!.Invoke(currentUser.IsStatic ? null : new ExtensionManagerService(), null)!;
            File.WriteAllText(
                Path.Combine(extPath, "extension.json"),
                "{\"authusers\": [\"\", \"" + user.Replace("\\", "\\\\") + "\"]}");

            ClearAllCaches();
            var parsed = ParseInstalledExtensions(extPath).Single();

            Assert.That(parsed.AuthDefinitionUnreadable, Is.False);
            Assert.That(parsed.AuthorizedUsers, Is.EquivalentTo(new[] { user }));
            Assert.That(InvokeIsExtensionAllowed(new ExtensionManagerService(), parsed), Is.True);
        }

        [TestCase("\"authusers\": \"SomeoneElse\"")]
        [TestCase("\"authgroups\": \"S-1-5-32-544\"")]
        [TestCase("\"authusers\": 5")]
        [TestCase("\"authgroups\": {\"sid\": \"S-1-5-32-544\"}")]
        [TestCase("\"authusers\": [\"\", \"  \"]")]
        [TestCase("\"authgroups\": [\"\"]")]
        [TestCase("\"authusers\": \"SomeoneElse\", \"authgroups\": [\"\"]")]
        public void MalformedAccessListInRegistryEntryIsRefused(string accessList)
        {
            var extPath = TestExtensionBuilder.CreateMinimalExtension(TestTempDir, "RegistryMalformedAuthExt");
            var registryPath = Path.Combine(TestTempDir, "extensions.json");
            File.WriteAllText(
                registryPath,
                "{\"extensions\": [{\"name\": \"RegistryMalformedAuthExt\", \"type\": \"extension\", " + accessList + "}]}");

            ClearAllCaches();
            var parsed = ParseCapturingErrors(extPath, out var errors);

            Assert.That(parsed.AuthDefinitionUnreadable, Is.True);
            Assert.That(InvokeIsExtensionAllowed(new ExtensionManagerService(), parsed), Is.False);
            Assert.That(
                errors.Messages,
                Has.Exactly(1).Contains(
                    "Access list in registry entry 'RegistryMalformedAuthExt' in " + registryPath + " could not be read"));
        }

        [Test]
        public void MalformedAccessListInRegistryEntryMatchedByManifestNameIsRefused()
        {
            var extPath = TestExtensionBuilder.CreateMinimalExtension(TestTempDir, "RegistryFolderNameExt");
            File.WriteAllText(
                Path.Combine(extPath, "extension.json"),
                "{\"name\": \"RegistryManifestNameExt\"}");
            File.WriteAllText(
                Path.Combine(TestTempDir, "extensions.json"),
                "{\"extensions\": [{\"name\": \"RegistryManifestNameExt\", \"type\": \"extension\", \"authusers\": \"SomeoneElse\"}]}");

            ClearAllCaches();
            var parsed = ParseInstalledExtensions(extPath).Single();

            Assert.That(parsed.AuthDefinitionUnreadable, Is.True);
            Assert.That(InvokeIsExtensionAllowed(new ExtensionManagerService(), parsed), Is.False);
        }

        [Test]
        public void MalformedSiblingRegistryEntryForSameExtensionIsRefused()
        {
            var extPath = TestExtensionBuilder.CreateMinimalExtension(TestTempDir, "RegistrySiblingExt");
            File.WriteAllText(
                Path.Combine(TestTempDir, "extensions.json"),
                "{\"extensions\": [" +
                "{\"name\": \"RegistrySiblingExt\", \"type\": \"extension\", \"authusers\": [\"ValidUser\"]}, " +
                "{\"name\": \"RegistrySiblingExt\", \"type\": \"extension\", \"authusers\": \"SomeoneElse\"}]}");

            ClearAllCaches();
            var parsed = ParseInstalledExtensions(extPath).Single();

            Assert.That(parsed.AuthorizedUsers, Is.EquivalentTo(new[] { "ValidUser" }));
            Assert.That(parsed.AuthDefinitionUnreadable, Is.True);
            Assert.That(InvokeIsExtensionAllowed(new ExtensionManagerService(), parsed), Is.False);
        }

        /// <summary>
        /// UseTestPyRevitConfig already clears the parser caches before injecting the
        /// test config; clearing again after it would drop that injected config.
        /// </summary>
        [Test]
        public void MalformedAccessListInConfiguredLookupSourceIsRefused()
        {
            var extPath = TestExtensionBuilder.CreateMinimalExtension(TestTempDir, "LookupMalformedAuthExt");
            var lookupPath = Path.Combine(TestTempDir, "custom-registry.json");
            File.WriteAllText(
                lookupPath,
                "{\"extensions\": [{\"name\": \"LookupMalformedAuthExt\", \"type\": \"extension\", \"authgroups\": [\"\"]}]}");
            UseTestPyRevitConfig(
                "[environment]\n" +
                "sources = [\"" + lookupPath.Replace("\\", "\\\\") + "\"]\n");

            var parsed = ParseInstalledExtensions(extPath).Single();

            Assert.That(parsed.AuthDefinitionUnreadable, Is.True);
            Assert.That(InvokeIsExtensionAllowed(new ExtensionManagerService(), parsed), Is.False);
        }

        [TestCase("\"authusers\": []")]
        [TestCase("\"authusers\": null, \"authgroups\": null")]
        [TestCase("\"author\": \"someone\"")]
        public void RegistryEntryWithoutAccessListLeavesExtensionAvailable(string accessList)
        {
            var extPath = TestExtensionBuilder.CreateMinimalExtension(TestTempDir, "RegistryNoAuthExt");
            File.WriteAllText(
                Path.Combine(TestTempDir, "extensions.json"),
                "{\"extensions\": [{\"name\": \"RegistryNoAuthExt\", \"type\": \"extension\", " + accessList + "}]}");

            ClearAllCaches();
            var parsed = ParseInstalledExtensions(extPath).Single();

            Assert.That(parsed.AuthDefinitionUnreadable, Is.False);
            Assert.That(InvokeIsExtensionAllowed(new ExtensionManagerService(), parsed), Is.True);
        }

        [Test]
        public void MalformedRegistryEntryForAnotherExtensionDoesNotAffectThisOne()
        {
            var extPath = TestExtensionBuilder.CreateMinimalExtension(TestTempDir, "RegistryNeighbourExt");
            File.WriteAllText(
                Path.Combine(TestTempDir, "extensions.json"),
                "{\"extensions\": [{\"name\": \"OtherExt\", \"type\": \"extension\", \"authusers\": \"SomeoneElse\"}]}");

            ClearAllCaches();
            var parsed = ParseCapturingErrors(extPath, out var errors);

            Assert.That(parsed.AuthDefinitionUnreadable, Is.False);
            Assert.That(errors.Messages, Has.None.Contains("Access list in"));
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
            UseTestPyRevitConfig(
                "[core]\n" +
                "userextensions = [\"" + rootA.Replace("\\", "\\\\") + "\",\"" + rootB.Replace("\\", "\\\\") + "\"]\n");

            List<string>? usersA = null;
            List<string>? groupsA = null;
            List<string>? usersB = null;
            List<string>? groupsB = null;
            ExtensionRegistryAuth.ApplyRegistryAuthorization(extA, "FirstExt", null, ref usersA, ref groupsA);
            ExtensionRegistryAuth.ApplyRegistryAuthorization(extB, "SecondExt", null, ref usersB, ref groupsB);

            Assert.That(usersA, Is.EquivalentTo(new[] { "FirstExtUser" }));
            Assert.That(usersB, Is.EquivalentTo(new[] { "SomeoneElse" }));
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

        private static ParsedExtension ParseCapturingErrors(string extPath, out ErrorCapture errors)
        {
            errors = new ErrorCapture();
            SetLogger(errors);
            try
            {
                return ParseInstalledExtensions(extPath).Single();
            }
            finally
            {
                SetLogger(null);
            }
        }

        private sealed class ErrorCapture : IParserLogger
        {
            public List<string> Messages { get; } = new List<string>();
            public void Debug(string message) { }
            public void Info(string message) { }
            public void Warning(string message) { }
            public void Error(string message) => Messages.Add(message);
        }
    }
}
