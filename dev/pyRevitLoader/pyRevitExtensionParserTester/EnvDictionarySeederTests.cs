using NUnit.Framework;
using pyRevitAssemblyBuilder.SessionManager;

namespace pyRevitExtensionParserTester
{
    /// <summary>
    /// Tests for EnvDictionarySeeder logging level translation.
    /// Verifies that pyRevit's logging level enum (0/1/2) is correctly
    /// mapped to Python's logging module scale (30/20/10).
    /// See: issue #3203
    /// </summary>
    [TestFixture]
    public class EnvDictionarySeederTests
    {
        [Test]
        public void ToPythonLoggingLevel_Quiet_ReturnsWarning30()
        {
            // pyRevit Quiet (0) → Python logging.WARNING (30)
            Assert.AreEqual(30, EnvDictionarySeeder.ToPythonLoggingLevel(0),
                "Quiet (0) must map to logging.WARNING (30) to suppress DEBUG/INFO output");
        }

        [Test]
        public void ToPythonLoggingLevel_Verbose_ReturnsInfo20()
        {
            // pyRevit Verbose (1) → Python logging.INFO (20)
            Assert.AreEqual(20, EnvDictionarySeeder.ToPythonLoggingLevel(1),
                "Verbose (1) must map to logging.INFO (20)");
        }

        [Test]
        public void ToPythonLoggingLevel_Debug_ReturnsDebug10()
        {
            // pyRevit Debug (2) → Python logging.DEBUG (10)
            Assert.AreEqual(10, EnvDictionarySeeder.ToPythonLoggingLevel(2),
                "Debug (2) must map to logging.DEBUG (10)");
        }

        [Test]
        public void ToPythonLoggingLevel_UnexpectedValue_DefaultsToWarning30()
        {
            // Any unrecognized value should fall through to WARNING (safe default)
            Assert.AreEqual(30, EnvDictionarySeeder.ToPythonLoggingLevel(-1),
                "Negative values should default to WARNING (30)");
            Assert.AreEqual(30, EnvDictionarySeeder.ToPythonLoggingLevel(99),
                "Out-of-range values should default to WARNING (30)");
        }
    }
}
