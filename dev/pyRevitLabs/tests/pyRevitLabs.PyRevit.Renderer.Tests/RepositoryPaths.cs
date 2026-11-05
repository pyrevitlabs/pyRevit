using System;
using System.IO;

namespace PyRevitLabs.PyRevit.Renderer.Tests {
    /// <summary>
    /// Locates the repository root from the test output folder, the same way
    /// the build pipeline does, so that the tests can reach the checked-in
    /// binaries and the build output without hard-coding a checkout path.
    /// </summary>
    internal static class RepositoryPaths {
        private const string RootMarkerFileName = "pyRevitfile";

        private static readonly Lazy<string> RootPath = new Lazy<string>(FindRoot);

        /// <summary>The repository root folder.</summary>
        internal static string Root {
            get { return RootPath.Value; }
        }

        private static string FindRoot() {
            var directory = new DirectoryInfo(AppContext.BaseDirectory);
            while (directory != null) {
                if (File.Exists(Path.Combine(directory.FullName, RootMarkerFileName)))
                    return directory.FullName;

                directory = directory.Parent;
            }

            throw new DirectoryNotFoundException(
                "Could not locate the repository root from the test output folder '"
                + AppContext.BaseDirectory + "'.");
        }
    }
}
