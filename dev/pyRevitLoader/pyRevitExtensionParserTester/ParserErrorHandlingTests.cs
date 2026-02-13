using System;
using System.IO;
using System.Linq;
using NUnit.Framework;
using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;
using pyRevitLabs.NLog;
using pyRevitLabs.NLog.Config;
using pyRevitLabs.NLog.Targets;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class ParserErrorHandlingTests : TempFileTestBase
    {
        private LoggingConfiguration? _previousConfig;
        private MemoryTarget? _memoryTarget;

        [SetUp]
        public void Setup()
        {
            _previousConfig = LogManager.Configuration;

            _memoryTarget = new MemoryTarget("parserErrors")
            {
                Layout = "${message}"
            };

            var config = new LoggingConfiguration();
            config.AddTarget(_memoryTarget);
            config.AddRuleForAllLevels(_memoryTarget);
            LogManager.Configuration = config;
            LogManager.ReconfigExistingLoggers();

            ExtensionParser.ClearAllCaches();
        }

        [TearDown]
        public void TearDown()
        {
            LogManager.Configuration = _previousConfig;
            LogManager.ReconfigExistingLoggers();
            _memoryTarget?.Dispose();
        }

        [Test]
        public void BundleParseErrorsAreLoggedAndDoNotStopParsing()
        {
            var builder = new TestExtensionBuilder(TestTempDir, "BundleErrorExt");
            builder.Create()
                .AddTab("ErrorTab")
                .AddPanel("ErrorPanel")
                .AddPushButton("ErrorButton", "print('x')", "title: Test");

            var bundlePath = Path.Combine(
                builder.ExtensionPath,
                "ErrorTab.tab",
                "ErrorPanel.panel",
                "ErrorButton.pushbutton",
                "bundle.yaml");

            using (var lockStream = new FileStream(bundlePath, FileMode.Open, FileAccess.Read, FileShare.None))
            {
                var parsed = ExtensionParser.ParseInstalledExtensions(new[] { builder.ExtensionPath }).ToList();
                Assert.That(parsed.Count, Is.EqualTo(1), "Extension parsing should continue after bundle read failure.");
            }

            Assert.That(HasLoggedParseError(bundlePath),
                "Expected bundle parse error to be logged.");
        }

        [Test]
        public void ScriptParseErrorsAreLoggedAndDoNotStopParsing()
        {
            var builder = new TestExtensionBuilder(TestTempDir, "ScriptErrorExt");
            builder.Create()
                .AddTab("ErrorTab")
                .AddPanel("ErrorPanel")
                .AddPushButton("ErrorButton", "__title__ = 'Test'\n");

            var scriptPath = Path.Combine(
                builder.ExtensionPath,
                "ErrorTab.tab",
                "ErrorPanel.panel",
                "ErrorButton.pushbutton",
                "script.py");

            using (var lockStream = new FileStream(scriptPath, FileMode.Open, FileAccess.Read, FileShare.None))
            {
                var parsed = ExtensionParser.ParseInstalledExtensions(new[] { builder.ExtensionPath }).ToList();
                Assert.That(parsed.Count, Is.EqualTo(1), "Extension parsing should continue after script read failure.");
            }

            Assert.That(HasLoggedParseError(scriptPath),
                "Expected script parse error to be logged.");
        }

        [Test]
        public void ExtensionJsonParseErrorsAreLoggedAndDoNotStopParsing()
        {
            var builder = new TestExtensionBuilder(TestTempDir, "JsonErrorExt");
            builder.Create()
                .AddTab("ErrorTab")
                .AddPanel("ErrorPanel")
                .AddPushButton("ErrorButton", "print('x')");

            var extensionJsonPath = Path.Combine(builder.ExtensionPath, "extension.json");
            File.WriteAllText(extensionJsonPath, "{ invalid json }");

            var parsed = ExtensionParser.ParseInstalledExtensions(new[] { builder.ExtensionPath }).ToList();
            Assert.That(parsed.Count, Is.EqualTo(1), "Extension parsing should continue after invalid extension.json.");

            Assert.That(HasLoggedParseError(extensionJsonPath),
                "Expected extension.json parse error to be logged.");
        }

        private bool HasLoggedParseError(string filePath)
        {
            if (_memoryTarget == null)
                return false;

            return _memoryTarget.Logs.Any(message =>
                message.Contains("Error while parsing file:") &&
                message.Contains(filePath));
        }
    }
}
