using System.IO;
using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;

namespace pyRevitExtensionParserTest
{
    /// <summary>Issue #2992: a Dynamo configuration graph must never become the main command.</summary>
    [TestFixture]
    [NonParallelizable]
    [Category("HostFree")]
    [Category("Integration")]
    [Category("Regression")]
    public class DynamoGraphSelectionTests : TempFileTestBase
    {
        /// <summary>Configuration-only bundles have no executable graph, regardless of filename casing.</summary>
        [TestCase("config.dyn")]
        [TestCase("CONFIG.dyn")]
        public void ConfigurationOnlyBundleDoesNotExecuteConfig(string configuration)
        {
            var extension = CreateSubDirectory("DynamoSelection.extension");
            var button = Path.Combine("DynamoSelection.extension", "Tests.tab", "Tests.panel", "Smoke.pushbutton");
            var configPath = CreateFile(Path.Combine(button, configuration), "{}");

            var parsed = ExtensionParser.ParseInstalledExtensions(new[] { extension }).Single();

            Assert.That(Components(parsed).Any(component => component.ScriptPath == configPath), Is.False);
        }

        /// <summary>Custom graph names remain executable when a sibling config graph is present.</summary>
        [TestCase("config.dyn")]
        [TestCase("CONFIG.dyn")]
        public void CustomGraphWinsOverConfiguration(string configuration)
        {
            var extension = CreateSubDirectory("DynamoSelection.extension");
            var button = Path.Combine("DynamoSelection.extension", "Tests.tab", "Tests.panel", "Smoke.pushbutton");
            CreateFile(Path.Combine(button, configuration), "{}");
            var graphPath = CreateFile(Path.Combine(button, "execution_script.dyn"), "{}");

            var parsed = ExtensionParser.ParseInstalledExtensions(new[] { extension }).Single();
            var command = Components(parsed).Single(component => component.Name == "Smoke");

            Assert.That(command.ScriptPath, Is.EqualTo(graphPath));
        }

        private static IEnumerable<ParsedComponent> Components(ParsedComponent component)
        {
            yield return component;
            foreach (var child in component.Children)
                foreach (var descendant in Components(child))
                    yield return descendant;
        }
    }
}
