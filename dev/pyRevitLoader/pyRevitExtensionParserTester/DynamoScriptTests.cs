using System.IO;
using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class DynamoScriptTests
    {
        private string _devToolsPath;

        [SetUp]
        public void Setup()
        {
            // Path to the real pyRevitDevTools extension
            _devToolsPath = Path.GetFullPath(Path.Combine(
                TestContext.CurrentContext.TestDirectory, 
                "..", "..", "..", "..", "..", "..", 
                "extensions", "pyRevitDevTools.extension"));
        }

        [Test]
        public void Parser_Should_Find_TestDynamoBIM_With_Script_Dyn()
        {
            if (!Directory.Exists(_devToolsPath))
            {
                Assert.Ignore($"pyRevitDevTools extension not found at {_devToolsPath}");
                return;
            }

            // Act - Parse the pyRevitDevTools extension
            var parsedExtensions = ParseInstalledExtensions(new[] { _devToolsPath }).ToList();
            
            Assert.That(parsedExtensions.Count, Is.EqualTo(1), "Should parse pyRevitDevTools extension");
            
            var extension = parsedExtensions.First();
            
            // Look for Test DynamoBIM button (has script.dyn)
            var dynamoButton = FindComponentRecursively(extension, "TestDynamoBIM");
            
            Assert.That(dynamoButton, Is.Not.Null, "Should find TestDynamoBIM button");
            Assert.That(dynamoButton.ScriptPath, Does.EndWith("script.dyn"), 
                "TestDynamoBIM should have script.dyn");
            Assert.That(File.Exists(dynamoButton.ScriptPath), Is.True, 
                "script.dyn file should exist");
            
            // Also verify config.dyn exists in same directory
            var configPath = Path.Combine(Path.GetDirectoryName(dynamoButton.ScriptPath)!, "config.dyn");
            Assert.That(File.Exists(configPath), Is.True, "config.dyn should also exist");
            
            TestContext.WriteLine($"Found TestDynamoBIM script at: {dynamoButton.ScriptPath}");
        }

        [Test]
        public void Parser_Should_Find_TestDynamoBIMGUI_With_Custom_Named_Script()
        {
            if (!Directory.Exists(_devToolsPath))
            {
                Assert.Ignore($"pyRevitDevTools extension not found at {_devToolsPath}");
                return;
            }

            // Act - Parse the pyRevitDevTools extension
            var parsedExtensions = ParseInstalledExtensions(new[] { _devToolsPath }).ToList();
            
            Assert.That(parsedExtensions.Count, Is.EqualTo(1), "Should parse pyRevitDevTools extension");
            
            var extension = parsedExtensions.First();
            
            // Look for Test DynamoBIM GUI button (has BIM1_ArrowHeadSwitcher_script.dyn)
            var dynamoGuiButton = FindComponentRecursively(extension, "TestDynamoBIMGUI");
            
            Assert.That(dynamoGuiButton, Is.Not.Null, "Should find TestDynamoBIMGUI button");
            Assert.That(dynamoGuiButton.ScriptPath, Does.EndWith("BIM1_ArrowHeadSwitcher_script.dyn"), 
                "TestDynamoBIMGUI should have BIM1_ArrowHeadSwitcher_script.dyn");
            Assert.That(File.Exists(dynamoGuiButton.ScriptPath), Is.True, 
                "BIM1_ArrowHeadSwitcher_script.dyn file should exist");
            
            // Also verify the config file exists
            var configPath = Path.Combine(Path.GetDirectoryName(dynamoGuiButton.ScriptPath)!, 
                "BIM1_DeleteUnusedViewTemplates_config.dyn");
            Assert.That(File.Exists(configPath), Is.True, 
                "BIM1_DeleteUnusedViewTemplates_config.dyn should also exist");
            
            TestContext.WriteLine($"Found TestDynamoBIMGUI script at: {dynamoGuiButton.ScriptPath}");
        }

        [Test]
        public void Parser_Should_Recognize_Both_Dynamo_Buttons_As_PushButtons()
        {
            if (!Directory.Exists(_devToolsPath))
            {
                Assert.Ignore($"pyRevitDevTools extension not found at {_devToolsPath}");
                return;
            }

            // Act - Parse the pyRevitDevTools extension
            var parsedExtensions = ParseInstalledExtensions(new[] { _devToolsPath }).ToList();
            var extension = parsedExtensions.First();
            
            // Find both buttons
            var dynamoButton = FindComponentRecursively(extension, "TestDynamoBIM");
            var dynamoGuiButton = FindComponentRecursively(extension, "TestDynamoBIMGUI");
            
            // Assert both are recognized as PushButtons
            Assert.That(dynamoButton, Is.Not.Null, "Should find TestDynamoBIM");
            Assert.That(dynamoButton.Type, Is.EqualTo(CommandComponentType.PushButton), 
                "TestDynamoBIM should be a PushButton");
            
            Assert.That(dynamoGuiButton, Is.Not.Null, "Should find TestDynamoBIMGUI");
            Assert.That(dynamoGuiButton.Type, Is.EqualTo(CommandComponentType.PushButton), 
                "TestDynamoBIMGUI should be a PushButton");
        }

        private ParsedComponent? FindComponentRecursively(ParsedComponent parent, string name)
        {
            if (parent.Name == name || parent.DisplayName == name)
                return parent;

            if (parent.Children != null)
            {
                foreach (var child in parent.Children)
                {
                    var found = FindComponentRecursively(child, name);
                    if (found != null)
                        return found;
                }
            }

            return null!;
        }
    }
}