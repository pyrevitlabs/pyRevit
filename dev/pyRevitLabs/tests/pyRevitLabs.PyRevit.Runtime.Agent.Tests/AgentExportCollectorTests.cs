using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using PyRevitLabs.PyRevit.Runtime.Agent;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Integration")]
    public sealed class AgentExportCollectorTests : IDisposable {
        private readonly string root;
        private readonly string exports;
        private readonly string outside;

        public AgentExportCollectorTests() {
            root = Path.Combine(Path.GetTempPath(), "agent-collect-" + Guid.NewGuid().ToString("N"));
            exports = Path.Combine(root, "exports");
            outside = Path.Combine(root, "outside");
            Directory.CreateDirectory(exports);
            Directory.CreateDirectory(outside);
        }

        public void Dispose() {
            var link = Path.Combine(exports, "link");
            if (Directory.Exists(link) && new DirectoryInfo(link).Attributes.HasFlag(FileAttributes.ReparsePoint))
                Directory.Delete(link);
            Directory.Delete(root, recursive: true);
        }

        [Fact]
        public void FilesInTheFolderAndItsSubfoldersAreListedInOrder() {
            var nested = Path.Combine(exports, "pdf");
            Directory.CreateDirectory(nested);
            var sheet = Write(Path.Combine(exports, "B.png"));
            var first = Write(Path.Combine(exports, "a.png"));
            var pdf = Write(Path.Combine(nested, "A101.pdf"));
            var last = Write(Path.Combine(exports, "z.png"));

            var files = AgentExportCollector.Collect(exports);

            Assert.Equal(new[] { first, sheet, pdf, last }, files);
            Assert.True(Directory.Exists(exports));
        }

        [Fact]
        public void FilesBehindALinkAreNotListed() {
            Write(Path.Combine(outside, "secret.txt"));
            var sheet = Write(Path.Combine(exports, "sheet.png"));
            Assert.True(TryCreateJunction(Path.Combine(exports, "link"), outside, out var error),
                "Creating a directory junction with 'mklink /J' failed, so link skipping can't be checked here: " + error);

            var files = AgentExportCollector.Collect(exports);

            Assert.Equal(new[] { sheet }, files);
        }

        [Fact]
        public void AnEmptyFolderIsRemoved() {
            var files = AgentExportCollector.Collect(exports);

            Assert.Empty(files);
            Assert.False(Directory.Exists(exports));
        }

        [Fact]
        public void AFolderThatHoldsAFileIsKept() {
            var sheet = Write(Path.Combine(exports, "sheet.png"));

            var files = AgentExportCollector.Collect(exports);

            Assert.Equal(new[] { sheet }, files);
            Assert.True(File.Exists(sheet));
        }

        [Fact]
        public void AFolderWithOnlyAnEmptySubfolderIsKept() {
            Directory.CreateDirectory(Path.Combine(exports, "pdf"));

            var files = AgentExportCollector.Collect(exports);

            Assert.Empty(files);
            Assert.True(Directory.Exists(exports));
        }

        [Fact]
        public void AMissingFolderYieldsNoFiles() {
            var missing = Path.Combine(root, "missing");

            var files = AgentExportCollector.Collect(missing);

            Assert.Empty(files);
            Assert.False(Directory.Exists(missing));
        }

        [Fact]
        public void EveryExportedFileIsListedWithoutACap() {
            var written = Enumerable.Range(0, 25)
                .Select(index => Write(Path.Combine(exports, $"sheet-{index:D2}.png")))
                .ToArray();

            var files = AgentExportCollector.Collect(exports);

            Assert.Equal(written, files);
        }

        private static string Write(string path) {
            File.WriteAllText(path, "");
            return path;
        }

        private static bool TryCreateJunction(string link, string target, out string error) {
            var start = new ProcessStartInfo("cmd.exe", $"/c mklink /J \"{link}\" \"{target}\"") {
                CreateNoWindow = true,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
            };
            using (var process = Process.Start(start)) {
                error = process.StandardError.ReadToEnd();
                process.WaitForExit();
                return process.ExitCode == 0;
            }
        }
    }
}
