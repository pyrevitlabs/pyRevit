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
using pyRevitLabs.PyRevit.Runtime.Shared;
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
#endif

        /// <summary>
        /// Creates the renderer on <paramref name="dispatcher"/>.
        ///
        /// The window must survive a renderer that cannot be located: the
        /// installation may be half updated, and an exception here would abort
        /// the script that opened the window. Such a window reports a broken
        /// deployment and keeps working as plain text.
        /// </summary>
        internal static IScriptRenderer Create(Dispatcher dispatcher) {
#if !NETFRAMEWORK
            try {
                var context = GetIsolatedContext();
                return CreateIsolated(context, context.AssemblyDirectory, dispatcher);
            }
            catch (Exception ex) when (IsRendererUnavailable(ex)) {
                ScriptRendererLog.Error(
                    "the isolated WebView2 renderer could not be located: {0}: {1}",
                    ex.GetType().Name,
                    ex.Message);
                return new UnavailableScriptRenderer();
            }
#else
            return new WebView2ScriptRenderer(dispatcher, GetProfileFolder());
#endif
        }

#if !NETFRAMEWORK
        /// <summary>
        /// Creates the renderer out of an explicit isolated folder.
        ///
        /// The folder is a parameter so that the isolation contract can be
        /// exercised against a deployed layout outside a Revit host, where
        /// the assembly location of the runtime does not describe the
        /// installation being tested.
        ///
        /// A renderer that cannot be loaded yields a stand-in that reports a
        /// broken deployment. The window and the running script outlive the
        /// renderer, and a half-updated installation is exactly when the
        /// isolated folder and the runtime disagree.
        /// </summary>
        internal static IScriptRenderer CreateIsolated(
            WebView2LoadContext context, string isolatedDirectory, Dispatcher dispatcher) {
            try {
                return LoadIsolatedRenderer(context, isolatedDirectory, dispatcher);
            }
            catch (Exception ex) when (IsRendererUnavailable(ex)) {
                ScriptRendererLog.Error(
                    "the isolated WebView2 renderer in '{0}' could not be loaded: {1}: {2}",
                    isolatedDirectory,
                    ex.GetType().Name,
                    ex.Message);
                return new UnavailableScriptRenderer();
            }
        }

        private static IScriptRenderer LoadIsolatedRenderer(
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
        /// Failures that mean the deployment cannot provide a working renderer,
        /// rather than a defect inside one. Only these degrade to the stand-in;
        /// anything else keeps propagating, because a renderer bug must stay
        /// visible instead of turning into a quiet plain-text window.
        /// </summary>
        private static bool IsRendererUnavailable(Exception exception) {
            if (exception == null)
                return false;

            if (exception is TypeLoadException
                || exception is MissingMethodException
                || exception is MissingFieldException
                || exception is FileNotFoundException
                || exception is DirectoryNotFoundException
                || exception is FileLoadException
                || exception is BadImageFormatException
                || exception is DllNotFoundException
                || exception is EntryPointNotFoundException) {
                return true;
            }

            var invocation = exception as TargetInvocationException;
            if (invocation != null)
                return IsRendererUnavailable(invocation.InnerException);

            var typeInitialization = exception as TypeInitializationException;
            return typeInitialization != null
                   && IsRendererUnavailable(typeInitialization.InnerException);
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
        /// The isolated load context of the process.
        ///
        /// The context is owned by the shared runtime assembly, which every
        /// runtime version binds to the same instance of, so a host process
        /// that loaded several runtime versions still holds one WebView2
        /// context and one copy of the WebView2 stack. It is created on first
        /// use and kept for the lifetime of the process: the WebView2 browser
        /// process and its profile outlive any single output window.
        /// </summary>
        private static WebView2LoadContext GetIsolatedContext() {
            return IsolatedWebView2Context.GetOrCreate(GetIsolatedDirectory());
        }

        private static string GetIsolatedDirectory() {
            return IsolatedRendererLayout.ResolveIsolatedDirectory(GetRuntimeAssemblyDirectory());
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
