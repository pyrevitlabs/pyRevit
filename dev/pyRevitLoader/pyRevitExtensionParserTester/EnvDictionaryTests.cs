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
        private object _originalEnvData;

        [SetUp]
        public void SetUp()
        {
            _originalEnvData = AppDomain.CurrentDomain.GetData(DomainStorageKeys.EnvVarsDictKey);
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

            var envData = (IDictionary)AppDomain.CurrentDomain.GetData(DomainStorageKeys.EnvVarsDictKey);
            envData["CUSTOM_ENVVAR"] = "stale-value";

            EnvDictionary.Seed(new Dictionary<string, object>
            {
                { EnvDictionaryKeys.SessionUUID, "new-session" }
            });

            Assert.That(envData.Contains("CUSTOM_ENVVAR"), Is.False);
            Assert.That(envData[EnvDictionaryKeys.SessionUUID], Is.EqualTo("new-session"));
            Assert.That(envData[EnvDictionaryKeys.RevitVersion], Is.EqualTo("2025.4"));
        }
    }
}