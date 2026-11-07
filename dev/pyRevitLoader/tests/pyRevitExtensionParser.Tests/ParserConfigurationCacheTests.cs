using System.IO;
using pyRevitExtensionParser;
using pyRevitLabs.Configurations;
using pyRevitLabs.Configurations.Ini.Extensions;
using pyRevitLoader.Tests.TestSupport;

namespace pyRevitExtensionParser.Tests
{
    /// <summary>Verifies refresh after external edits to the parser configuration.</summary>
    [TestFixture]
    [Category("HostFree")]
    [Category("Integration")]
    public class ParserConfigurationCacheTests : TempFileTestBase
    {
        /// <summary>
        ///     Verifies that clearing the loader cache refreshes settings after an external INI edit.
        /// </summary>
        [Test]
        public void ClearCache_RefreshesPyRevitConfigLoad_AfterExternalEdit()
        {
            var path = CreateFile("config.ini", "");
            File.WriteAllText(path,
                "[core]\nrocketmode = true\nloadbeta = false\n"
                + "user_locale = en_us\nread_script_metadata = true\nfilelogging = false\n");
            PyRevitConfig.ClearCache();
            PyRevitConfigStore.SetFactory(() => new ConfigurationBuilder(false).AddIniConfiguration(path).Build());
            var previous = PyRevitConfig.Load();
            Assert.IsTrue(previous.RocketMode);
            Assert.IsFalse(previous.LoadBeta);
            Assert.AreEqual("en_us", previous.UserLocale);
            Assert.IsTrue(previous.ReadScriptMetadata);
            Assert.IsFalse(previous.FileLogging);

            File.WriteAllText(path,
                "[core]\nrocketmode = false\nloadbeta = true\n"
                + "user_locale = fr_fr\nread_script_metadata = false\nfilelogging = true\n");
            Assert.AreSame(previous, PyRevitConfig.Load());
            Assert.IsTrue(PyRevitConfig.Load().RocketMode);

            PyRevitConfig.ClearCache();
            var current = PyRevitConfig.Load();
            Assert.AreNotSame(previous, current);
            Assert.IsFalse(current.RocketMode);
            Assert.IsTrue(current.LoadBeta);
            Assert.AreEqual("fr_fr", current.UserLocale);
            Assert.IsFalse(current.ReadScriptMetadata);
            Assert.IsTrue(current.FileLogging);
        }

    }
}
