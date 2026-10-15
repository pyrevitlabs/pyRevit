using System;
using System.Collections;
using System.Collections.Generic;

using NUnit.Framework;

using PyRevitLabs.PyRevit.Runtime;

namespace pyRevitExtensionParserTester
{
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

        [TestCase("PYREVIT_ROUTESSERVER")]
        [TestCase("PYREVIT_CHECKUPDATESTIMESTAMP")]
        [TestCase("PYREVIT_CHECKUPDATESRESULT")]
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