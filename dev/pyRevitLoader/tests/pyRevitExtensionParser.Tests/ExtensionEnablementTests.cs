using System;
using System.IO;
using System.Linq;
using pyRevitExtensionParser;
using pyRevitLabs.Configurations;
using pyRevitLabs.Configurations.Ini.Extensions;
using pyRevitLoader.Tests.TestSupport;

namespace pyRevitExtensionParser.Tests
{
    /// <summary>
    /// A stored <c>disabled</c> key decides whether an extension loads; without one the
    /// manifest's <c>default_enabled</c> decides.
    /// </summary>
    [TestFixture]
    [Category("HostFree")]
    [Category("Integration")]
    public class ExtensionEnablementTests : TempFileTestBase
    {
        private string UseConfig(string ini)
        {
            var path = CreateFile("enablement_config.ini", ini);
            PyRevitConfigStore.Reset();
            PyRevitConfigStore.SetFactory(() => new ConfigurationBuilder(false).AddIniConfiguration(path).Build());
            PyRevitConfig.ClearCache();
            ExtensionParser.ClearAllCaches();
            return path;
        }

        private string CreateExtension(string name, bool? defaultEnabled)
        {
            var extDir = CreateSubDirectory(name + ".extension");
            if (defaultEnabled.HasValue)
                CreateFile(Path.Combine(name + ".extension", "extension.json"),
                    "{\"default_enabled\": \"" + (defaultEnabled.Value ? "true" : "false") + "\"}");
            return extDir;
        }

        private static bool Loads(string extDir) =>
            ExtensionParser.ParseInstalledExtensions(extDir).Any();

        [Test]
        public void StoredDisabledTrue_SkipsAnEnabledByDefaultExtension()
        {
            UseConfig("[core]\nread_script_metadata = true\n[Sample.extension]\ndisabled = true\n");
            Assert.IsFalse(Loads(CreateExtension("Sample", defaultEnabled: true)));
        }

        [Test]
        public void StoredDisabledFalse_LoadsADisabledByDefaultExtension()
        {
            UseConfig("[core]\nread_script_metadata = true\n[Sample.extension]\ndisabled = false\n");
            Assert.IsTrue(Loads(CreateExtension("Sample", defaultEnabled: false)));
        }

        [Test]
        public void SectionWithoutDisabledKey_FallsBackToTheManifest()
        {
            UseConfig("[core]\nread_script_metadata = true\n[Sample.extension]\nprivate_repo = true\n");
            Assert.IsFalse(Loads(CreateExtension("Sample", defaultEnabled: false)));

            var config = PyRevitConfig.Load().ParseExtensionByName("Sample");
            Assert.IsNotNull(config);
            Assert.IsNull(config.Disabled);
            Assert.IsTrue(config.PrivateRepo);
        }

        [Test]
        public void NoSection_FallsBackToTheManifest()
        {
            UseConfig("[core]\nread_script_metadata = true\n");
            Assert.IsNull(PyRevitConfig.Load().ParseExtensionByName("Sample"));
            Assert.IsFalse(Loads(CreateExtension("Sample", defaultEnabled: false)));
            Assert.IsTrue(Loads(CreateExtension("Other", defaultEnabled: null)));
        }

        [Test]
        public void LibrarySection_IsResolvedForTheExtensionName()
        {
            UseConfig("[core]\nread_script_metadata = true\n[Shared.lib]\ndisabled = true\n");
            var config = PyRevitConfig.Load().ParseExtensionByName("Shared");
            Assert.IsNotNull(config);
            Assert.AreEqual(true, config.Disabled);
        }

        [Test]
        public void OnlyExistingExtensionOrLibraryFolders_AreParsed()
        {
            UseConfig("[core]\nread_script_metadata = true\n");
            var plainFolder = CreateSubDirectory("NotAnExtension");
            var missing = Path.Combine(TestTempDir, "Missing.extension");
            var extension = CreateExtension("Sample", defaultEnabled: null);

            Assert.IsEmpty(ExtensionParser.ParseInstalledExtensions(" "));
            Assert.IsEmpty(ExtensionParser.ParseInstalledExtensions(missing));
            Assert.IsEmpty(ExtensionParser.ParseInstalledExtensions(plainFolder));
            Assert.IsEmpty(ExtensionParser.ParseInstalledExtensions((string[])null));
            Assert.AreEqual(1, ExtensionParser.ParseInstalledExtensions(
                new[] { " ", missing, plainFolder, extension }).Count());
        }

        [Test]
        public void BlankExtensionName_IsRejected()
        {
            UseConfig("[core]\nread_script_metadata = true\n");
            Assert.Throws<ArgumentException>(() => PyRevitConfig.Load().ParseExtensionByName(" "));
        }
    }
}
