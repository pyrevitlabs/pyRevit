using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Runtime.CompilerServices;

using NUnit.Framework;

using PyRevitLabs.PyRevit.Runtime;

namespace pyRevitExtensionParserTester
{
    /// <summary>Verifies the environment values shared by Python and the session loader.</summary>
    [TestFixture]
    [NonParallelizable]
    public class EnvDictionaryTests
    {
        private object? _originalEnvData;

        [SetUp]
        public void SetUp()
        {
            _originalEnvData = AppDomain.CurrentDomain.GetData(DomainStorageKeys.EnvVarsDictKey);
            AppDomain.CurrentDomain.SetData(DomainStorageKeys.EnvVarsDictKey, null);
        }

        [TearDown]
        public void TearDown()
        {
            AppDomain.CurrentDomain.SetData(DomainStorageKeys.EnvVarsDictKey, _originalEnvData);
        }

        [Test]
        public void SeedRemovesCustomKeysAndPreservesOtherCoreKeys()
        {
            EnvDictionary.Seed(new Dictionary<string, object>
            {
                { EnvDictionaryKeys.SessionUUID, "previous-session" },
                { EnvDictionaryKeys.RevitVersion, "2025.4" }
            });

            var envData = (IDictionary)AppDomain.CurrentDomain.GetData(DomainStorageKeys.EnvVarsDictKey)!;
            envData["CUSTOM_ENVVAR"] = "stale-value";

            EnvDictionary.Seed(new Dictionary<string, object>
            {
                { EnvDictionaryKeys.SessionUUID, "new-session" }
            });

            Assert.That(envData.Contains("CUSTOM_ENVVAR"), Is.False);
            Assert.That(envData[EnvDictionaryKeys.SessionUUID], Is.EqualTo("new-session"));
            Assert.That(envData[EnvDictionaryKeys.RevitVersion], Is.EqualTo("2025.4"));
        }

        private static IEnumerable<string> PythonCoreKeys()
        {
            yield return EnvDictionaryKeys.RoutesServer;
            yield return EnvDictionaryKeys.CheckUpdatesTimestamp;
            yield return EnvDictionaryKeys.CheckUpdatesResult;
        }

        private static string ReadPythonEnvironmentKeys([CallerFilePath] string sourcePath = "")
        {
            var repositoryPath = Path.GetFullPath(Path.Combine(Path.GetDirectoryName(sourcePath)!, "..", "..", ".."));
            return File.ReadAllText(Path.Combine(repositoryPath, "pyrevitlib", "pyrevit", "coreutils", "envvars.py"));
        }

        /// <summary>Pins the C# environment key names to the literals used by Python.</summary>
        [Test]
        public void PythonSetKeysHaveMatchingCSharpConstants()
        {
            Assert.That(EnvDictionaryKeys.RoutesServer, Is.EqualTo("PYREVIT_ROUTESSERVER"));
            Assert.That(EnvDictionaryKeys.CheckUpdatesTimestamp, Is.EqualTo("PYREVIT_CHECKUPDATESTIMESTAMP"));
            Assert.That(EnvDictionaryKeys.CheckUpdatesResult, Is.EqualTo("PYREVIT_CHECKUPDATESRESULT"));
            var pythonEnvironmentKeys = ReadPythonEnvironmentKeys();
            Assert.That(pythonEnvironmentKeys, Does.Match(@"(?m)^PRODUCT_NAME = str\(Common\.PyRevitLabsConsts\.ProductName\)\.upper\(\)\r?$"));
            Assert.That(pythonEnvironmentKeys, Does.Match(@"(?m)^ROUTES_SERVER = PRODUCT_NAME \+ ""_ROUTESSERVER""\r?$"));
            Assert.That(pythonEnvironmentKeys, Does.Match(@"(?m)^CHECKUPDATES_TIMESTAMP_ENVVAR = PRODUCT_NAME \+ ""_CHECKUPDATESTIMESTAMP""\r?$"));
            Assert.That(pythonEnvironmentKeys, Does.Match(@"(?m)^CHECKUPDATES_RESULT_ENVVAR = PRODUCT_NAME \+ ""_CHECKUPDATESRESULT""\r?$"));
        }

        /// <summary>
        ///     Verifies that repeated session seeding preserves Python core values and removes custom values.
        /// </summary>
        /// <param name="key">The Python core environment key preserved across reloads.</param>
        [TestCaseSource(nameof(PythonCoreKeys))]
        public void SeedPreservesPythonCoreValuesAcrossRepeatedReloads(string key)
        {
            EnvDictionary.Seed(new Dictionary<string, object>());
            var envData = (IDictionary)AppDomain.CurrentDomain.GetData(DomainStorageKeys.EnvVarsDictKey)!;
            var value = new object();
            envData[key] = value;

            for (var reload = 0; reload < 2; reload++)
            {
                envData["CUSTOM_ENVVAR"] = "stale-value";

                EnvDictionary.Seed(new Dictionary<string, object>
                {
                    { EnvDictionaryKeys.SessionUUID, $"session-{reload}" }
                });

                var reloadedEnvData = (IDictionary)AppDomain.CurrentDomain.GetData(DomainStorageKeys.EnvVarsDictKey)!;
                Assert.That(reloadedEnvData[key], Is.SameAs(value));
                Assert.That(reloadedEnvData.Contains("CUSTOM_ENVVAR"), Is.False);
            }
        }
    }
}