using System;
using System.Diagnostics;
using System.IO;
using NUnit.Framework;
using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;

namespace pyRevitExtensionParserTest
{
    /// <summary>Regression coverage for #3940 directory-linked extension cache keys.</summary>
    [TestFixture]
    [Category("HostFree")]
    [Category("Integration")]
    [Category("Regression")]
    public class ParsedExtensionHashTests : TempFileTestBase
    {
        /// <summary>Changing a command inside a linked extension changes its generated cache key.</summary>
        [Test]
        public void GetHash_DirectoryLinkedExtension_ChangesWhenACommandIsAdded()
        {
            var targetExtension = CreateExtension("Target.extension");
            var linkedExtension = CreateDirectoryJunction("Linked.extension", targetExtension);

            var before = GetHash(linkedExtension);
            AddCommand(targetExtension, "Added.pushbutton", DateTime.UtcNow.AddMinutes(1));
            var after = GetHash(linkedExtension);

            Assert.That(after, Is.Not.EqualTo(before));
        }

        /// <summary>Linked directories below an extension root remain excluded from hash traversal.</summary>
        [Test]
        public void GetHash_DoesNotFollowLinkedDescendantDirectories()
        {
            var extension = CreateExtension("Root.extension");
            var externalCommand = CreateExtension("External.extension");
            var linkedCommand = Path.Combine(
                extension,
                "Root.tab",
                "Root.panel",
                "Linked.pushbutton");
            CreateDirectoryJunction(linkedCommand, externalCommand);

            var before = GetHash(extension);
            AddCommand(externalCommand, "Changed.pushbutton", DateTime.UtcNow.AddMinutes(1));
            var after = GetHash(extension);

            Assert.That(after, Is.EqualTo(before));
        }

        private string CreateExtension(string directoryName)
        {
            var extension = CreateSubDirectory(directoryName);
            AddCommand(extension, "Initial.pushbutton", DateTime.UtcNow.AddMinutes(-1));
            return extension;
        }

        private static string GetHash(string extensionDirectory)
        {
            return new ParsedExtension { Directory = extensionDirectory }.GetHash("Roslyn");
        }

        private static void AddCommand(string extensionDirectory, string commandName, DateTime timestamp)
        {
            var commandDirectory = Path.Combine(
                extensionDirectory,
                "Root.tab",
                "Root.panel",
                commandName);
            Directory.CreateDirectory(commandDirectory);

            var scriptPath = Path.Combine(commandDirectory, "script.py");
            File.WriteAllText(scriptPath, "print('test')");
            File.SetLastWriteTimeUtc(scriptPath, timestamp);
            Directory.SetLastWriteTimeUtc(commandDirectory, timestamp);
        }

        private string CreateDirectoryJunction(string linkName, string targetDirectory)
        {
            if (Environment.OSVersion.Platform != PlatformID.Win32NT)
                Assert.Ignore("Directory junctions are a Windows-only fixture.");

            var linkDirectory = Path.Combine(TestTempDir, linkName);
            using var process = Process.Start(new ProcessStartInfo
            {
                FileName = "cmd.exe",
                Arguments = $"/c mklink /J \"{linkDirectory}\" \"{targetDirectory}\"",
                CreateNoWindow = true,
                UseShellExecute = false,
                RedirectStandardError = true,
            }) ?? throw new InvalidOperationException("Could not start cmd.exe to create a directory junction.");
            process.WaitForExit();

            Assert.That(
                process.ExitCode,
                Is.EqualTo(0),
                $"Could not create directory junction: {process.StandardError.ReadToEnd()}");
            return linkDirectory;
        }
    }
}