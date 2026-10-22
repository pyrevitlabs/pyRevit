using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.Loader;

using Microsoft.VisualStudio.TestTools.UnitTesting;

using PyRevitLabs.PyRevit.Runtime;
using pyRevitLabs.PyRevit.Runtime.Shared;

namespace PyRevitLabs.PyRevit.Renderer.Tests {
    /// <summary>
    /// Pins the invariant that the isolated WebView2 load context is one per
    /// process.
    ///
    /// Every runtime version is deployed to the same engine folder and the
    /// loader sweeps that folder, so a host process holds the Revit 2025, 2026
    /// and 2027 runtimes at once. A context owned by a per-year runtime would
    /// give the process one copy of the WebView2 stack and one Chromium
    /// environment per runtime version. The context therefore lives in the
    /// shared runtime assembly, which every runtime version binds to the same
    /// instance of.
    ///
    /// The fixture is shared by the whole test class, because the process-wide
    /// context binds to the folder of its first caller and keeps it.
    /// </summary>
    [TestClass]
    public class ProcessWideLoadContextTests {
        private static IsolatedRendererFixture _fixture;

        [ClassInitialize]
        public static void CreateFixture(TestContext context) {
            _fixture = IsolatedRendererFixture.Create();
        }

        [ClassCleanup]
        public static void DisposeFixture() {
            if (_fixture != null)
                _fixture.Dispose();
        }

        [TestMethod]
        public void TheIsolatedContextIsAcquiredOnceForTheWholeProcess() {
            var first = IsolatedWebView2Context.GetOrCreate(_fixture.IsolatedDirectory);
            var contextsAfterFirstAcquisition = CountIsolatedContexts();

            var second = IsolatedWebView2Context.GetOrCreate(_fixture.IsolatedDirectory);
            var third = IsolatedWebView2Context.GetOrCreate(_fixture.IsolatedDirectory);
            var contextsAfterRepeatedAcquisition = CountIsolatedContexts();

            Assert.AreSame(
                first, second,
                "The isolated load context must be the same instance on every acquisition.");
            Assert.AreSame(
                first, third,
                "The isolated load context must be the same instance on every acquisition.");
            Assert.AreEqual(
                contextsAfterFirstAcquisition,
                contextsAfterRepeatedAcquisition,
                "Acquiring the isolated load context again must not create another one.");
        }

        [TestMethod]
        public void TheRuntimeVersionAcquiresTheProcessWideContext() {
            var shared = IsolatedWebView2Context.GetOrCreate(_fixture.IsolatedDirectory);
            var contextsBefore = CountIsolatedContexts();

            var throughRuntime = AcquireThroughRuntimeProvider();

            Assert.AreSame(
                shared, throughRuntime,
                "A runtime version must hand out the process-wide context, not one of its own.");
            Assert.AreEqual(
                contextsBefore, CountIsolatedContexts(),
                "Acquiring the context through a runtime version must not create another one.");
        }

        [TestMethod]
        public void TheRuntimeVersionHoldsNoLoadContextOfItsOwn() {
            var contextFields = typeof(ScriptRendererProvider)
                .GetFields(BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic)
                .Where(field => typeof(WebView2LoadContext).IsAssignableFrom(field.FieldType))
                .ToList();

            Assert.AreEqual(
                0, contextFields.Count,
                "A context field on a per-year runtime would give the process one WebView2 stack "
                + "per runtime version: " + string.Join(", ", contextFields.Select(field => field.Name)));
        }

        [TestMethod]
        public void TheProcessWideContextIsTheOneThatHoldsTheWebView2Stack() {
            var context = IsolatedWebView2Context.GetOrCreate(_fixture.IsolatedDirectory);

            var core = context.LoadFromAssemblyPath(
                Path.Combine(
                    _fixture.IsolatedDirectory, IsolatedRendererFixture.CoreAssemblyFileName));

            Assert.AreSame(
                context, AssemblyLoadContext.GetLoadContext(core),
                "The WebView2 stack must be bound by the process-wide load context.");
            Assert.AreNotSame(
                AssemblyLoadContext.Default, AssemblyLoadContext.GetLoadContext(core),
                "The WebView2 stack must not reach the host process default load context.");
            Assert.AreEqual(
                WebView2LoadContext.ContextName, context.Name,
                "The load context must keep the name the runtime log reports.");
        }

        private static int CountIsolatedContexts() {
            return AssemblyLoadContext.All.Count(
                context => context.Name == WebView2LoadContext.ContextName);
        }

        /// <summary>
        /// Acquires the context the way a runtime version does, through the
        /// provider every runtime version carries a copy of.
        /// </summary>
        private static WebView2LoadContext AcquireThroughRuntimeProvider() {
            var method = typeof(ScriptRendererProvider).GetMethod(
                "GetIsolatedContext", BindingFlags.Static | BindingFlags.NonPublic);
            Assert.IsNotNull(method, "The runtime must acquire the isolated context through the shared owner.");

            return (WebView2LoadContext)method.Invoke(null, null);
        }
    }
}
