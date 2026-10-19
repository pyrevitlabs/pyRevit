#if !NETFRAMEWORK
using System;
using System.IO;
using System.Reflection;
using System.Runtime.Loader;

using NUnit.Framework;

using pyRevitLabs.PyRevit.Runtime.Shared;

namespace pyRevitLabs.PyRevit.Runtime.Shared.Tests {
    /// <summary>
    /// Exercises the deployed shared runtime's WebView2 load context: only the
    /// WebView2 stack is isolated, and a missing isolated file fails loudly.
    /// </summary>
    [TestFixture]
    [Category("HostFree")]
    [Category("Integration")]
    public class WebView2LoadContextTests {
        private string _directory;

        [SetUp]
        public void SetUp() {
            _directory = Path.Combine(Path.GetTempPath(), "pyrevit-webview2-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(_directory);
        }

        [TearDown]
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

        [Test]
        public void NonIsolatedAssemblies_FallBackToTheDefaultContext() {
            var context = new WebView2LoadContext(_directory);

            var assembly = context.LoadFromAssemblyName(typeof(Uri).Assembly.GetName());

            Assert.That(AssemblyLoadContext.GetLoadContext(assembly), Is.SameAs(AssemblyLoadContext.Default));
            Assert.That(InvokeProtected(context, "Load", new AssemblyName { Name = null }), Is.Null);
            Assert.That(context.Name, Is.EqualTo(WebView2LoadContext.ContextName));
            Assert.That(context.AssemblyDirectory, Is.EqualTo(_directory));
        }

        [Test]
        public void MissingIsolatedAssembly_FailsInsteadOfFallingBack() {
            var context = new WebView2LoadContext(_directory);

            var error = Assert.Throws<FileNotFoundException>(
                () => InvokeProtected(context, "Load", new AssemblyName("microsoft.web.webview2.core")));

            Assert.That(error.Message, Does.Contain("installation is incomplete"));
        }

        [Test]
        public void MissingNativeLoader_FailsLoudly() {
            var context = new WebView2LoadContext(_directory);

            Assert.Throws<DllNotFoundException>(() => LoadUnmanaged(context, "WebView2Loader"));
            Assert.Throws<DllNotFoundException>(() => LoadUnmanaged(context, "WebView2Loader.dll"));
        }

        [Test]
        public void OtherMissingNativeLibraries_DeferToDefaultProbing() {
            var context = new WebView2LoadContext(_directory);

            Assert.That(LoadUnmanaged(context, "not-a-webview2-library"), Is.EqualTo(IntPtr.Zero));
            Assert.That(LoadUnmanaged(context, string.Empty), Is.EqualTo(IntPtr.Zero));
        }

        [Test]
        public void IsolatedContext_IsSharedByTheWholeProcess() {
            var first = IsolatedWebView2Context.GetOrCreate(_directory);
            var second = IsolatedWebView2Context.GetOrCreate(Path.Combine(_directory, "other"));

            Assert.That(second, Is.SameAs(first));
            Assert.That(second.AssemblyDirectory, Is.EqualTo(first.AssemblyDirectory));
        }
    }
}
#endif
