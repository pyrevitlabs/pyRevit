using System;
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

        [Test]
        public void Release_LetsAnEngineNobodyHoldsBeCollected()
        {
            WeakReference engine = RunAndDropTrackedEngine();

            IronPythonRuleCaches.Release();
            for (int attempt = 0; attempt < 5 && engine.IsAlive; attempt++)
            {
                GC.Collect();
                GC.WaitForPendingFinalizers();
                GC.Collect();
            }

            Assert.That(engine.IsAlive, Is.False);
        }

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static WeakReference RunAndDropTrackedEngine()
        {
            object engine = CreateTrackedEngine();
            Execute(engine, ListExpression);
            Execute(engine, StringExpression);
            return new WeakReference(engine);
        }

        private static object CreateTrackedEngine()
        {
            Type python = IronPythonAssembly().GetType("IronPython.Hosting.Python", throwOnError: true)!;
            object engine = python.GetMethod("CreateEngine", Type.EmptyTypes)!.Invoke(null, null)!;
            typeof(IronPythonRuleCaches)
                .GetMethod("Track", BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic)!
                .Invoke(null, new[] { engine });
            return engine;
        }

        private static object? Execute(object engine, string expression)
        {
            return engine.GetType()
                .GetMethod("Execute", new[] { typeof(string) })!
                .Invoke(engine, new object[] { expression });
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
