#if !NETFRAMEWORK
using System;
using System.IO;

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>
    /// Locates the folders of a pyRevit installation from the location of the
    /// runtime assembly.
    ///
    /// The runtime assembly is deployed to an engine folder below the binary
    /// folder, and the isolated renderer folder sits next to the engines, so
    /// the search walks up until it finds the folder that holds them.
    ///
    /// Invariant: the isolated folder name is part of the deployment
    /// contract. The loader keeps the WebView2 stack out of the binary
    /// folder on .NET, and the renderer loads it from the isolated folder by
    /// path.
    /// </summary>
    internal static class IsolatedRendererLayout {
        internal const string EnginesFolderName = "engines";
        internal const string IsolatedFolderName = "isolated";

        /// <summary>
        /// The binary folder of the installation, the one that holds the
        /// engine folders.
        /// </summary>
        /// <param name="assemblyDirectory">The folder the runtime assembly sits in.</param>
        internal static string ResolveBinDirectory(string assemblyDirectory) {
            var directory = assemblyDirectory;
            while (!string.IsNullOrEmpty(directory)) {
                if (Directory.Exists(Path.Combine(directory, EnginesFolderName)))
                    return directory;

                var parent = Path.GetDirectoryName(directory);
                if (string.Equals(parent, directory, StringComparison.OrdinalIgnoreCase))
                    break;
                directory = parent;
            }

            var fallback = Path.GetDirectoryName(Path.GetDirectoryName(assemblyDirectory));
            if (string.IsNullOrEmpty(fallback)) {
                throw new DirectoryNotFoundException(
                    "Could not locate the pyRevit binary folder from the runtime assembly location.");
            }

            return fallback;
        }

        /// <summary>
        /// The folder the isolated WebView2 stack is deployed to.
        /// </summary>
        /// <param name="assemblyDirectory">The folder the runtime assembly sits in.</param>
        internal static string ResolveIsolatedDirectory(string assemblyDirectory) {
            return Path.Combine(ResolveBinDirectory(assemblyDirectory), IsolatedFolderName);
        }
    }
}
#endif
