using System;
using System.IO;
using System.Linq;
using NUnit.Framework;
using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class StartupScriptTests
    {
        private string _testBundlePath;
        private ParsedExtension _testExtension;

        [SetUp]
        public void Setup()
        {
            _testBundlePath = TestConfiguration.TestExtensionPath;
            var extensions = ParseInstalledExtensions(new[] { _testBundlePath });
            _testExtension = extensions.FirstOrDefault()!;
        }

        [Test]
        public void StartupScript_Property_Exists()
        {
            // Arrange & Act
            Assert.IsNotNull(_testExtension, "Test extension should be parsed");

            // Assert - Check that StartupScript property is accessible
            var startupScript = _testExtension.StartupScript;
            Assert.DoesNotThrow(() => { var _ = _testExtension.StartupScript; }, 
                "StartupScript property should be accessible without throwing");
        }

        [Test]
        public void StartupScript_FindsPythonStartupScript()
        {
            // Arrange
            Assert.IsNotNull(_testExtension, "Test extension should be parsed");
            
            // Act
            var startupScript = _testExtension.StartupScript;
            
            // Assert
            Assert.IsNotNull(startupScript, "Startup script should be found");
            Assert.IsTrue(File.Exists(startupScript), "Startup script file should exist at the returned path");
            Assert.That(startupScript, Does.EndWith("startup.py"), "Should find Python startup script");
            
            TestContext.Out.WriteLine($"Found startup script: {startupScript}");
        }

        [Test]
        public void StartupScript_ReturnsFullPath()
        {
            // Arrange
            Assert.IsNotNull(_testExtension, "Test extension should be parsed");
            
            // Act
            var startupScript = _testExtension.StartupScript;
            
            // Assert
            Assert.IsNotNull(startupScript, "Startup script should be found");
            Assert.IsTrue(Path.IsPathRooted(startupScript), "Startup script path should be absolute");
            
            TestContext.Out.WriteLine($"Startup script full path: {startupScript}");
        }

        [Test]
        public void StartupScript_VerifiesFileContent()
        {
            // Arrange
            Assert.IsNotNull(_testExtension, "Test extension should be parsed");
            var startupScript = _testExtension.StartupScript;
            Assert.IsNotNull(startupScript, "Startup script should be found");
            
            // Act
            var content = File.ReadAllText(startupScript);
            
            // Assert
            Assert.IsNotEmpty(content, "Startup script should have content");
            // Check for content that actually exists in the pyRevitDevTools startup.py
            Assert.That(content, Does.Contain("startup.py"), 
                "Startup script should be a valid Python startup script");
            Assert.That(content, Does.Contain("pyrevit") | Does.Contain("pyRevit"), 
                "Startup script should reference pyRevit");
            
            TestContext.Out.WriteLine($"Startup script found at: {startupScript}");
            TestContext.Out.WriteLine($"Content length: {content.Length} characters");
            TestContext.Out.WriteLine($"First 200 characters:\n{content.Substring(0, Math.Min(200, content.Length))}...");
        }

        [Test]
        public void StartupScript_ReturnsNullForNonExistentDirectory()
        {
            // Arrange
            var emptyExtension = new ParsedExtension
            {
                Name = "TestEmpty",
                Directory = Path.Combine(Path.GetTempPath(), "NonExistentDirectory_" + Guid.NewGuid())
            };
            
            // Act
            var startupScript = emptyExtension.StartupScript;
            
            // Assert
            Assert.IsNull(startupScript, "Startup script should be null for non-existent directory");
        }

        [Test]
        public void StartupScript_ReturnsNullForDirectoryWithoutStartupScript()
        {
            // Arrange - Create a temporary directory without startup script
            var tempDir = Path.Combine(Path.GetTempPath(), "TestExtensionNoStartup_" + Guid.NewGuid());
            Directory.CreateDirectory(tempDir);
            
            try
            {
                var extensionWithoutStartup = new ParsedExtension
                {
                    Name = "TestNoStartup",
                    Directory = tempDir
                };
                
                // Act
                var startupScript = extensionWithoutStartup.StartupScript;
                
                // Assert
                Assert.IsNull(startupScript, "Startup script should be null when no startup file exists");
            }
            finally
            {
                // Cleanup
                if (Directory.Exists(tempDir))
                    Directory.Delete(tempDir, true);
            }
        }

        [Test]
        public void StartupScript_PrioritizesPythonOverOtherFormats()
        {
            // Arrange - Create a temporary directory with multiple startup files
            var tempDir = Path.Combine(Path.GetTempPath(), "TestExtensionMultiStartup_" + Guid.NewGuid());
            Directory.CreateDirectory(tempDir);
            
            try
            {
                // Create startup files in different formats
                File.WriteAllText(Path.Combine(tempDir, "startup.cs"), "// C# startup");
                File.WriteAllText(Path.Combine(tempDir, "startup.py"), "# Python startup");
                File.WriteAllText(Path.Combine(tempDir, "startup.vb"), "' VB startup");
                
                var extension = new ParsedExtension
                {
                    Name = "TestMultiFormat",
                    Directory = tempDir
                };
                
                // Act
                var startupScript = extension.StartupScript;
                
                // Assert
                Assert.IsNotNull(startupScript, "Startup script should be found");
                Assert.That(startupScript, Does.EndWith("startup.py"), 
                    "Should prioritize Python startup script when multiple formats exist");
                
                TestContext.Out.WriteLine($"Selected startup script: {startupScript}");
            }
            finally
            {
                // Cleanup
                if (Directory.Exists(tempDir))
                    Directory.Delete(tempDir, true);
            }
        }

        [Test]
        public void StartupScript_FindsCSharpWhenPythonNotAvailable()
        {
            // Arrange - Create a temporary directory with only C# startup
            var tempDir = Path.Combine(Path.GetTempPath(), "TestExtensionCSharpStartup_" + Guid.NewGuid());
            Directory.CreateDirectory(tempDir);
            
            try
            {
                File.WriteAllText(Path.Combine(tempDir, "startup.cs"), "// C# startup script");
                
                var extension = new ParsedExtension
                {
                    Name = "TestCSharpStartup",
                    Directory = tempDir
                };
                
                // Act
                var startupScript = extension.StartupScript;
                
                // Assert
                Assert.IsNotNull(startupScript, "Startup script should be found");
                Assert.That(startupScript, Does.EndWith("startup.cs"), 
                    "Should find C# startup script when Python is not available");
                
                TestContext.Out.WriteLine($"Found C# startup script: {startupScript}");
            }
            finally
            {
                // Cleanup
                if (Directory.Exists(tempDir))
                    Directory.Delete(tempDir, true);
            }
        }
    }
}
