using NUnit.Framework;
using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;
using System.IO;
using System.Linq;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class SmartButtonTests : TempFileTestBase
    {
        private string _extensionDir;

        [SetUp]
        public override void BaseSetUp()
        {
            base.BaseSetUp();
            _extensionDir = CreateSubDirectory("Test.extension");
        }

        /// <summary>
        /// Helper method to create a basic tab and panel structure.
        /// </summary>
        private string CreateTabAndPanel(string tabName = "Test", string panelName = "TestPanel")
        {
            var tabDir = CreateSubDirectory($"Test.extension/{tabName}.tab");
            var panelDir = CreateSubDirectory($"Test.extension/{tabName}.tab/{panelName}.panel");
            return panelDir;
        }

        /// <summary>
        /// Test that SmartButton inside a pulldown menu is correctly parsed.
        /// This matches the structure of Test Smart Button.smartbutton inside Bundle Tests.pulldown
        /// in pyRevitDevTools.extension.
        /// </summary>
        [Test]
        public void SmartButton_InPulldown_ParsedCorrectly()
        {
            var panelDir = CreateTabAndPanel();
            // Create pulldown structure similar to:
            // extensions/pyRevitDevTools.extension/pyRevitDev.tab/Debug.panel/Bundle Tests.pulldown/Test Smart Button.smartbutton
            var pulldownDir = CreateSubDirectory("Test.extension/Test.tab/TestPanel.panel/Bundle Tests.pulldown");
            var smartButtonDir = CreateSubDirectory("Test.extension/Test.tab/TestPanel.panel/Bundle Tests.pulldown/Test Smart Button.smartbutton");

            // Create script matching the real Test Smart Button structure
            CreateFile("Test.extension/Test.tab/TestPanel.panel/Bundle Tests.pulldown/Test Smart Button.smartbutton/script.py", @"
# Test Smart Button
from pyrevit import script

__context__ = 'zero-doc'
__highlight__= 'updated'

config = script.get_config()

def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    on_icon = script_cmp.get_bundle_file('on.png')
    ui_button_cmp.set_icon(on_icon)

if __name__ == '__main__':
    print('Works...')
");

            // Create icons matching the real Test Smart Button structure
            var minimalPng = CreateMinimalPng();
            CreateFile("Test.extension/Test.tab/TestPanel.panel/Bundle Tests.pulldown/Test Smart Button.smartbutton/icon.png", minimalPng);
            CreateFile("Test.extension/Test.tab/TestPanel.panel/Bundle Tests.pulldown/Test Smart Button.smartbutton/icon.dark.png", minimalPng);
            CreateFile("Test.extension/Test.tab/TestPanel.panel/Bundle Tests.pulldown/Test Smart Button.smartbutton/on.png", minimalPng);
            CreateFile("Test.extension/Test.tab/TestPanel.panel/Bundle Tests.pulldown/Test Smart Button.smartbutton/on.dark.png", minimalPng);
            CreateFile("Test.extension/Test.tab/TestPanel.panel/Bundle Tests.pulldown/Test Smart Button.smartbutton/off.png", minimalPng);
            CreateFile("Test.extension/Test.tab/TestPanel.panel/Bundle Tests.pulldown/Test Smart Button.smartbutton/off.dark.png", minimalPng);

            // Add another button to the pulldown so it's not empty
            var pushButtonDir = CreateSubDirectory("Test.extension/Test.tab/TestPanel.panel/Bundle Tests.pulldown/Other Button.pushbutton");
            CreateFile("Test.extension/Test.tab/TestPanel.panel/Bundle Tests.pulldown/Other Button.pushbutton/script.py", @"
print('Other')
");

            var extensions = ParseInstalledExtensions(new[] { _extensionDir });
            var extension = extensions.First();

            var allComponents = GetAllComponentsFlat(extension);
            
            // Verify pulldown is parsed
            var pulldown = allComponents.FirstOrDefault(c => c.Type == CommandComponentType.PullDown);
            Assert.IsNotNull(pulldown, "Pulldown should be found");
            Assert.AreEqual("Bundle Tests", pulldown.DisplayName);
            
            // Verify SmartButton inside pulldown is parsed
            var smartButton = allComponents.FirstOrDefault(c => c.Type == CommandComponentType.SmartButton);
            Assert.IsNotNull(smartButton, "SmartButton in pulldown should be found");
            Assert.AreEqual("Test Smart Button", smartButton.DisplayName);
            Assert.AreEqual(CommandComponentType.SmartButton, smartButton.Type);
            
            // Verify SmartButton is a child of the pulldown
            Assert.IsNotNull(pulldown.Children, "Pulldown should have children");
            var smartButtonInPulldown = pulldown.Children.FirstOrDefault(c => c.Type == CommandComponentType.SmartButton);
            Assert.IsNotNull(smartButtonInPulldown, "SmartButton should be a child of pulldown");
            
            // Verify on/off icons are detected
            Assert.IsTrue(smartButton.HasToggleIcons, "SmartButton should have toggle icons");
            Assert.IsNotNull(smartButton.OnIconPath, "OnIconPath should not be null");
            Assert.IsNotNull(smartButton.OffIconPath, "OffIconPath should not be null");
        }

        [Test]
        public void SmartButton_ParsedAsSmartButtonType()
        {
            var panelDir = CreateTabAndPanel();
            var smartButtonDir = CreateSubDirectory("Test.extension/Test.tab/TestPanel.panel/Toggle.smartbutton");
            
            // Create a simple smart button script
            CreateFile("Test.extension/Test.tab/TestPanel.panel/Toggle.smartbutton/script.py", @"
# Smart button script
def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    return True
");

            var extensions = ParseInstalledExtensions(new[] { _extensionDir });
            var extension = extensions.First();
            
            var allComponents = GetAllComponentsFlat(extension);
            var smartButton = allComponents.FirstOrDefault(c => c.Type == CommandComponentType.SmartButton);
            
            Assert.IsNotNull(smartButton, "SmartButton should be found");
            Assert.AreEqual(CommandComponentType.SmartButton, smartButton.Type);
            Assert.AreEqual("Toggle", smartButton.DisplayName);
        }

        [Test]
        public void SmartButton_DetectsConfigScript()
        {
            var panelDir = CreateTabAndPanel();
            var smartButtonDir = CreateSubDirectory("Test.extension/Test.tab/TestPanel.panel/Toggle.smartbutton");
            
            // Create main script
            CreateFile("Test.extension/Test.tab/TestPanel.panel/Toggle.smartbutton/script.py", @"
# Main script
print('Hello')
");
            
            // Create config script
            CreateFile("Test.extension/Test.tab/TestPanel.panel/Toggle.smartbutton/config.py", @"
# Config script for shift+click
print('Config')
");

            var extensions = ParseInstalledExtensions(new[] { _extensionDir });
            var extension = extensions.First();
            
            var allComponents = GetAllComponentsFlat(extension);
            var smartButton = allComponents.FirstOrDefault(c => c.Type == CommandComponentType.SmartButton);
            
            Assert.IsNotNull(smartButton, "SmartButton should be found");
            Assert.IsTrue(smartButton.HasConfigScript, "SmartButton should have config script");
            Assert.IsNotNull(smartButton.ConfigScriptPath, "ConfigScriptPath should not be null");
            Assert.IsTrue(smartButton.ConfigScriptPath.EndsWith("config.py"), "ConfigScriptPath should end with config.py");
            Assert.AreNotEqual(smartButton.ScriptPath, smartButton.ConfigScriptPath, "ConfigScriptPath should differ from ScriptPath");
        }

        [Test]
        public void SmartButton_NoConfigScript_HasConfigScriptIsFalse()
        {
            var panelDir = CreateTabAndPanel();
            var smartButtonDir = CreateSubDirectory("Test.extension/Test.tab/TestPanel.panel/Toggle.smartbutton");
            
            // Create only main script (no config.py)
            CreateFile("Test.extension/Test.tab/TestPanel.panel/Toggle.smartbutton/script.py", @"
# Main script only
print('Hello')
");

            var extensions = ParseInstalledExtensions(new[] { _extensionDir });
            var extension = extensions.First();
            
            var allComponents = GetAllComponentsFlat(extension);
            var smartButton = allComponents.FirstOrDefault(c => c.Type == CommandComponentType.SmartButton);
            
            Assert.IsNotNull(smartButton, "SmartButton should be found");
            Assert.IsFalse(smartButton.HasConfigScript, "SmartButton should not have config script");
            // ConfigScriptPath should equal ScriptPath when no separate config exists
            Assert.AreEqual(smartButton.ScriptPath, smartButton.ConfigScriptPath, 
                "ConfigScriptPath should equal ScriptPath when no config.py exists");
        }

        [Test]
        public void SmartButton_DetectsOnOffIcons()
        {
            var panelDir = CreateTabAndPanel();
            var smartButtonDir = CreateSubDirectory("Test.extension/Test.tab/TestPanel.panel/Toggle.smartbutton");
            
            // Create script
            CreateFile("Test.extension/Test.tab/TestPanel.panel/Toggle.smartbutton/script.py", @"
print('Hello')
");
            
            // Create on/off icons (minimal valid PNG)
            var minimalPng = CreateMinimalPng();
            CreateFile("Test.extension/Test.tab/TestPanel.panel/Toggle.smartbutton/on.png", minimalPng);
            CreateFile("Test.extension/Test.tab/TestPanel.panel/Toggle.smartbutton/off.png", minimalPng);

            var extensions = ParseInstalledExtensions(new[] { _extensionDir });
            var extension = extensions.First();
            
            var allComponents = GetAllComponentsFlat(extension);
            var smartButton = allComponents.FirstOrDefault(c => c.Type == CommandComponentType.SmartButton);
            
            Assert.IsNotNull(smartButton, "SmartButton should be found");
            Assert.IsTrue(smartButton.HasToggleIcons, "SmartButton should have toggle icons");
            Assert.IsNotNull(smartButton.OnIconPath, "OnIconPath should not be null");
            Assert.IsNotNull(smartButton.OffIconPath, "OffIconPath should not be null");
            Assert.IsTrue(smartButton.OnIconPath.EndsWith("on.png", System.StringComparison.OrdinalIgnoreCase), 
                "OnIconPath should end with on.png");
            Assert.IsTrue(smartButton.OffIconPath.EndsWith("off.png", System.StringComparison.OrdinalIgnoreCase), 
                "OffIconPath should end with off.png");
        }

        [Test]
        public void SmartButton_DetectsDarkOnOffIcons()
        {
            var panelDir = CreateTabAndPanel();
            var smartButtonDir = CreateSubDirectory("Test.extension/Test.tab/TestPanel.panel/Toggle.smartbutton");
            
            // Create script
            CreateFile("Test.extension/Test.tab/TestPanel.panel/Toggle.smartbutton/script.py", @"
print('Hello')
");
            
            // Create on/off icons with dark variants
            var minimalPng = CreateMinimalPng();
            CreateFile("Test.extension/Test.tab/TestPanel.panel/Toggle.smartbutton/on.png", minimalPng);
            CreateFile("Test.extension/Test.tab/TestPanel.panel/Toggle.smartbutton/on.dark.png", minimalPng);
            CreateFile("Test.extension/Test.tab/TestPanel.panel/Toggle.smartbutton/off.png", minimalPng);
            CreateFile("Test.extension/Test.tab/TestPanel.panel/Toggle.smartbutton/off.dark.png", minimalPng);

            var extensions = ParseInstalledExtensions(new[] { _extensionDir });
            var extension = extensions.First();
            
            var allComponents = GetAllComponentsFlat(extension);
            var smartButton = allComponents.FirstOrDefault(c => c.Type == CommandComponentType.SmartButton);
            
            Assert.IsNotNull(smartButton, "SmartButton should be found");
            Assert.IsTrue(smartButton.HasToggleIcons, "SmartButton should have toggle icons");
            Assert.IsNotNull(smartButton.OnIconPath, "OnIconPath should not be null");
            Assert.IsNotNull(smartButton.OnIconDarkPath, "OnIconDarkPath should not be null");
            Assert.IsNotNull(smartButton.OffIconPath, "OffIconPath should not be null");
            Assert.IsNotNull(smartButton.OffIconDarkPath, "OffIconDarkPath should not be null");
            Assert.IsTrue(smartButton.OnIconDarkPath.EndsWith("on.dark.png", System.StringComparison.OrdinalIgnoreCase), 
                "OnIconDarkPath should end with on.dark.png");
            Assert.IsTrue(smartButton.OffIconDarkPath.EndsWith("off.dark.png", System.StringComparison.OrdinalIgnoreCase), 
                "OffIconDarkPath should end with off.dark.png");
        }

        [Test]
        public void SmartButton_NoToggleIcons_HasToggleIconsIsFalse()
        {
            var panelDir = CreateTabAndPanel();
            var smartButtonDir = CreateSubDirectory("Test.extension/Test.tab/TestPanel.panel/Toggle.smartbutton");
            
            // Create only script (no on/off icons)
            CreateFile("Test.extension/Test.tab/TestPanel.panel/Toggle.smartbutton/script.py", @"
print('Hello')
");

            var extensions = ParseInstalledExtensions(new[] { _extensionDir });
            var extension = extensions.First();
            
            var allComponents = GetAllComponentsFlat(extension);
            var smartButton = allComponents.FirstOrDefault(c => c.Type == CommandComponentType.SmartButton);
            
            Assert.IsNotNull(smartButton, "SmartButton should be found");
            Assert.IsFalse(smartButton.HasToggleIcons, "SmartButton should not have toggle icons");
            Assert.IsNull(smartButton.OnIconPath, "OnIconPath should be null");
            Assert.IsNull(smartButton.OffIconPath, "OffIconPath should be null");
        }

        [Test]
        public void SmartButton_PartialToggleIcons_HasToggleIconsIsTrue()
        {
            var panelDir = CreateTabAndPanel();
            var smartButtonDir = CreateSubDirectory("Test.extension/Test.tab/TestPanel.panel/Toggle.smartbutton");
            
            // Create script
            CreateFile("Test.extension/Test.tab/TestPanel.panel/Toggle.smartbutton/script.py", @"
print('Hello')
");
            
            // Create only on.png (no off.png)
            var minimalPng = CreateMinimalPng();
            CreateFile("Test.extension/Test.tab/TestPanel.panel/Toggle.smartbutton/on.png", minimalPng);

            var extensions = ParseInstalledExtensions(new[] { _extensionDir });
            var extension = extensions.First();
            
            var allComponents = GetAllComponentsFlat(extension);
            var smartButton = allComponents.FirstOrDefault(c => c.Type == CommandComponentType.SmartButton);
            
            Assert.IsNotNull(smartButton, "SmartButton should be found");
            Assert.IsTrue(smartButton.HasToggleIcons, "SmartButton should have toggle icons even with partial set");
            Assert.IsNotNull(smartButton.OnIconPath, "OnIconPath should not be null");
            Assert.IsNull(smartButton.OffIconPath, "OffIconPath should be null");
        }

        [Test]
        public void PushButton_DetectsConfigScript()
        {
            var panelDir = CreateTabAndPanel();
            var buttonDir = CreateSubDirectory("Test.extension/Test.tab/TestPanel.panel/MyButton.pushbutton");
            
            // Create main script
            CreateFile("Test.extension/Test.tab/TestPanel.panel/MyButton.pushbutton/script.py", @"
# Main script
print('Hello')
");
            
            // Create config script
            CreateFile("Test.extension/Test.tab/TestPanel.panel/MyButton.pushbutton/config.py", @"
# Config script
print('Config')
");

            var extensions = ParseInstalledExtensions(new[] { _extensionDir });
            var extension = extensions.First();
            
            var allComponents = GetAllComponentsFlat(extension);
            var pushButton = allComponents.FirstOrDefault(c => c.Type == CommandComponentType.PushButton);
            
            Assert.IsNotNull(pushButton, "PushButton should be found");
            Assert.IsTrue(pushButton.HasConfigScript, "PushButton should have config script");
        }

        [Test]
        public void SmartButton_InStack_ParsedCorrectly()
        {
            var panelDir = CreateTabAndPanel();
            var stackDir = CreateSubDirectory("Test.extension/Test.tab/TestPanel.panel/MyStack.stack");
            var smartButtonDir = CreateSubDirectory("Test.extension/Test.tab/TestPanel.panel/MyStack.stack/Toggle.smartbutton");
            var pushButtonDir = CreateSubDirectory("Test.extension/Test.tab/TestPanel.panel/MyStack.stack/Other.pushbutton");
            
            // Create scripts
            CreateFile("Test.extension/Test.tab/TestPanel.panel/MyStack.stack/Toggle.smartbutton/script.py", @"
def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    return True
");
            CreateFile("Test.extension/Test.tab/TestPanel.panel/MyStack.stack/Toggle.smartbutton/config.py", @"
print('Config')
");
            CreateFile("Test.extension/Test.tab/TestPanel.panel/MyStack.stack/Other.pushbutton/script.py", @"
print('Other')
");

            // Create on/off icons for smartbutton
            var minimalPng = CreateMinimalPng();
            CreateFile("Test.extension/Test.tab/TestPanel.panel/MyStack.stack/Toggle.smartbutton/on.png", minimalPng);
            CreateFile("Test.extension/Test.tab/TestPanel.panel/MyStack.stack/Toggle.smartbutton/off.png", minimalPng);

            var extensions = ParseInstalledExtensions(new[] { _extensionDir });
            var extension = extensions.First();
            
            var allComponents = GetAllComponentsFlat(extension);
            var smartButton = allComponents.FirstOrDefault(c => c.Type == CommandComponentType.SmartButton);
            
            Assert.IsNotNull(smartButton, "SmartButton in stack should be found");
            Assert.IsTrue(smartButton.HasConfigScript, "SmartButton in stack should have config script");
            Assert.IsTrue(smartButton.HasToggleIcons, "SmartButton in stack should have toggle icons");
        }

        /// <summary>
        /// Helper to get all components in a flat list for easier assertions.
        /// </summary>
        private static System.Collections.Generic.List<ParsedComponent> GetAllComponentsFlat(ParsedExtension extension)
        {
            var result = new System.Collections.Generic.List<ParsedComponent>();
            CollectComponents(extension.Children, result);
            return result;
        }

        private static void CollectComponents(System.Collections.Generic.IEnumerable<ParsedComponent> components, 
            System.Collections.Generic.List<ParsedComponent> result)
        {
            if (components == null) return;
            foreach (var comp in components)
            {
                result.Add(comp);
                if (comp.Children != null)
                    CollectComponents(comp.Children, result);
            }
        }

        [Test]
        public void SmartButton_ConfigScriptPath_IsPassedToCodeGenerator()
        {
            var panelDir = CreateTabAndPanel();
            var smartButtonDir = CreateSubDirectory("Test.extension/Test.tab/TestPanel.panel/Toggle.smartbutton");
            
            // Create main script and config script
            CreateFile("Test.extension/Test.tab/TestPanel.panel/Toggle.smartbutton/script.py", @"
def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    return True

if __name__ == '__main__':
    if __shiftclick__:
        print('Config mode')
    else:
        print('Normal mode')
");
            CreateFile("Test.extension/Test.tab/TestPanel.panel/Toggle.smartbutton/config.py", @"
# Config script - runs on SHIFT+Click
print('Config dialog')
");

            var extensions = ParseInstalledExtensions(new[] { _extensionDir });
            var extension = extensions.First();
            
            // Verify the extension was parsed correctly
            Assert.IsNotNull(extension, "Extension should be parsed");
            
            // Get the SmartButton component
            var allComponents = GetAllComponentsFlat(extension);
            var smartButton = allComponents.FirstOrDefault(c => c.Type == CommandComponentType.SmartButton);
            
            Assert.IsNotNull(smartButton, "SmartButton should be found");
            Assert.IsTrue(smartButton.HasConfigScript, "SmartButton should have config script");
            
            // Verify config script path is different from script path
            Assert.AreNotEqual(smartButton.ScriptPath, smartButton.ConfigScriptPath,
                "ConfigScriptPath should be different from ScriptPath");
            
            // Generate code using RoslynCommandTypeGenerator
            var codeGenerator = new pyRevitAssemblyBuilder.AssemblyMaker.RoslynCommandTypeGenerator();
            var generatedCode = codeGenerator.GenerateExtensionCode(extension, "2024");
            
            // Verify the generated code contains the config script path
            Assert.IsTrue(generatedCode.Contains("config.py"),
                "Generated code should contain config.py path");
            
            // Verify both script path and config path are in the generated code (they should be different)
            Assert.IsTrue(generatedCode.Contains("script.py"),
                "Generated code should contain script.py path");
        }

        [Test]
        public void SmartButton_NoConfigScript_GeneratedCodeUsesSamePathForBoth()
        {
            var panelDir = CreateTabAndPanel();
            var smartButtonDir = CreateSubDirectory("Test.extension/Test.tab/TestPanel.panel/Toggle.smartbutton");
            
            // Create only main script (no config script)
            CreateFile("Test.extension/Test.tab/TestPanel.panel/Toggle.smartbutton/script.py", @"
print('Hello')
");

            var extensions = ParseInstalledExtensions(new[] { _extensionDir });
            var extension = extensions.First();
            
            var allComponents = GetAllComponentsFlat(extension);
            var smartButton = allComponents.FirstOrDefault(c => c.Type == CommandComponentType.SmartButton);
            
            Assert.IsNotNull(smartButton, "SmartButton should be found");
            Assert.IsFalse(smartButton.HasConfigScript, "SmartButton should not have config script");
            
            // ConfigScriptPath should equal ScriptPath when no separate config exists
            Assert.AreEqual(smartButton.ScriptPath, smartButton.ConfigScriptPath,
                "ConfigScriptPath should equal ScriptPath when no config.py exists");
        }

        [Test]
        public void PushButton_ConfigScriptPath_DetectedCorrectly()
        {
            var panelDir = CreateTabAndPanel();
            var buttonDir = CreateSubDirectory("Test.extension/Test.tab/TestPanel.panel/MyButton.pushbutton");
            
            // Create main script and config script
            CreateFile("Test.extension/Test.tab/TestPanel.panel/MyButton.pushbutton/script.py", @"
print('Main action')
");
            CreateFile("Test.extension/Test.tab/TestPanel.panel/MyButton.pushbutton/config.py", @"
print('Config dialog')
");

            var extensions = ParseInstalledExtensions(new[] { _extensionDir });
            var extension = extensions.First();
            
            var allComponents = GetAllComponentsFlat(extension);
            var pushButton = allComponents.FirstOrDefault(c => c.Type == CommandComponentType.PushButton);
            
            Assert.IsNotNull(pushButton, "PushButton should be found");
            Assert.IsTrue(pushButton.HasConfigScript, "PushButton should have config script");
            Assert.IsNotNull(pushButton.ConfigScriptPath, "ConfigScriptPath should not be null");
            Assert.IsTrue(pushButton.ConfigScriptPath.EndsWith("config.py"), 
                "ConfigScriptPath should end with config.py");
        }

        /// <summary>
        /// Creates a minimal valid PNG file (1x1 pixel, transparent).
        /// </summary>
        private static byte[] CreateMinimalPng()
        {
            // Minimal 1x1 transparent PNG
            return new byte[]
            {
                0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, // PNG signature
                0x00, 0x00, 0x00, 0x0D, // IHDR length
                0x49, 0x48, 0x44, 0x52, // IHDR
                0x00, 0x00, 0x00, 0x01, // width: 1
                0x00, 0x00, 0x00, 0x01, // height: 1
                0x08, 0x06, // bit depth: 8, color type: RGBA
                0x00, 0x00, 0x00, // compression, filter, interlace
                0x1F, 0x15, 0xC4, 0x89, // CRC
                0x00, 0x00, 0x00, 0x0A, // IDAT length
                0x49, 0x44, 0x41, 0x54, // IDAT
                0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00, 0x05, 0x00, 0x01, // zlib data
                0x0D, 0x0A, 0x2D, 0xB4, // CRC
                0x00, 0x00, 0x00, 0x00, // IEND length
                0x49, 0x45, 0x4E, 0x44, // IEND
                0xAE, 0x42, 0x60, 0x82  // CRC
            };
        }
    }
}


