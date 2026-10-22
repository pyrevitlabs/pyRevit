using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.Loader;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Interop;
using System.Windows.Threading;

using Microsoft.VisualStudio.TestTools.UnitTesting;

using PyRevitLabs.PyRevit.Renderer;
using PyRevitLabs.PyRevit.Runtime;
using pyRevitLabs.PyRevit.Runtime.Shared;

namespace PyRevitLabs.PyRevit.Renderer.Tests {
    /// <summary>
    /// Spike tests for the WebView2 load-context isolation.
    ///
    /// The assumptions these tests pin down are the ones the fix rests on:
    /// the WebView2 stack can be hosted in a dedicated load context while the
    /// WPF framework assemblies stay in the default context, so the isolated
    /// control keeps its type identity and can enter a visual tree; the
    /// native loader is found next to the managed assemblies; and a WebView2
    /// core that the host process already carries never gets unified with the
    /// one the renderer binds to.
    ///
    /// The last one is the mechanism behind pyRevit#3806: the host bound a
    /// newer WebView2 wrapper against its own older core and crashed the
    /// process.
    /// </summary>
    [TestClass]
    public class WebView2IsolationSpikeTests {
        private const string CoreTypeName = "Microsoft.Web.WebView2.Core.CoreWebView2Environment";
        private const string EnvironmentOptionsTypeName =
            "Microsoft.Web.WebView2.Core.CoreWebView2EnvironmentOptions";
        private const string ControlTypeName = "Microsoft.Web.WebView2.Wpf.WebView2";

        private IsolatedRendererFixture _fixture;
        private WebView2LoadContext _context;

        [TestInitialize]
        public void SetUp() {
            _fixture = IsolatedRendererFixture.Create();
            _context = new WebView2LoadContext(_fixture.IsolatedDirectory);
        }

        [TestCleanup]
        public void TearDown() {
            if (_fixture != null)
                _fixture.Dispose();
        }

        [TestMethod]
        public void WebView2Core_IsLoadedIntoTheIsolatedLoadContext() {
            var core = LoadIsolated(IsolatedRendererFixture.CoreAssemblyFileName);

            Assert.AreSame(_context, AssemblyLoadContext.GetLoadContext(core));
        }

        [TestMethod]
        public void WebView2WpfAssembly_IsLoadedIntoTheIsolatedLoadContext() {
            var wpf = LoadIsolated(IsolatedRendererFixture.WpfAssemblyFileName);

            Assert.AreSame(_context, AssemblyLoadContext.GetLoadContext(wpf));
        }

        [TestMethod]
        public void RendererAssembly_IsLoadedIntoTheIsolatedLoadContext() {
            var renderer = LoadIsolated(IsolatedRendererFixture.RendererAssemblyFileName);

            Assert.AreSame(_context, AssemblyLoadContext.GetLoadContext(renderer));
        }

        [TestMethod]
        public void IsolatedWebView2Assemblies_AreNotLoadedIntoTheDefaultLoadContext() {
            var isolated = new[] {
                LoadIsolated(IsolatedRendererFixture.CoreAssemblyFileName),
                LoadIsolated(IsolatedRendererFixture.WpfAssemblyFileName),
                LoadIsolated(IsolatedRendererFixture.RendererAssemblyFileName),
            };

            var defaultAssemblies = AssemblyLoadContext.Default.Assemblies.ToList();
            foreach (var assembly in isolated) {
                Assert.IsFalse(
                    defaultAssemblies.Any(a => ReferenceEquals(a, assembly)),
                    "'" + assembly.GetName().Name + "' must not be loaded into the default context.");
            }
        }

        [TestMethod]
        public void WpfFrameworkAssemblies_AreNotDuplicatedIntoTheIsolatedLoadContext() {
            LoadIsolated(IsolatedRendererFixture.WpfAssemblyFileName);

            var duplicated = new[] { "PresentationFramework", "WindowsBase", "System.Xaml" }
                .Where(name => _context.Assemblies.Any(a => a.GetName().Name == name))
                .ToList();

            Assert.AreEqual(0, duplicated.Count, "Duplicated WPF assemblies: " + string.Join(", ", duplicated));
        }

        [TestMethod]
        public void WpfFrameworkAssemblies_StayInTheDefaultLoadContext() {
            LoadIsolated(IsolatedRendererFixture.WpfAssemblyFileName);

            Assert.AreSame(
                AssemblyLoadContext.Default,
                AssemblyLoadContext.GetLoadContext(typeof(FrameworkElement).Assembly));
        }

        [TestMethod]
        public void IsolatedWebView2Control_DerivesFromTheDefaultLoadContextHwndHost() {
            var controlType = LoadIsolated(IsolatedRendererFixture.WpfAssemblyFileName)
                .GetType(ControlTypeName, throwOnError: true);

            Assert.AreSame(typeof(HwndHost), controlType.BaseType);
            Assert.IsTrue(typeof(FrameworkElement).IsAssignableFrom(controlType));
        }

        [TestMethod]
        public void IsolatedRenderer_BindsTheWebView2CoreFromTheIsolatedFolder() {
            var coreAssembly = StaTestRunner.Run(() => {
                using (var renderer = CreateIsolatedRenderer()) {
                    return ResolveControlCoreAssembly(renderer);
                }
            });

            Assert.AreEqual(IsolatedRendererFixture.CoreAssemblyName, coreAssembly.GetName().Name);
            Assert.AreSame(_context, AssemblyLoadContext.GetLoadContext(coreAssembly));
        }

        [TestMethod]
        public void IsolatedRenderer_BindsItsOwnCoreTypeWithoutUnifyingWithTheHostCopy() {
            var hostCorePath = _fixture.StageHostCoreCopy();
            var hostCore = LoadHostCore(hostCorePath);

            var isolatedCoreAssembly = StaTestRunner.Run(() => {
                using (var renderer = CreateIsolatedRenderer()) {
                    return ResolveControlCoreAssembly(renderer);
                }
            });

            Assert.AreSame(AssemblyLoadContext.Default, AssemblyLoadContext.GetLoadContext(hostCore));

            var hostType = hostCore.GetType(CoreTypeName, throwOnError: true);
            var isolatedType = isolatedCoreAssembly.GetType(CoreTypeName, throwOnError: true);

            Assert.AreNotSame(hostType, isolatedType);
        }

        [TestMethod]
        public void IsolatedWebView2Control_ExposesTheIsolatedCoreType() {
            var controlType = LoadIsolated(IsolatedRendererFixture.WpfAssemblyFileName)
                .GetType(ControlTypeName, throwOnError: true);
            var coreProperty = controlType.GetProperty("CoreWebView2");
            Assert.IsNotNull(coreProperty, "The WebView2 control must expose its core.");

            var coreAssembly = coreProperty.PropertyType.Assembly;

            Assert.AreEqual(IsolatedRendererFixture.CoreAssemblyName, coreAssembly.GetName().Name);
            Assert.AreSame(_context, AssemblyLoadContext.GetLoadContext(coreAssembly));
        }

        [TestMethod]
        public void IsolatedContext_ResolvesTheNativeWebView2LoaderFromTheIsolatedFolder() {
            var handle = InvokeLoadUnmanagedDll(IsolatedRendererFixture.NativeLoaderFileName);

            Assert.AreNotEqual(IntPtr.Zero, handle);
        }

        [TestMethod]
        public void IsolatedContext_DoesNotResolveAnUnknownNativeLibrary() {
            var handle = InvokeLoadUnmanagedDll("pyrevit-not-a-deployed-native-library.dll");

            Assert.AreEqual(IntPtr.Zero, handle);
        }

        [TestMethod]
        public void IsolatedRenderer_CanBePlacedInAWpfVisualTree() {
            StaTestRunner.Run(() => {
                using (var renderer = CreateIsolatedRenderer()) {
                    FrameworkElement element = renderer.Control;

                    Assert.IsNotNull(element);
                    Assert.IsInstanceOfType(element, typeof(HwndHost));

                    var grid = new Grid();
                    grid.Children.Add(element);

                    Assert.AreEqual(1, grid.Children.Count);
                }
            });
        }

        /// <summary>
        /// WebView2 creates its environment only on a single-threaded-apartment
        /// thread whose dispatcher is pumping, so the creation runs on an STA
        /// thread with a frame instead of blocking the test thread on the task:
        /// blocking would starve the callbacks the environment start depends
        /// on and fail on machines where the runtime is actually available.
        /// </summary>
        [TestMethod]
        public void IsolatedRenderer_StartsTheBrowserWhenTheEvergreenRuntimeIsAvailable() {
            var core = LoadIsolated(IsolatedRendererFixture.CoreAssemblyFileName);
            if (!IsBrowserRuntimeInstalled(core))
                Assert.Inconclusive(
                    "The WebView2 Evergreen runtime is not installed on this machine.");

            var environmentType = core.GetType(CoreTypeName, throwOnError: true);
            var optionsType = core.GetType(EnvironmentOptionsTypeName, throwOnError: true);
            var createAsync = environmentType.GetMethod(
                "CreateAsync", new[] { typeof(string), typeof(string), optionsType });
            Assert.IsNotNull(createAsync, "The core must expose the environment factory.");

            var userDataFolder = Path.Combine(
                Path.GetTempPath(), "pyrevit-renderer-spike-browser");

            StaTestRunner.Run(() => {
                var dispatcher = Dispatcher.CurrentDispatcher;
                var options = Activator.CreateInstance(optionsType);
                var creation = (Task)createAsync.Invoke(
                    null, new object[] { null, userDataFolder, options });

                var frame = new DispatcherFrame();
                var timeout = new DispatcherTimer(
                    TimeSpan.FromSeconds(60),
                    DispatcherPriority.Background,
                    (sender, args) => frame.Continue = false,
                    dispatcher);
                timeout.Start();

                creation.ContinueWith(
                    completed => dispatcher.BeginInvoke(new Action(() => frame.Continue = false)),
                    TaskScheduler.Default);

                Dispatcher.PushFrame(frame);
                timeout.Stop();

                Assert.IsTrue(
                    creation.IsCompleted,
                    "The browser environment did not come up in time.");
                Assert.IsFalse(
                    creation.IsFaulted,
                    "The browser environment failed to start: "
                    + (creation.Exception == null
                        ? "unknown error"
                        : creation.Exception.GetBaseException().Message));
            });
        }

        private Assembly LoadIsolated(string fileName) {
            var path = Path.Combine(_fixture.IsolatedDirectory, fileName);
            return _context.LoadFromAssemblyPath(path);
        }

        private Assembly LoadHostCore(string path) {
            var loaded = AssemblyLoadContext.Default.Assemblies
                .FirstOrDefault(a => a.GetName().Name == IsolatedRendererFixture.CoreAssemblyName);
            if (loaded != null)
                return loaded;

            return AssemblyLoadContext.Default.LoadFromAssemblyPath(path);
        }

        private IScriptRenderer CreateIsolatedRenderer() {
            return ScriptRendererProvider.CreateIsolated(
                _context, _fixture.IsolatedDirectory, Dispatcher.CurrentDispatcher);
        }

        /// <summary>
        /// The core assembly the isolated control binds to. Reading the
        /// property type is what makes the runtime resolve the core, so the
        /// resolution happens through the isolated context and not by chance.
        /// </summary>
        private static Assembly ResolveControlCoreAssembly(IScriptRenderer renderer) {
            var coreProperty = renderer.Control.GetType().GetProperty("CoreWebView2");
            Assert.IsNotNull(coreProperty, "The WebView2 control must expose its core.");

            return coreProperty.PropertyType.Assembly;
        }

        private IntPtr InvokeLoadUnmanagedDll(string libraryFileName) {
            var method = typeof(WebView2LoadContext).GetMethod(
                "LoadUnmanagedDll", BindingFlags.Instance | BindingFlags.NonPublic);
            Assert.IsNotNull(method, "The load context must override the native library probing.");

            return (IntPtr)method.Invoke(_context, new object[] { libraryFileName });
        }

        private static bool IsBrowserRuntimeInstalled(Assembly core) {
            var environmentType = core.GetType(CoreTypeName, throwOnError: true);
            var method = environmentType.GetMethod(
                "GetAvailableBrowserVersionString",
                BindingFlags.Public | BindingFlags.Static,
                null,
                new[] { typeof(string) },
                null);
            Assert.IsNotNull(
                method,
                "The core must expose the browser version probe. Its signature changed, so "
                + "the browser-start test can no longer tell a missing runtime from a broken one.");

            try {
                return method.Invoke(null, new object[] { null }) is string;
            }
            catch (TargetInvocationException ex) when (
                ex.InnerException != null
                && ex.InnerException.GetType().Name == "WebView2RuntimeNotFoundException") {
                return false;
            }
        }
    }
}
