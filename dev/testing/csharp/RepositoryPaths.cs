using System;
using System.IO;

namespace pyRevit.Tests.TestSupport {
    internal static class RepositoryPaths {
        internal static string Root {
            get {
                var directory = new DirectoryInfo(AppContext.BaseDirectory);
                while (directory != null) {
                    if (File.Exists(Path.Combine(directory.FullName, "pyRevitfile")))
                        return directory.FullName;
                    directory = directory.Parent;
                }
                throw new DirectoryNotFoundException("Cannot locate the pyRevit repository root.");
            }
        }
    }
}
