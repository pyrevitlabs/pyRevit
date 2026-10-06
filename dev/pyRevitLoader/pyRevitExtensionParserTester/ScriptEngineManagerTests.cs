using System;
using System.Collections.Generic;

using NUnit.Framework;

using PyRevitLabs.PyRevit.Runtime;

using pyRevitExtensionParserTest.TestHelpers;

namespace pyRevitExtensionParserTester
{
    /// <summary>
    /// Engine cache behavior: a command gets its engine back on the next click, and the engines a
    /// previous session load or a previous copy of the runtime assembly left behind are shut down
    /// and dropped instead of piling up in the cache.
    /// </summary>
    [TestFixture]
    [NonParallelizable]
    public class ScriptEngineManagerTests : TempFileTestBase
    {
        private string _sessionId;
        private string _scriptPath;

        /// <summary>
        /// Gives the test its own session and an empty cache: both live in process-wide AppDomain
        /// data, so they are shared with every other test in the run.
        /// </summary>
        [SetUp]
        public void SetUp()
        {
            _sessionId = "session-" + Guid.NewGuid().ToString("N");
            _scriptPath = CreateFile("MyExtension.extension/script.py", "__revit__\n");

            EnvDictionary.Seed(new Dictionary<string, object>
            {
                { EnvDictionaryKeys.SessionUUID, _sessionId }
            });

            ScriptEngineManager.EngineDict.Clear();
            ScriptEngineManager.ActiveEngineDict.Clear();
        }

        [TearDown]
        public void TearDown()
        {
            ScriptEngineManager.EngineDict.Clear();
            ScriptEngineManager.ActiveEngineDict.Clear();
        }

        [Test]
        public void RepeatedExecutionOfACommandReusesTheCachedEngine()
        {
            var first = GetEngine();
            var second = GetEngine();

            Assert.That(second, Is.SameAs(first));
            Assert.That(second.RecoveredFromCache, Is.True);
            Assert.That(ScriptEngineManager.EngineDict.Count, Is.EqualTo(1));
        }

        [Test]
        public void CommandsOfDifferentExtensionsGetTheirOwnCachedEngine()
        {
            var first = GetEngine("FirstExtension.extension");
            var second = GetEngine("SecondExtension.extension");

            Assert.That(second, Is.Not.SameAs(first));
            Assert.That(ScriptEngineManager.EngineDict.Count, Is.EqualTo(2));
            Assert.That(ScriptEngineManager.EngineDict[first.TypeId], Is.SameAs(first));
            Assert.That(ScriptEngineManager.EngineDict[second.TypeId], Is.SameAs(second));
        }

        [Test]
        public void AnEngineUnderTheRequestedKeyThatThisRuntimeCannotUseIsShutDownAndDropped()
        {
            var key = GetEngine().TypeId;
            var unusableEngine = new UnusableEngine();
            ScriptEngineManager.EngineDict[key] = unusableEngine;

            var engine = GetEngine();

            Assert.That(unusableEngine.ShutdownCount, Is.EqualTo(1),
                "a cached engine nothing can cast to must be shut down, not silently overwritten");
            Assert.That(ScriptEngineManager.EngineDict[key], Is.SameAs(engine));
            Assert.That(engine.RecoveredFromCache, Is.False);

            var nextRun = GetEngine();

            Assert.That(nextRun, Is.SameAs(engine), "the replacement engine must be cacheable");
        }

        [Test]
        public void AnEngineFromAnotherCopyOfTheRuntimeIsDroppedOnTheFirstCacheMiss()
        {
            var unusableKey = _sessionId + ":IronPython:OtherExtension.extension";
            var unusableEngine = new UnusableEngine();
            ScriptEngineManager.EngineDict[unusableKey] = unusableEngine;

            GetEngine("MyExtension.extension");

            Assert.That(unusableEngine.ShutdownCount, Is.EqualTo(1));
            Assert.That(ScriptEngineManager.EngineDict.ContainsKey(unusableKey), Is.False);
        }

        [Test]
        public void EnginesCachedByAPreviousSessionLoadAreShutDownAndDropped()
        {
            var previousSessionEngine = new RecordingEngine();
            var previousSessionKey = "previous-session:IronPython:MyExtension.extension";
            ScriptEngineManager.EngineDict[previousSessionKey] = previousSessionEngine;

            var engine = GetEngine();

            Assert.That(previousSessionEngine.ShutdownCount, Is.EqualTo(1));
            Assert.That(ScriptEngineManager.EngineDict.ContainsKey(previousSessionKey), Is.False);
            Assert.That(ScriptEngineManager.EngineDict[engine.TypeId], Is.SameAs(engine));
        }

        [Test]
        public void RepeatedSessionLoadsDoNotAccumulateEnginesInTheCache()
        {
            var extensions = new[]
            {
                "FirstExtension.extension",
                "SecondExtension.extension",
                "ThirdExtension.extension"
            };

            for (int load = 0; load < 5; load++)
            {
                _sessionId = "session-" + load;
                EnvDictionary.Seed(new Dictionary<string, object>
                {
                    { EnvDictionaryKeys.SessionUUID, _sessionId }
                });

                foreach (string extension in extensions)
                    GetEngine(extension);
            }

            Assert.That(ScriptEngineManager.EngineDict.Count, Is.EqualTo(extensions.Length),
                "each session load must leave exactly its own engines cached, not one set per load");
        }

        [Test]
        public void AMidExecutionEngineIsHandedBackAndNeverShutDown()
        {
            var running = GetEngine();
            ScriptEngineManager.EnterEngine(running.TypeId);
            try
            {
                var engine = GetEngine();

                Assert.That(engine, Is.SameAs(running),
                    "a nested execution of the same command must keep using the running engine");
                Assert.That(running.ShutdownCount, Is.EqualTo(0));
                Assert.That(ScriptEngineManager.EngineDict[running.TypeId], Is.SameAs(running));
            }
            finally
            {
                ScriptEngineManager.ExitEngine(running.TypeId);
            }
        }

        [Test]
        public void AnUnusableMidExecutionEngineKeepsItsPlaceInTheCache()
        {
            var key = GetEngine().TypeId;
            var unusableEngine = new UnusableEngine();
            ScriptEngineManager.EngineDict[key] = unusableEngine;
            ScriptEngineManager.EnterEngine(key);
            try
            {
                var engine = GetEngine();

                Assert.That(unusableEngine.ShutdownCount, Is.EqualTo(0));
                Assert.That(ScriptEngineManager.EngineDict[key], Is.SameAs(unusableEngine),
                    "an engine that is still running must not be dropped from the cache");
                Assert.That(engine.RecoveredFromCache, Is.False);
            }
            finally
            {
                ScriptEngineManager.ExitEngine(key);
            }
        }

        [Test]
        public void AMidExecutionEngineFromAnotherSessionIsNotShutDown()
        {
            var previousSessionKey = "previous-session:IronPython:MyExtension.extension";
            var previousSessionEngine = new RecordingEngine();
            ScriptEngineManager.EngineDict[previousSessionKey] = previousSessionEngine;
            ScriptEngineManager.EnterEngine(previousSessionKey);
            try
            {
                GetEngine("MyExtension.extension");

                Assert.That(previousSessionEngine.ShutdownCount, Is.EqualTo(0));
                Assert.That(ScriptEngineManager.EngineDict[previousSessionKey],
                    Is.SameAs(previousSessionEngine));
            }
            finally
            {
                ScriptEngineManager.ExitEngine(previousSessionKey);
            }
        }

        [Test]
        public void ClearEnginesKeepsOnlyTheExcludedEngineAndSkipsRunningOnes()
        {
            var excluded = GetEngine("ExcludedExtension.extension");
            var cached = GetEngine("CachedExtension.extension");
            var running = GetEngine("RunningExtension.extension");
            ScriptEngineManager.EnterEngine(running.TypeId);
            try
            {
                var newCache = ScriptEngineManager.ClearEngines(excluded.TypeId);

                Assert.That(cached.ShutdownCount, Is.EqualTo(1));
                Assert.That(running.ShutdownCount, Is.EqualTo(0));
                Assert.That(newCache.Count, Is.EqualTo(1));
                Assert.That(newCache[excluded.TypeId], Is.SameAs(excluded));
                Assert.That(ScriptEngineManager.EngineDict, Is.SameAs(newCache));
            }
            finally
            {
                ScriptEngineManager.ExitEngine(running.TypeId);
            }
        }

        [Test]
        public void ClearEnginesToleratesAnEngineThatFailsToShutDown()
        {
            var broken = GetEngine("BrokenExtension.extension");
            var excluded = GetEngine("ExcludedExtension.extension");
            ScriptEngineManager.EngineDict[broken.TypeId] = new ThrowingEngine();

            var newCache = ScriptEngineManager.ClearEngines(excluded.TypeId);

            Assert.That(newCache.Count, Is.EqualTo(1));
            Assert.That(newCache[excluded.TypeId], Is.SameAs(excluded));
        }

        [Test]
        public void DescribeEngineReportsTypeAssemblyAndActiveState()
        {
            var engine = new RecordingEngine();

            string idle = ScriptEngineManager.DescribeEngine(engine, "an-engine-id");

            Assert.That(idle, Does.Contain(typeof(RecordingEngine).FullName));
            Assert.That(idle, Does.Contain(typeof(RecordingEngine).Assembly.FullName));
            Assert.That(idle, Does.Contain("active: False"));
#if !NETFRAMEWORK
            Assert.That(idle, Does.Contain("load context"),
                "engines from different load contexts are the case the cache has to report");
#endif

            ScriptEngineManager.EnterEngine("an-engine-id");
            try
            {
                Assert.That(ScriptEngineManager.DescribeEngine(engine, "an-engine-id"),
                    Does.Contain("active: True"));
            }
            finally
            {
                ScriptEngineManager.ExitEngine("an-engine-id");
            }

            Assert.That(ScriptEngineManager.DescribeEngine(null, "an-engine-id"),
                Does.Contain("no engine"));
        }

        private RecordingEngine GetEngine(string extension = "MyExtension.extension")
        {
            var runtime = CreateRuntime(extension);
            return ScriptEngineManager.GetEngine<RecordingEngine>(ref runtime);
        }

        private ScriptRuntime CreateRuntime(string extension)
        {
            var scriptData = new ScriptData
            {
                ScriptPath = _scriptPath,
                CommandName = "Test Command",
                CommandUniqueId = "test-command",
                CommandExtension = extension
            };

            var runtime = (ScriptRuntime)CreateUninitialized(typeof(ScriptRuntime));
            SetProperty(runtime, "ScriptData", scriptData);
            SetProperty(runtime, "ScriptRuntimeConfigs", new ScriptRuntimeConfigs());
            SetProperty(runtime, "EnvDict", new EnvDictionary());
            return runtime;
        }

        private static object CreateUninitialized(Type type)
        {
#if NETFRAMEWORK
            return System.Runtime.Serialization.FormatterServices.GetUninitializedObject(type);
#else
            return System.Runtime.CompilerServices.RuntimeHelpers.GetUninitializedObject(type);
#endif
        }

        private static void SetProperty(object target, string propertyName, object value)
        {
            target.GetType().GetProperty(
                propertyName,
                System.Reflection.BindingFlags.Instance
                    | System.Reflection.BindingFlags.Public
                    | System.Reflection.BindingFlags.NonPublic
                )!.SetValue(target, value);
        }

        /// <summary>Engine standing in for a cached interpreter, counting its own shutdowns.</summary>
        public class RecordingEngine : ScriptEngine
        {
            public int ShutdownCount { get; private set; }

            public override void Shutdown()
            {
                ShutdownCount++;
            }
        }

        /// <summary>
        /// Stands in for an engine left in the cache by another copy of the runtime assembly: its
        /// type derives from that copy's ScriptEngine, so this copy can never cast from it.
        /// </summary>
        public class UnusableEngine
        {
            public int ShutdownCount { get; private set; }

            public void Shutdown()
            {
                ShutdownCount++;
            }
        }

        /// <summary>Stands in for a cached engine whose shutdown blows up.</summary>
        public class ThrowingEngine
        {
            public void Shutdown()
            {
                throw new InvalidOperationException("engine is already gone");
            }
        }
    }
}
