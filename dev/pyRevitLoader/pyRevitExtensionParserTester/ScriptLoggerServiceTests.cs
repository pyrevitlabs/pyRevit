using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.Serialization;
using System.Threading.Tasks;

using NUnit.Framework;
using PyRevitLabs.PyRevit.Runtime;

namespace pyRevitExtensionParserTester {
    [TestFixture]
    public class ScriptLoggerServiceTests {
        private string _tempDirectory;

        [SetUp]
        public void SetUp() {
            _tempDirectory = Path.Combine(
                Path.GetTempPath(),
                "pyrevit-script-logger-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(_tempDirectory);
        }

        [TearDown]
        public void TearDown() {
            if (Directory.Exists(_tempDirectory))
                Directory.Delete(_tempDirectory, true);
        }

        [Test]
        public void LevelFilteringUsesRuntimeDebugOverride() {
            var service = ScriptLoggerService.GetDefault();
            service.SetMinimumLevel((int)ScriptLogLevel.Warning);

            Assert.That(service.IsVisibleEnabled((int)ScriptLogLevel.Info), Is.False);
            Assert.That(service.IsVisibleEnabled((int)ScriptLogLevel.Warning), Is.True);

            var runtime = CreateRuntime(debugMode: true, suppressOutput: true);
            Assert.That(
                ScriptLoggerService.GetForRuntime(runtime)
                    .IsVisibleEnabled((int)ScriptLogLevel.Debug),
                Is.True);
        }

        [Test]
        public void RuntimeResolutionIsStableAndPerRuntime() {
            var firstRuntime = CreateRuntime(suppressOutput: true);
            var secondRuntime = CreateRuntime(suppressOutput: true);

            Assert.That(
                ScriptLoggerService.GetForRuntime(firstRuntime),
                Is.SameAs(ScriptLoggerService.GetForRuntime(firstRuntime)));
            Assert.That(
                firstRuntime.LoggerService,
                Is.SameAs(ScriptLoggerService.GetForRuntime(firstRuntime)));
            Assert.That(
                ScriptLoggerService.GetForRuntime(firstRuntime),
                Is.Not.SameAs(ScriptLoggerService.GetForRuntime(secondRuntime)));
        }

        [Test]
        public void ErrorsAreTrackedByTheRuntimeService() {
            var path = Path.Combine(_tempDirectory, "errors.log");
            var runtime = CreateRuntime(suppressOutput: true, logFilePath: path);
            var service = ScriptLoggerService.GetForRuntime(runtime);

            service.Log("tests", (int)ScriptLogLevel.Error, "failed");

            Assert.That(service.HasErrors, Is.True);
        }

        [Test]
        public void SuppressedRuntimeStillWritesConfiguredUnicodeLog() {
            var path = Path.Combine(_tempDirectory, "suppressed.log");
            var runtime = CreateRuntime(suppressOutput: true, logFilePath: path);

            ScriptLoggerService.GetForRuntime(runtime).Log(
                "unicode",
                (int)ScriptLogLevel.Info,
                "Привет 😀");

            Assert.That(File.ReadAllText(path), Does.Contain(
                "INFO [<Test Command> unicode] Привет 😀"));
        }

        [Test]
        public void FileFormattingIncludesTimestampLevelAndCommand() {
            var path = Path.Combine(_tempDirectory, "formatted.log");
            var runtime = CreateRuntime(suppressOutput: true, logFilePath: path);

            ScriptLoggerService.GetForRuntime(runtime).Log(
                "sample",
                (int)ScriptLogLevel.Warning,
                "message");

            Assert.That(File.ReadAllText(path), Does.Match(
                @"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} WARNING \[<Test Command> sample\] message"));
        }

        [Test]
        public void ConcurrentFileWritesRemainWhole() {
            var path = Path.Combine(_tempDirectory, "concurrent.log");
            var runtime = CreateRuntime(suppressOutput: true, logFilePath: path);
            var service = ScriptLoggerService.GetForRuntime(runtime);

            Parallel.For(0, 100, index =>
                service.Log("parallel", (int)ScriptLogLevel.Info, index.ToString()));

            var lines = File.ReadAllLines(path);
            Assert.That(lines.Length, Is.EqualTo(100));
            Assert.That(lines.Distinct().Count(), Is.EqualTo(100));
        }

        [Test]
        public void DisposedRuntimeIgnoresFurtherRecords() {
            var path = Path.Combine(_tempDirectory, "disposed.log");
            var runtime = CreateRuntime(suppressOutput: true, logFilePath: path);
            var service = ScriptLoggerService.GetForRuntime(runtime);
            SetProperty(runtime, "IsDisposed", true);

            service.Log("tests", (int)ScriptLogLevel.Error, "late record");

            Assert.That(File.Exists(path), Is.False);
            Assert.That(service.HasErrors, Is.False);
        }

        [Test]
        public void DisposedRuntimeResolutionUsesSessionService() {
            var runtime = CreateRuntime(suppressOutput: true);
            SetProperty(runtime, "IsDisposed", true);

            Assert.That(
                ScriptLoggerService.GetForRuntime(runtime),
                Is.SameAs(ScriptLoggerService.GetDefault()));
        }

        [TestCase(ScriptLogLevel.Debug, "DEBUG [sample] value <tag>")]
        [TestCase(ScriptLogLevel.Info, "INFO [sample] value <tag>")]
        [TestCase(ScriptLogLevel.Warning, "&clt;div class=\"logdefault logwarning\"&cgt;&clt;strong&cgt;WARNING&clt;/strong&cgt; [sample] value <tag>&clt;/div&cgt;")]
        [TestCase(ScriptLogLevel.Error, "&clt;div class=\"logdefault logerror\"&cgt;&clt;strong&cgt;ERROR&clt;/strong&cgt; [sample] value <tag>&clt;/div&cgt;")]
        [TestCase(ScriptLogLevel.Critical, "&clt;div class=\"logdefault logcritical\"&cgt;&clt;strong&cgt;CRITICAL&clt;/strong&cgt; [sample] value <tag>&clt;/div&cgt;")]
        public void VisibleFormattingMatchesLegacyMainDocumentOutput(
            ScriptLogLevel level,
            string expected) {
            Assert.That(FormatVisibleEntry(level, "sample", "value <tag>"), Is.EqualTo(expected));
        }

        [TestCase(ScriptLogLevel.Success, "logsuccess", "SUCCESS")]
        [TestCase(ScriptLogLevel.Deprecate, "logdeprecate", "DEPRECATE")]
        public void HeaderOnlyLevelsOmitLoggerName(
            ScriptLogLevel level,
            string style,
            string levelName) {
            var expected = string.Format(
                "&clt;div class=\"logdefault {0}\"&cgt;&clt;strong&cgt;{1}&clt;/strong&cgt;{2}value <tag>&clt;/div&cgt;",
                style,
                levelName,
                Environment.NewLine);

            Assert.That(FormatVisibleEntry(level, "sample", "value <tag>"), Is.EqualTo(expected));
        }

        private static ScriptRuntime CreateRuntime(
            bool debugMode = false,
            bool suppressOutput = false,
            string logFilePath = null) {
            var runtime = (ScriptRuntime)FormatterServices.GetUninitializedObject(
                typeof(ScriptRuntime));
            SetProperty(runtime, "ScriptData", new ScriptData {
                CommandName = "Test Command",
                CommandUniqueId = "test-command"
            });
            SetProperty(runtime, "ScriptRuntimeConfigs", new ScriptRuntimeConfigs {
                DebugMode = debugMode,
                SuppressOutput = suppressOutput,
                LogFilePath = logFilePath
            });
            return runtime;
        }

        private static void SetProperty(object target, string propertyName, object value) {
            target.GetType().GetProperty(
                propertyName,
                BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic)
                .SetValue(target, value);
        }

        private static string FormatVisibleEntry(
            ScriptLogLevel level,
            string loggerName,
            string message) {
            return (string)typeof(ScriptLoggerService).GetMethod(
                "FormatVisibleEntry",
                BindingFlags.Static | BindingFlags.NonPublic)
                .Invoke(null, new object[] { level, loggerName, message });
        }
    }
}
