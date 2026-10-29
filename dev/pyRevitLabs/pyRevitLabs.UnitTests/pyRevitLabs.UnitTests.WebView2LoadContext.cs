#if !NETFRAMEWORK
using System;
using System.IO;
using System.Reflection;
using System.Runtime.Loader;

using Microsoft.VisualStudio.TestTools.UnitTesting;

using pyRevitLabs.PyRevit.Runtime.Shared;

namespace pyRevitLabs.UnitTests {
    /// <summary>
    /// Exercises the deployed shared runtime's WebView2 load context: only the
    /// WebView2 stack is isolated, and a missing isolated file fails loudly.
    /// </summary>
    [TestClass]
    [TestCategory("HostFree")]
    [TestCategory("Integration")]
    public class WebView2LoadContextTests {
        private string _directory;

        [TestInitialize]
        public void SetUp() {
            _directory = Path.Combine(Path.GetTempPath(), "pyrevit-webview2-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(_directory);
        }

        [TestCleanup]
        public void TearDown() {
            Directory.Delete(_directory, recursive: true);
        }

        private static object InvokeProtected(WebView2LoadContext context, string methodName, object argument) {
            var method = typeof(WebView2LoadContext).GetMethod(
                methodName, BindingFlags.Instance | BindingFlags.NonPublic);
            try {
                return method.Invoke(context, new[] { argument });
            }
            catch (TargetInvocationException ex) {
                throw ex.InnerException;
            }
        }

        private static IntPtr LoadUnmanaged(WebView2LoadContext context, string name) =>
            (IntPtr)InvokeProtected(context, "LoadUnmanagedDll", name);

        [TestMethod]
        public void NonIsolatedAssemblies_FallBackToTheDefaultContext() {
            var context = new WebView2LoadContext(_directory);

            var assembly = context.LoadFromAssemblyName(typeof(Uri).Assembly.GetName());

            Assert.AreSame(AssemblyLoadContext.Default, AssemblyLoadContext.GetLoadContext(assembly));
            Assert.IsNull(InvokeProtected(context, "Load", new AssemblyName { Name = null }));
            Assert.AreEqual(WebView2LoadContext.ContextName, context.Name);
            Assert.AreEqual(_directory, context.AssemblyDirectory);
        }

        [TestMethod]
        public void MissingIsolatedAssembly_FailsInsteadOfFallingBack() {
            var context = new WebView2LoadContext(_directory);

            var error = Assert.ThrowsException<FileNotFoundException>(
                () => InvokeProtected(context, "Load", new AssemblyName("microsoft.web.webview2.core")));

            StringAssert.Contains(error.Message, "installation is incomplete");
        }

        [TestMethod]
        public void MissingNativeLoader_FailsLoudly() {
            var context = new WebView2LoadContext(_directory);

            Assert.ThrowsException<DllNotFoundException>(() => LoadUnmanaged(context, "WebView2Loader"));
            Assert.ThrowsException<DllNotFoundException>(() => LoadUnmanaged(context, "WebView2Loader.dll"));
        }

        [TestMethod]
        public void OtherMissingNativeLibraries_DeferToDefaultProbing() {
            var context = new WebView2LoadContext(_directory);

            Assert.AreEqual(IntPtr.Zero, LoadUnmanaged(context, "not-a-webview2-library"));
            Assert.AreEqual(IntPtr.Zero, LoadUnmanaged(context, string.Empty));
        }

        [TestMethod]
        public void IsolatedContext_IsSharedByTheWholeProcess() {
            var first = IsolatedWebView2Context.GetOrCreate(_directory);
            var second = IsolatedWebView2Context.GetOrCreate(Path.Combine(_directory, "other"));

            Assert.AreSame(first, second);
            Assert.AreEqual(first.AssemblyDirectory, second.AssemblyDirectory);
        }
    }
}
#endif
