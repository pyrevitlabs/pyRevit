#if !NETFRAMEWORK
using System;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Runtime.Loader;

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>
    /// Load context that keeps pyRevit's WebView2 stack out of the host
    /// process default load context.
    ///
    /// Revit 2025 and newer already ship their own Microsoft.Web.WebView2.Core
    /// in the default load context. Letting pyRevit's newer WebView2 assemblies
    /// bind there makes the host bind the newer WPF wrapper against the older
    /// core, which fails at runtime and takes the host down. Loading the whole
    /// WebView2 stack here keeps the two apart.
    ///
    /// Invariant: only the WebView2 assemblies and the renderer implementation
    /// are served from this context. Everything else falls back to the default
    /// context, which is what keeps WPF type identity intact: a private copy
    /// of PresentationFramework would make the renderer control derive from a
    /// different Control type than the host window, and adding it to the visual
    /// tree would throw.
    /// </summary>
    internal sealed class WebView2LoadContext : AssemblyLoadContext {
        private static readonly string[] IsolatedAssemblyNames = {
            "Microsoft.Web.WebView2.Core",
            "Microsoft.Web.WebView2.Wpf",
            "Microsoft.Web.WebView2.WinForms",
            "pyRevitLabs.PyRevit.WebView2",
        };

        private readonly string _assemblyDirectory;

        public WebView2LoadContext(string assemblyDirectory)
            : base("pyRevit.WebView2", isCollectible: false) {
            _assemblyDirectory = assemblyDirectory;
        }

        public string AssemblyDirectory {
            get { return _assemblyDirectory; }
        }

        protected override Assembly Load(AssemblyName assemblyName) {
            if (!IsIsolatedAssembly(assemblyName == null ? null : assemblyName.Name))
                return null;

            var path = Path.Combine(_assemblyDirectory, assemblyName.Name + ".dll");
            if (!File.Exists(path))
                return null;

            return LoadFromAssemblyPath(path);
        }

        /// <summary>
        /// The native WebView2 loader sits next to the managed assemblies. The
        /// default native probing does not know about this folder, so without
        /// this override the core fails with a DllNotFoundException.
        /// </summary>
        protected override IntPtr LoadUnmanagedDll(string unmanagedDllName) {
            var path = Path.Combine(_assemblyDirectory, unmanagedDllName);
            if (!File.Exists(path)) {
                path = Path.Combine(
                    _assemblyDirectory,
                    Path.GetFileNameWithoutExtension(unmanagedDllName) + ".dll");
                if (!File.Exists(path))
                    return IntPtr.Zero;
            }

            return LoadUnmanagedDllFromPath(path);
        }

        private static bool IsIsolatedAssembly(string assemblyName) {
            if (string.IsNullOrEmpty(assemblyName))
                return false;

            foreach (var isolated in IsolatedAssemblyNames) {
                if (string.Equals(isolated, assemblyName, StringComparison.OrdinalIgnoreCase))
                    return true;
            }

            return false;
        }
    }
}
#endif
