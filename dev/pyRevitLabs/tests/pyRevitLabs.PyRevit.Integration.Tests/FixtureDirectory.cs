using System.IO;

namespace pyRevitLabs.PyRevit.Integration.Tests {
    internal static class FixtureDirectory {
        internal static void Delete(string path) {
            if (!Directory.Exists(path))
                return;

            foreach (var file in Directory.EnumerateFiles(path, "*", SearchOption.AllDirectories))
                File.SetAttributes(file, FileAttributes.Normal);

            Directory.Delete(path, recursive: true);
        }
    }
}
