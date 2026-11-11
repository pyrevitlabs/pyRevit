using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.CompilerServices;

using NUnit.Framework;

using PyRevitLabs.PyRevit.Runtime;

namespace pyRevitExtensionParserTester
{
    /// <summary>
    /// Releasing the call-site rules IronPython's long-lived contexts cached lets a dropped engine
    /// be collected, and leaves the engines still in use working.
    /// </summary>
    /// <remarks>
    /// <c>import ctypes</c> is the bridge measured in Revit: ctypes reads a library's
    /// <c>_handle</c> through the default context, whose binder then caches a rule that holds the
    /// importing engine. The engines follow the order of Revit sessions: the first one, which owns
    /// the default context and IronPython's first-use caches, imports ctypes before the dropped
    /// one, and a successor repeats the import after it, so IronPython's static last-call caches
    /// stop pointing at the dropped engine. Only the cached rules are left to hold it.
    /// </remarks>
    [TestFixture]
    [NonParallelizable]
    [Category("HostFree")]
    [Category("Integration")]
    public class IronPythonRuleCachesTests
    {
        private const string StdLibZip = "python_342_lib.zip";

        private const string CtypesImport = "import ctypes";

        [Test]
        public void Release_AfterCtypesImport_FreesTheDroppedEngineAndKeepsTheLiveOneWorking()
        {
            var keeper = CreateEngine();
            keeper.Execute(CtypesImport);

            WeakReference dropped = ImportCtypesInDroppedEngine();
            var successor = CreateEngine();
            successor.Execute(CtypesImport);
            Collect();
            Assert.That(dropped.IsAlive, Is.True, "ctypes no longer bridges engines; this test proves nothing");

            int released = IronPythonRuleCaches.Release();
            Collect();

            Assert.That(released, Is.GreaterThan(0));
            Assert.That(dropped.IsAlive, Is.False);
            Assert.That(successor.Execute<int>("import ctypes\nlen([ctypes.c_int])"), Is.EqualTo(1));
            Assert.That(keeper.Execute<int>("import ctypes\nlen([ctypes.c_int])"), Is.EqualTo(1));
        }

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static WeakReference ImportCtypesInDroppedEngine()
        {
            var engine = CreateEngine();
            engine.Execute(CtypesImport);
            return new WeakReference(Microsoft.Scripting.Hosting.Providers.HostingHelpers.GetLanguageContext(engine));
        }

        private static Microsoft.Scripting.Hosting.ScriptEngine CreateEngine()
        {
            var engine = IronPython.Hosting.Python.CreateEngine();
            engine.SetSearchPaths(new List<string> { FindStdLibZip() });
            IronPythonRuleCaches.Track(engine);
            return engine;
        }

        private static void Collect()
        {
            for (int i = 0; i < 3; i++)
            {
                GC.Collect();
                GC.WaitForPendingFinalizers();
            }
        }

        private static string FindStdLibZip()
        {
            for (var dir = new DirectoryInfo(TestContext.CurrentContext.TestDirectory); dir != null; dir = dir.Parent)
            {
                var candidate = Path.Combine(dir.FullName, "dev", "libs", "IronPython", StdLibZip);
                if (File.Exists(candidate))
                    return candidate;
            }
            throw new FileNotFoundException("IronPython standard library not found", StdLibZip);
        }
    }
}
