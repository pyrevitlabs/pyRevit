using System;
using System.Diagnostics;
using System.IO;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using PyRevitLabs.PyRevit.Runtime.Agent;
using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Integration")]
    public sealed class AgentExportFolderTests : IDisposable {
        private readonly string root;
        private readonly string exports;
        private readonly string outside;

        public AgentExportFolderTests() {
            root = Path.Combine(Path.GetTempPath(), "agent-export-" + Guid.NewGuid().ToString("N"));
            exports = Path.Combine(root, "run", "exports");
            outside = Path.Combine(root, "outside");
            Directory.CreateDirectory(exports);
            Directory.CreateDirectory(outside);
        }

        public void Dispose() {
            foreach (var link in Directory.GetDirectories(exports))
                if (new DirectoryInfo(link).Attributes.HasFlag(FileAttributes.ReparsePoint))
                    Directory.Delete(link);
            var run = Path.Combine(root, "run");
            if (Directory.Exists(run) && new DirectoryInfo(run).Attributes.HasFlag(FileAttributes.ReparsePoint))
                Directory.Delete(run);
            Directory.Delete(root, recursive: true);
        }

        [Theory]
        [InlineData("")]
        [InlineData("sheet.png")]
        [InlineData("exports\\sheet.png")]
        public void TargetsInsideTheFolderAreAllowed(string relative) {
            var folder = new AgentExportFolder(exports);

            Assert.True(folder.Contains(Path.Combine(exports, relative)));
        }

        [Fact]
        public void APrefixInsideTheFolderIsAllowedLikeExportImageUsesIt() {
            var folder = new AgentExportFolder(exports);

            Assert.True(folder.Contains(Path.Combine(exports, "A101")));
            Assert.True(folder.Contains(exports + "\\"));
            Assert.True(folder.Contains(exports.Replace('\\', '/') + "/sheet.png"));
        }

        [Fact]
        public void TargetsOutsideTheFolderAreRefused() {
            var folder = new AgentExportFolder(exports);

            Assert.False(folder.Contains(Path.Combine(outside, "sheet.png")));
            Assert.False(folder.Contains(Path.Combine(exports, "..", "sheet.png")));
            Assert.False(folder.Contains(Path.Combine(exports, "..", "..", "outside", "sheet.png")));
            Assert.False(folder.Contains(exports + "-sibling\\sheet.png"));
            Assert.False(folder.Contains(Path.GetDirectoryName(exports)));
        }

        [Theory]
        [InlineData(null)]
        [InlineData("")]
        [InlineData("   ")]
        [InlineData("sheet.png")]
        [InlineData(".\\sheet.png")]
        [InlineData("..\\sheet.png")]
        public void TargetsThatAreNotFullyQualifiedAreRefused(string target) {
            var folder = new AgentExportFolder(exports);

            Assert.False(folder.Contains(target));
        }

        [Fact]
        public void DriveRelativeUncAndDevicePathsAreRefused() {
            var folder = new AgentExportFolder(exports);
            var drive = exports.Substring(0, 2);
            var unc = "\\\\localhost\\" + exports[0] + "$" + exports.Substring(2);

            Assert.False(folder.Contains(drive + "sheet.png"));
            Assert.False(folder.Contains(Path.Combine(unc, "sheet.png")));
            Assert.False(folder.Contains("\\\\?\\" + Path.Combine(exports, "sheet.png")));
            Assert.False(folder.Contains("\\\\.\\" + Path.Combine(exports, "sheet.png")));
        }

        [Fact]
        public void AFolderOnAShareAcceptsTargetsThroughThatShareOnly() {
            var share = AdminShare(exports);
            if (!Directory.Exists(share))
                return;
            var folder = new AgentExportFolder(share);

            Assert.True(folder.Contains(Path.Combine(share, "sheet.png")));
            Assert.False(folder.Contains(Path.Combine(AdminShare(outside), "sheet.png")));
            Assert.False(folder.Contains(Path.Combine(share, "..", "sheet.png")));
        }

        [Fact]
        public void AJunctionInsideTheFolderThatPointsOutsideIsRefused() {
            var folder = new AgentExportFolder(exports);
            var link = Path.Combine(exports, "link");
            CreateJunction(link, outside);

            Assert.False(folder.Contains(Path.Combine(link, "sheet.png")));
            Assert.False(folder.Contains(link));
        }

        [Fact]
        public void ReplacingTheFolderWithAJunctionAfterItWasResolvedIsRefused() {
            var folder = new AgentExportFolder(exports);
            var run = Path.Combine(root, "run");
            Directory.Delete(run, recursive: true);
            Directory.CreateDirectory(Path.Combine(outside, "exports"));
            CreateJunction(run, outside);

            Assert.True(Directory.Exists(exports));
            Assert.False(folder.Contains(Path.Combine(exports, "sheet.png")));
        }

        [Fact]
        public void ShortNamesResolveToTheEntryTheyAlias() {
            var folder = new AgentExportFolder(exports);
            var inside = Path.Combine(exports, "sheet-with-a-long-name.png");
            var other = Path.Combine(outside, "sheet-with-a-long-name.png");
            File.WriteAllText(inside, "");
            File.WriteAllText(other, "");

            Assert.True(folder.Contains(ShortName(inside)));
            Assert.False(folder.Contains(ShortName(other)));
        }

        [Fact]
        public void TheScriptFacingFolderEndsWithExactlyOneSeparator() {
            var exportDir = Directory.CreateDirectory(Path.Combine(Path.GetDirectoryName(exports), "exports")).FullName;
            var forScripts = exportDir + Path.DirectorySeparatorChar;

            Assert.Equal(exports + Path.DirectorySeparatorChar, forScripts);
        }

        [Fact]
        public void TheScriptFacingFolderAndItsPrefixesAreAllowedByAGuardOnThePlainFolder() {
            var app = new UIApplication();
            var forScripts = exports + Path.DirectorySeparatorChar;
            using (var guard = new AgentRunGuard(app, new Document(), exports)) {
                guard.Arm("Test");

                Assert.True(app.Application.ExportFile(forScripts));
                Assert.True(app.Application.ExportFile(Path.Combine(forScripts, "sheet")));
                Assert.True(app.Application.ExportFile(forScripts + "sheet"));
                Assert.Empty(guard.Blocked);
            }
        }

        [Fact]
        public void AFolderThatDoesNotExistRefusesEverything() {
            var folder = new AgentExportFolder(Path.Combine(root, "missing"));

            Assert.False(folder.Contains(Path.Combine(root, "missing", "sheet.png")));
        }

        [Fact]
        public void TheGuardAllowsExportsIntoTheFolderAndBlocksOthersWithTheirPath() {
            var app = new UIApplication();
            var document = new Document();
            using (var guard = new AgentRunGuard(app, document, exports)) {
                guard.Arm("Test");

                Assert.True(app.Application.ExportFile(Path.Combine(exports, "sheet.png")));
                Assert.True(app.Application.ExportFile(exports));
                var elsewhere = Path.Combine(outside, "sheet.png");
                Assert.False(app.Application.ExportFile(elsewhere));

                var blocked = Assert.Single(guard.Blocked);
                Assert.Equal("file_export", blocked.Value<string>("operation"));
                Assert.Equal(elsewhere, blocked.Value<string>("path"));
                Assert.Equal(
                    $"operation_blocked: file_export to '{elsewhere}' not allowed in agent runs. "
                    + "Revit exports may only write into the run's export_dir.",
                    guard.DescribeBlockedOperations());
            }
        }

        [Fact]
        public void ABackgroundExportIsBlockedEvenIntoTheFolder() {
            var app = new UIApplication();
            using (var guard = new AgentRunGuard(app, new Document(), exports)) {
                guard.Arm("Test");

                Assert.False(app.Application.ExportFile(exports, background: true));
                Assert.True(app.Application.ExportFile(exports));

                var blocked = Assert.Single(guard.Blocked);
                Assert.Equal("background_export", blocked.Value<string>("operation"));
                Assert.Equal(exports, blocked.Value<string>("path"));
                Assert.Null(blocked["outside_export_dir"]);
                Assert.Equal(
                    $"operation_blocked: background_export to '{exports}' not allowed in agent runs. "
                    + "Background exports finish after the run, so export without SetExportInBackground.",
                    guard.DescribeBlockedOperations());
            }
        }

        [Fact]
        public void ABackgroundExportOutsideTheFolderNamesBothFixesInOneEntry() {
            var app = new UIApplication();
            var elsewhere = Path.Combine(outside, "sheet.pdf");
            using (var guard = new AgentRunGuard(app, new Document(), exports)) {
                guard.Arm("Test");

                Assert.False(app.Application.ExportFile(elsewhere, background: true));

                var blocked = Assert.Single(guard.Blocked);
                Assert.Equal("background_export", blocked.Value<string>("operation"));
                Assert.Equal(elsewhere, blocked.Value<string>("path"));
                Assert.True(blocked.Value<bool>("outside_export_dir"));
                Assert.Equal(
                    $"operation_blocked: background_export to '{elsewhere}' not allowed in agent runs. "
                    + "Revit exports may only write into the run's export_dir. "
                    + "Background exports finish after the run, so export without SetExportInBackground.",
                    guard.DescribeBlockedOperations());
            }
        }

        [Fact]
        public void WithoutAFolderEveryExportIsBlocked() {
            var app = new UIApplication();
            using (var guard = new AgentRunGuard(app, new Document())) {
                guard.Arm("Test");

                Assert.False(app.Application.ExportFile(Path.Combine(exports, "sheet.png")));
                Assert.Single(guard.Blocked);
            }
        }

        private static string AdminShare(string path) {
            return "\\\\localhost\\" + path[0] + "$" + path.Substring(2);
        }

        private static string ShortName(string path) {
            var buffer = new System.Text.StringBuilder(1024);
            var length = GetShortPathName(path, buffer, buffer.Capacity);
            Assert.True(length > 0 && length < buffer.Capacity);
            return buffer.ToString();
        }

        [System.Runtime.InteropServices.DllImport("kernel32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode, SetLastError = true)]
        private static extern int GetShortPathName(string longPath, System.Text.StringBuilder shortPath, int bufferLength);

        private static void CreateJunction(string link, string target) {
            var start = new ProcessStartInfo("cmd.exe", $"/c mklink /J \"{link}\" \"{target}\"") {
                CreateNoWindow = true,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
            };
            using (var process = Process.Start(start)) {
                process.WaitForExit();
                Assert.True(process.ExitCode == 0, process.StandardError.ReadToEnd());
            }
        }
    }
}
