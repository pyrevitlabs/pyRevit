using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;

using NUnit.Framework;

using PyRevitLabs.PyRevit.Runtime;

namespace pyRevitExtensionParserTester
{
    /// <summary>
    /// Dropping the IronPython call-site rule caches on reload (#3685): the caches really are
    /// dropped, the engine keeps working, and an engine nobody holds can then be collected.
    /// </summary>
    /// <remarks>
    /// The engines are created and driven by reflection because this project does not compile
    /// against the IronPython assemblies; the Runtime's own references bring them into the
    /// output folder. Release works on process-wide state, hence <see cref="NonParallelizableAttribute"/>.
    /// </remarks>
    [TestFixture]
    [NonParallelizable]
    [Category("HostFree")]
    [Category("Unit")]
    public class IronPythonRuleCachesTests
    {
        private const string ListExpression = "len([1, 2] + [3])";
        private const string StringExpression = "'rule'.upper() + str(2)";
        private const string CtypesImport = "import ctypes";
        private const string StdLibZip = "python_342_lib.zip";

        [Test]
        public void Release_AfterATrackedEngineRanCode_DropsBinderCaches()
        {
            object engine = CreateTrackedEngine();
            Execute(engine, ListExpression);
            Execute(engine, StringExpression);

            int released = IronPythonRuleCaches.Release();

            Assert.That(released, Is.GreaterThan(0));
        }

        [Test]
        public void Release_LeavesTheEngineUsable()
        {
            object engine = CreateTrackedEngine();
            Assert.That(Execute(engine, ListExpression), Is.EqualTo(3));

            IronPythonRuleCaches.Release();

            Assert.That(Execute(engine, ListExpression), Is.EqualTo(3));
            Assert.That(Execute(engine, StringExpression), Is.EqualTo("RULE2"));
        }

        /// <remarks>
        /// <c>import ctypes</c> is the bridge measured in Revit: ctypes reads a library's
        /// <c>_handle</c> through the default context, whose binder then caches a rule that holds
        /// the importing engine. The engines follow the order of Revit sessions: the first one,
        /// which owns the default context and IronPython's first-use caches, imports ctypes before
        /// the dropped one, and a successor repeats the import after it, so IronPython's static
        /// last-call caches stop pointing at the dropped engine. In any other order those caches
        /// alone keep it alive, and the test would not show what the release does.
        /// </remarks>
        [Test]
        public void Release_LetsAnEngineNobodyHoldsBeCollected()
        {
            object first = CreateTrackedEngine();
            Execute(first, CtypesImport);
            WeakReference dropped = RunAndDropTrackedEngine();
            object successor = CreateTrackedEngine();
            Execute(successor, CtypesImport);
            Collect();
            Assert.That(dropped.IsAlive, Is.True, "ctypes no longer bridges engines; this test proves nothing");

            IronPythonRuleCaches.Release();
            Collect();

            Assert.That(dropped.IsAlive, Is.False);
            Assert.That(Execute(successor, CtypesImport + "\nlen([ctypes.c_int])"), Is.EqualTo(1));
            Assert.That(Execute(first, CtypesImport + "\nlen([ctypes.c_int])"), Is.EqualTo(1));
        }

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static WeakReference RunAndDropTrackedEngine()
        {
            object engine = CreateTrackedEngine();
            Execute(engine, CtypesImport);
            return new WeakReference(engine);
        }

        private static void Collect()
        {
            for (int attempt = 0; attempt < 3; attempt++)
            {
                GC.Collect();
                GC.WaitForPendingFinalizers();
            }
        }

        private static object CreateTrackedEngine()
        {
            Type python = IronPythonAssembly().GetType("IronPython.Hosting.Python", throwOnError: true)!;
            object engine = python.GetMethod("CreateEngine", Type.EmptyTypes)!.Invoke(null, null)!;
            engine.GetType().GetMethod("SetSearchPaths")!
                .Invoke(engine, new object[] { new List<string> { FindStdLibZip() } });
            typeof(IronPythonRuleCaches)
                .GetMethod("Track", BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic)!
                .Invoke(null, new[] { engine });
            return engine;
        }

        private static object? Execute(object engine, string expression)
        {
            MethodInfo execute = engine.GetType()
                .GetMethods(BindingFlags.Instance | BindingFlags.Public)
                .Single(method => method.Name == "Execute"
                    && !method.IsGenericMethodDefinition
                    && method.GetParameters().Length == 1
                    && method.GetParameters()[0].ParameterType == typeof(string));
            return execute.Invoke(engine, new object[] { expression });
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

        private static Assembly IronPythonAssembly()
        {
            AssemblyName name = typeof(IronPythonRuleCaches).Assembly
                .GetReferencedAssemblies()
                .First(reference => reference.Name != null
                    && reference.Name.EndsWith("IronPython", StringComparison.Ordinal));
            return Assembly.Load(name);
        }
    }
}
