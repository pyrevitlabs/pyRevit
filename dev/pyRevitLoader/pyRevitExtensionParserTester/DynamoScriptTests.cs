using System.IO;
using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    /// <summary>Checks Dynamo file discovery using isolated extension fixtures.</summary>
    [TestFixture]
    [Category("HostFree")]
    [Category("Integration")]
    [Category("Regression")]
    public class DynamoScriptTests : TempFileTestBase
    {
        [TestCase("script.dyn")]
        [TestCase("custom_graph.dyn")]
        public void DynamoGraphIsDiscoveredWithoutRevit(string graphName)
        {
            var extensionPath = CreateSubDirectory("Dynamo.extension");
            var buttonPath = Path.Combine(extensionPath, "Tab.tab", "Panel.panel", "Graph.pushbutton");
            Directory.CreateDirectory(buttonPath);
            var graphPath = Path.Combine(buttonPath, graphName);
            File.WriteAllText(graphPath, "{}");
            File.WriteAllText(Path.Combine(buttonPath, "config.dyn"), "{}");
            var extension = ExtensionParser.ParseInstalledExtensions(new[] { extensionPath }).Single();
            var button = extension.Children.Single().Children.Single().Children.Single();
            Assert.That(button.Type, Is.EqualTo(CommandComponentType.PushButton));
            Assert.That(button.ScriptPath, Is.EqualTo(graphPath));
        }
    }
}
