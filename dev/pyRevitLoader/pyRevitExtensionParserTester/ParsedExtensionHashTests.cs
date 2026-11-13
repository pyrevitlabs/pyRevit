using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
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
        private readonly List<string> _junctionDirectories = new();

        /// <summary>Removes junctions before the temporary fixture directory is deleted.</summary>
        [TearDown]
        public void RemoveDirectoryJunctions()
        {
            foreach (var junctionDirectory in _junctionDirectories)
            {
                if (Directory.Exists(junctionDirectory))
                    Directory.Delete(junctionDirectory, false);
            }
        }

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

        /// <summary>Renaming a command in a linked extension changes the cache key even when timestamps are restored.</summary>
        [Test]
        public void GetHash_DirectoryLinkedExtension_ChangesWhenACommandIsRenamedWithPreservedTimestamps()
        {
            var targetExtension = CreateExtension("Target.extension");
            var linkedExtension = CreateDirectoryJunction("Linked.extension", targetExtension);
            var tabDirectory = Path.Combine(targetExtension, "Root.tab");
            var panelDirectory = Path.Combine(tabDirectory, "Root.panel");
            var initialCommand = GetCommandDirectory(targetExtension, "Initial.pushbutton");
            var renamedCommand = GetCommandDirectory(targetExtension, "Renamed.pushbutton");
            var scriptPath = Path.Combine(initialCommand, "script.py");
            var tabTimestamp = Directory.GetLastWriteTimeUtc(tabDirectory);
            var panelTimestamp = Directory.GetLastWriteTimeUtc(panelDirectory);
            var commandTimestamp = Directory.GetLastWriteTimeUtc(initialCommand);
            var scriptTimestamp = File.GetLastWriteTimeUtc(scriptPath);

            var before = GetHash(linkedExtension);
            Directory.Move(initialCommand, renamedCommand);
            File.SetLastWriteTimeUtc(Path.Combine(renamedCommand, "script.py"), scriptTimestamp);
            Directory.SetLastWriteTimeUtc(renamedCommand, commandTimestamp);
            Directory.SetLastWriteTimeUtc(panelDirectory, panelTimestamp);
            Directory.SetLastWriteTimeUtc(tabDirectory, tabTimestamp);
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

        /// <summary>Editing a file in a bundle type that generates commands changes the cache key.</summary>
        [TestCase("Open.urlbutton", "bundle.yaml")]
        [TestCase("Invoke.invokebutton", "bundle.yaml")]
        [TestCase("Open.nobutton", "script.py")]
        public void GetHash_ChangesWhenAFileInsideABundleIsEdited(string bundleName, string fileName)
        {
            var extension = CreateExtension("Root.extension");
            var bundleDirectory = Path.Combine(extension, "Root.tab", "Root.panel", bundleName);
            var editedFile = AddFile(bundleDirectory, fileName, DateTime.UtcNow.AddMinutes(-1));

            var before = GetHash(extension);
            File.SetLastWriteTimeUtc(editedFile, DateTime.UtcNow.AddMinutes(1));
            var after = GetHash(extension);

            Assert.That(after, Is.Not.EqualTo(before));
        }

        /// <summary>Editing a family file inside a content bundle changes the cache key.</summary>
        [Test]
        public void GetHash_ChangesWhenAFamilyFileInsideAContentBundleIsEdited()
        {
            var extension = CreateExtension("Root.extension");
            var bundleDirectory = Path.Combine(extension, "Root.tab", "Root.panel", "Family.content");
            var editedFile = AddFile(bundleDirectory, "content.rfa", DateTime.UtcNow.AddMinutes(-1));

            var before = GetHash(extension);
            File.SetLastWriteTimeUtc(editedFile, DateTime.UtcNow.AddMinutes(1));
            var after = GetHash(extension);

            Assert.That(after, Is.Not.EqualTo(before));
        }

        /// <summary>Every bundle suffix the parser recognizes is walked by the cache key.</summary>
        [Test]
        public void GetHash_ChangesWhenAFileInsideAnyRecognizedBundleTypeIsEdited()
        {
            var suffixes = Enum.GetValues(typeof(ExtensionParser.CommandComponentType))
                .Cast<ExtensionParser.CommandComponentType>()
                .Select(type => type.ToExtension())
                .Where(suffix => suffix.Length > 0)
                .ToList();
            Assert.That(suffixes, Is.Not.Empty);

            foreach (var suffix in suffixes)
            {
                var extension = CreateExtension("Root" + suffix.Replace('.', '_') + ".extension");
                var bundleDirectory = Path.Combine(extension, "Root.tab", "Root.panel", "Probe" + suffix);
                var editedFile = AddFile(bundleDirectory, "script.py", DateTime.UtcNow.AddMinutes(-1));

                var before = GetHash(extension);
                File.SetLastWriteTimeUtc(editedFile, DateTime.UtcNow.AddMinutes(1));
                var after = GetHash(extension);

                Assert.That(after, Is.Not.EqualTo(before), $"Bundle suffix {suffix} is not hashed.");
            }
        }

        /// <summary>Editing a file in the extension checks folder changes the cache key.</summary>
        [Test]
        public void GetHash_ChangesWhenAFileInsideChecksIsEdited()
        {
            var extension = CreateExtension("Root.extension");
            var editedFile = AddFile(Path.Combine(extension, "checks"), "check.py", DateTime.UtcNow.AddMinutes(-1));

            var before = GetHash(extension);
            File.SetLastWriteTimeUtc(editedFile, DateTime.UtcNow.AddMinutes(1));
            var after = GetHash(extension);

            Assert.That(after, Is.Not.EqualTo(before));
        }

        /// <summary>Editing a file directly in the extension root changes the cache key.</summary>
        [TestCase("extension.json")]
        [TestCase("startup.py")]
        public void GetHash_ChangesWhenAFileInTheExtensionRootIsEdited(string fileName)
        {
            var extension = CreateExtension("Root.extension");
            var editedFile = AddFile(extension, fileName, DateTime.UtcNow.AddMinutes(-1));
            Directory.SetLastWriteTimeUtc(extension, DateTime.UtcNow.AddMinutes(-1));

            var before = GetHash(extension);
            File.SetLastWriteTimeUtc(editedFile, DateTime.UtcNow.AddMinutes(1));
            var after = GetHash(extension);

            Assert.That(after, Is.Not.EqualTo(before));
        }

        /// <summary>Files in unrelated folders do not change the cache key.</summary>
        [Test]
        public void GetHash_IgnoresFilesInUnlistedDirectories()
        {
            var extension = CreateExtension("Root.extension");
            var editedFile = AddFile(Path.Combine(extension, "docs"), "notes.py", DateTime.UtcNow.AddMinutes(-1));

            var before = GetHash(extension);
            File.SetLastWriteTimeUtc(editedFile, DateTime.UtcNow.AddMinutes(1));
            var after = GetHash(extension);

            Assert.That(after, Is.EqualTo(before));
        }

        /// <summary>Writes a file with a deterministic timestamp, creating its directory.</summary>
        private static string AddFile(string directory, string fileName, DateTime timestamp)
        {
            Directory.CreateDirectory(directory);
            Directory.SetLastWriteTimeUtc(directory, timestamp);
            var path = Path.Combine(directory, fileName);
            File.WriteAllText(path, "{}");
            File.SetLastWriteTimeUtc(path, timestamp);
            Directory.SetLastWriteTimeUtc(directory, timestamp);
            return path;
        }

        /// <summary>Creates an extension fixture containing one command bundle.</summary>
        private string CreateExtension(string directoryName)
        {
            var extension = CreateSubDirectory(directoryName);
            AddCommand(extension, "Initial.pushbutton", DateTime.UtcNow.AddMinutes(-1));
            return extension;
        }

        /// <summary>Calculates the Roslyn cache key for an extension fixture.</summary>
        private static string GetHash(string extensionDirectory)
        {
            return new ParsedExtension { Directory = extensionDirectory }.GetHash("Roslyn");
        }

        /// <summary>Adds a command bundle with a script file and deterministic timestamps.</summary>
        private static void AddCommand(string extensionDirectory, string commandName, DateTime timestamp)
        {
            var commandDirectory = GetCommandDirectory(extensionDirectory, commandName);
            Directory.CreateDirectory(commandDirectory);

            var scriptPath = Path.Combine(commandDirectory, "script.py");
            File.WriteAllText(scriptPath, "print('test')");
            File.SetLastWriteTimeUtc(scriptPath, timestamp);
            Directory.SetLastWriteTimeUtc(commandDirectory, timestamp);
        }

        /// <summary>Returns the fixture path for a command bundle.</summary>
        private static string GetCommandDirectory(string extensionDirectory, string commandName)
        {
            return Path.Combine(
                extensionDirectory,
                "Root.tab",
                "Root.panel",
                commandName);
        }

        /// <summary>Creates a Windows directory junction pointing to a fixture directory.</summary>
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
            _junctionDirectories.Add(linkDirectory);
            return linkDirectory;
        }
    }
}
