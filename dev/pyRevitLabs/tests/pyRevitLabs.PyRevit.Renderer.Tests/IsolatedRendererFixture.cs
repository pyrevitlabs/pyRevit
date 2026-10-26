using System;
using System.IO;

namespace PyRevitLabs.PyRevit.Renderer.Tests {
    /// <summary>
    /// A fake pyRevit deployment used by the load-context spike tests.
    ///
    /// The layout mirrors a real installation: the runtime assembly sits in an
    /// engine folder below the binary folder, and the WebView2 stack sits in
    /// the isolated folder next to it. The discovery of those folders walks
    /// up from the runtime assembly location until it finds the folder that
    /// holds the engines, so the marker folder has to be there.
    /// </summary>
    internal sealed class IsolatedRendererFixture : IDisposable {
        internal const string CoreAssemblyFileName = "Microsoft.Web.WebView2.Core.dll";
        internal const string WpfAssemblyFileName = "Microsoft.Web.WebView2.Wpf.dll";
        internal const string WinFormsAssemblyFileName = "Microsoft.Web.WebView2.WinForms.dll";
        internal const string NativeLoaderFileName = "WebView2Loader.dll";
        internal const string RendererAssemblyFileName = "pyRevitLabs.PyRevit.WebView2.dll";

        internal const string CoreAssemblyName = "Microsoft.Web.WebView2.Core";

        private static readonly string[] WebView2AssemblyFileNames = {
            CoreAssemblyFileName,
            WpfAssemblyFileName,
            WinFormsAssemblyFileName,
        };

        private readonly string _root;

        private IsolatedRendererFixture(string root) {
            _root = root;
            BinDirectory = Path.Combine(root, "bin", "netcore");
            IsolatedDirectory = Path.Combine(BinDirectory, "isolated");
            EngineDirectory = Path.Combine(BinDirectory, "engines", "IPY2712PR");
            HostDirectory = Path.Combine(root, "host");
        }

        /// <summary>Root of the fake installation.</summary>
        internal string Root {
            get { return _root; }
        }

        /// <summary>The binary folder, the one that holds the engines.</summary>
        internal string BinDirectory {
            get; private set;
        }

        /// <summary>The folder the WebView2 stack is deployed to.</summary>
        internal string IsolatedDirectory {
            get; private set;
        }

        /// <summary>The engine folder the runtime assembly is deployed to.</summary>
        internal string EngineDirectory {
            get; private set;
        }

        /// <summary>A folder outside the isolated one, used to stage a host copy of the core.</summary>
        internal string HostDirectory {
            get; private set;
        }

        /// <summary>
        /// Builds the fake deployment out of the staged WebView2 package files
        /// and the renderer the build produces.
        /// </summary>
        internal static IsolatedRendererFixture Create() {
            var root = Path.Combine(
                Path.GetTempPath(),
                "pyrevit-renderer-spike-" + Guid.NewGuid().ToString("N"));
            var fixture = new IsolatedRendererFixture(root);
            fixture.Populate();
            return fixture;
        }

        /// <summary>
        /// Copies the WebView2 core out of the isolated folder, so that it can
        /// be loaded into the default load context the way a host process that
        /// already carries its own WebView2 would.
        /// </summary>
        internal string StageHostCoreCopy() {
            var hostCorePath = Path.Combine(HostDirectory, CoreAssemblyFileName);
            File.Copy(Path.Combine(IsolatedDirectory, CoreAssemblyFileName), hostCorePath, true);
            return hostCorePath;
        }

        /// <summary>Removes the fake deployment.</summary>
        public void Dispose() {
            try {
                if (Directory.Exists(_root))
                    Directory.Delete(_root, recursive: true);
            }
            catch (IOException) {
            }
            catch (UnauthorizedAccessException) {
            }
        }

        /// <summary>
        /// The WebView2 stack and renderer the test project stages next to its
        /// output. They come from the same package and project the deployment
        /// consumes, so running the renderer tests alone does not require the
        /// product deployment to have run first.
        /// </summary>
        internal static string StagedWebView2Directory {
            get {
                return Path.Combine(
                    Path.GetDirectoryName(typeof(IsolatedRendererFixture).Assembly.Location),
                    "webview2-fixture");
            }
        }

        private void Populate() {
            Directory.CreateDirectory(EngineDirectory);
            Directory.CreateDirectory(IsolatedDirectory);
            Directory.CreateDirectory(HostDirectory);

            foreach (var fileName in WebView2AssemblyFileNames)
                CopyRequired(StagedWebView2Directory, fileName, "The staged WebView2 stack is missing.");

            CopyRequired(StagedWebView2Directory, NativeLoaderFileName, "The staged WebView2 stack is missing.");
            CopyRequired(
                StagedWebView2Directory,
                RendererAssemblyFileName,
                "The staged WebView2 renderer is missing.");
        }

        private void CopyRequired(string sourceDirectory, string fileName, string message) {
            var source = Path.Combine(sourceDirectory, fileName);
            if (!File.Exists(source))
                throw new FileNotFoundException(
                    message + " Build the solution before running the renderer tests.", source);

            File.Copy(source, Path.Combine(IsolatedDirectory, fileName), true);
        }
    }
}


