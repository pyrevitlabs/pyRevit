using System;
using System.IO;
using System.Reflection;
using System.Text.RegularExpressions;
using System.Windows.Threading;
using PyRevitLabs.PyRevit.Renderer;
#if NETFRAMEWORK
using PyRevitLabs.PyRevit.WebView2;
#else
using System.Runtime.Loader;
#endif

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>
    /// Creates the renderer behind a script output window.
    ///
    /// On Revit 2021 to 2024 the renderer runs in the host process default
    /// load context, which is the only option on the .NET Framework. On Revit
    /// 2025 and newer the renderer is loaded into a dedicated load context so
    /// that the WebView2 stack pyRevit ships never binds against the one the
    /// host process already loaded.
    /// </summary>
    internal static class ScriptRendererProvider {
#if !NETFRAMEWORK
        private const string IsolatedRendererAssemblyFileName = "pyRevitLabs.PyRevit.WebView2.dll";
        private const string IsolatedRendererTypeName =
            "PyRevitLabs.PyRevit.WebView2.WebView2ScriptRenderer";

        private static readonly object IsolatedContextLock = new object();
        private static WebView2LoadContext _isolatedContext;
#endif

        /// <summary>
        /// Creates the renderer on <paramref name="dispatcher"/>.
        /// </summary>
        internal static IScriptRenderer Create(Dispatcher dispatcher) {
#if !NETFRAMEWORK
            return CreateIsolated(dispatcher);
#else
            return new WebView2ScriptRenderer(dispatcher, GetProfileFolder());
#endif
        }

#if !NETFRAMEWORK
        /// <summary>
        /// Loads the renderer implementation into the isolated load context and
        /// hands back the contract view of it.
        ///
        /// The implementation is reached by reflection on purpose: a metadata
        /// reference would let the default load context demand-load it, which
        /// is exactly the binding this isolation exists to prevent.
        /// </summary>
        private static IScriptRenderer CreateIsolated(Dispatcher dispatcher) {
            var context = GetIsolatedContext();
            return CreateIsolated(context, context.AssemblyDirectory, dispatcher);
        }

        /// <summary>
        /// Creates the renderer out of an explicit isolated folder.
        ///
        /// The folder is a parameter so that the isolation contract can be
        /// exercised against a deployed layout outside a Revit host, where
        /// the assembly location of the runtime does not describe the
        /// installation being tested.
        /// </summary>
        internal static IScriptRenderer CreateIsolated(
            WebView2LoadContext context, string isolatedDirectory, Dispatcher dispatcher) {
            var assemblyPath = Path.Combine(
                isolatedDirectory, IsolatedRendererAssemblyFileName);
            if (!File.Exists(assemblyPath)) {
                throw new FileNotFoundException(
                    "The isolated WebView2 renderer assembly was not found. "
                    + "The pyRevit installation is incomplete.",
                    assemblyPath);
            }

            var assembly = context.LoadFromAssemblyPath(assemblyPath);
            var rendererType = assembly.GetType(IsolatedRendererTypeName, throwOnError: true);
            var renderer = (IScriptRenderer)Activator.CreateInstance(
                rendererType,
                BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic,
                null,
                new object[] { dispatcher, GetProfileFolder() },
                null);
            LogLoadContexts(context, assembly);
            return renderer;
        }

        /// <summary>
        /// Records the load context of the renderer and of the WebView2
        /// assemblies it pulled in, so that the isolation from the host process
        /// is observable in the runtime log.
        /// </summary>
        private static void LogLoadContexts(WebView2LoadContext context, Assembly rendererAssembly) {
            ScriptRendererLog.Debug(
                "renderer assembly {0}{1}",
                rendererAssembly.GetName().Name,
                DescribeLoadContext(rendererAssembly));

            foreach (var assembly in context.Assemblies) {
                var name = assembly.GetName().Name;
                if (name == null || !name.StartsWith("Microsoft.Web.WebView2", StringComparison.OrdinalIgnoreCase))
                    continue;

                ScriptRendererLog.Debug(
                    "renderer dependency {0}{1}", name, DescribeLoadContext(assembly));
            }
        }

        private static string DescribeLoadContext(Assembly assembly) {
            var context = AssemblyLoadContext.GetLoadContext(assembly);
            return context == null
                ? string.Empty
                : string.Format(" loaded into load context '{0}'", context.Name);
        }

        /// <summary>
        /// The isolated load context, created on first use and kept for the
        /// lifetime of the process: the WebView2 browser process and its
        /// profile outlive any single output window.
        /// </summary>
        private static WebView2LoadContext GetIsolatedContext() {
            lock (IsolatedContextLock) {
                if (_isolatedContext == null)
                    _isolatedContext = new WebView2LoadContext(GetIsolatedDirectory());
                return _isolatedContext;
            }
        }

        private static string GetIsolatedDirectory() {
            return IsolatedRendererLayout.ResolveIsolatedDirectory(GetRuntimeAssemblyDirectory());
        }

        /// <summary>
        /// The folder the host process binaries live in, which is where the
        /// isolated renderer folder sits. The runtime assembly is deployed to
        /// an engine folder below it, so the search walks up until it finds
        /// the engine folder marker.
        /// </summary>
        private static string GetPyRevitBinDirectory() {
            return IsolatedRendererLayout.ResolveBinDirectory(GetRuntimeAssemblyDirectory());
        }

        private static string GetRuntimeAssemblyDirectory() {
            return Path.GetDirectoryName(typeof(ScriptRendererProvider).Assembly.Location);
        }
#endif

        /// <summary>
        /// Name of the browser profile folder for this host. Every Revit
        /// version gets its own, because sharing one folder makes hosts that
        /// run side by side connect to whichever browser process won the race.
        /// </summary>
        private static string GetProfileFolder() {
            try {
                var match = Regex.Match(
                    Path.GetFileNameWithoutExtension(typeof(ScriptRendererProvider).Assembly.Location),
                    @"(\d{4})$");
                if (match.Success)
                    return match.Groups[1].Value;
            }
            catch {
            }

            return "shared";
        }
    }
}
