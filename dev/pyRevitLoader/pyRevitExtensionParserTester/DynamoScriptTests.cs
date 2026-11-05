using System.IO;
using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    /// <summary>
    /// Script discovery for Dynamo bundles: the default <c>script.dyn</c> next to its
    /// <c>config.dyn</c>, and a custom-named <c>*_script.dyn</c>. The bundles are built
    /// in a temp extension because pyRevitDevTools no longer ships these exact buttons.
    /// </summary>
    [TestFixture]
    public class DynamoScriptTests : TempFileTestBase
    {
        private const string EmptyDynamoGraph = "{}";

        private string _extensionPath;

        [SetUp]
        public void Setup()
        {
            var builder = new TestExtensionBuilder(TestTempDir, "DynamoTests").Create();
            var panelPath = builder.AddTab("DynamoTab").AddPanel("DynamoPanel").PanelPath;
            _extensionPath = builder.ExtensionPath;

            var dynamoDir = Directory.CreateDirectory(Path.Combine(panelPath, "Test DynamoBIM.pushbutton")).FullName;
            File.WriteAllText(Path.Combine(dynamoDir, "script.dyn"), EmptyDynamoGraph);
            File.WriteAllText(Path.Combine(dynamoDir, "config.dyn"), EmptyDynamoGraph);

            var dynamoGuiDir = Directory.CreateDirectory(Path.Combine(panelPath, "Test DynamoBIM GUI.pushbutton")).FullName;
            File.WriteAllText(Path.Combine(dynamoGuiDir, "folie_architecturale_script.dyn"), EmptyDynamoGraph);
        }

        [Test]
        public void Parser_Should_Find_TestDynamoBIM_With_Script_Dyn()
        {
            var parsedExtensions = ParseInstalledExtensions(new[] { _extensionPath }).ToList();

            Assert.That(parsedExtensions.Count, Is.EqualTo(1), "Should parse the Dynamo test extension");

            var dynamoButton = FindComponentRecursively(parsedExtensions.First(), "TestDynamoBIM");

            Assert.That(dynamoButton, Is.Not.Null, "Should find TestDynamoBIM button");
            Assert.That(dynamoButton.ScriptPath, Does.EndWith("script.dyn"),
                "TestDynamoBIM should have script.dyn");
            Assert.That(File.Exists(dynamoButton.ScriptPath), Is.True,
                "script.dyn file should exist");

            var configPath = Path.Combine(Path.GetDirectoryName(dynamoButton.ScriptPath)!, "config.dyn");
            Assert.That(File.Exists(configPath), Is.True, "config.dyn should also exist");
        }

        [Test]
        public void Parser_Should_Find_TestDynamoBIMGUI_With_Custom_Named_Script()
        {
            var parsedExtensions = ParseInstalledExtensions(new[] { _extensionPath }).ToList();

            Assert.That(parsedExtensions.Count, Is.EqualTo(1), "Should parse the Dynamo test extension");

            var dynamoGuiButton = FindComponentRecursively(parsedExtensions.First(), "TestDynamoBIMGUI");

            Assert.That(dynamoGuiButton, Is.Not.Null, "Should find TestDynamoBIMGUI button");
            Assert.That(dynamoGuiButton.ScriptPath, Does.EndWith("folie_architecturale_script.dyn"),
                "TestDynamoBIMGUI should have custom-named folie_architecturale_script.dyn");
            Assert.That(File.Exists(dynamoGuiButton.ScriptPath), Is.True,
                "folie_architecturale_script.dyn file should exist");
        }

        [Test]
        public void Parser_Should_Recognize_Both_Dynamo_Buttons_As_PushButtons()
        {
            var extension = ParseInstalledExtensions(new[] { _extensionPath }).First();

            var dynamoButton = FindComponentRecursively(extension, "TestDynamoBIM");
            var dynamoGuiButton = FindComponentRecursively(extension, "TestDynamoBIMGUI");

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
