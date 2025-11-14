using pyRevitExtensionParser;
using System.IO;
using NUnit.Framework;
using static pyRevitExtensionParser.ExtensionParser;
using System;
using System.Collections.Generic;
using System.Linq;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class SeparatorTests
    {
        [Test]
        public void TestPanelWithSeparatorInLayout()
        {
            // Create a temporary test panel with separator in layout
            var tempDir = Path.Combine(Path.GetTempPath(), "TestSeparatorPanel.extension");
            var tabDir = Path.Combine(tempDir, "TestTab.tab");
            var panelDir = Path.Combine(tabDir, "TestPanel.panel");
            var button1Dir = Path.Combine(panelDir, "Button1.pushbutton");
            var button2Dir = Path.Combine(panelDir, "Button2.pushbutton");
            var button3Dir = Path.Combine(panelDir, "Button3.pushbutton");
            
            try
            {
                Directory.CreateDirectory(button1Dir);
                Directory.CreateDirectory(button2Dir);
                Directory.CreateDirectory(button3Dir);
                
                // Create script files
                File.WriteAllText(Path.Combine(button1Dir, "script.py"), "print('Button 1')");
                File.WriteAllText(Path.Combine(button2Dir, "script.py"), "print('Button 2')");
                File.WriteAllText(Path.Combine(button3Dir, "script.py"), "print('Button 3')");
                
                // Create bundle.yaml with separator
                var bundlePath = Path.Combine(panelDir, "bundle.yaml");
                var bundleContent = @"layout:
  - Button1
  - -----
  - Button2
  - Button3";
                
                File.WriteAllText(bundlePath, bundleContent);
                
                // Parse the extension
                var extensions = ParseInstalledExtensions(new[] { tempDir });
                var extension = extensions.FirstOrDefault();
                
                Assert.IsNotNull(extension, "Extension should be parsed");
                
                var testPanel = FindComponentRecursively(extension, "TestPanel");
                Assert.IsNotNull(testPanel, "TestPanel should be found");
                Assert.IsNotNull(testPanel.Children, "Panel should have children");
                Assert.AreEqual(4, testPanel.Children.Count, "Panel should have 4 children (3 buttons + 1 separator)");
                
                // Verify the order and separator placement
                Assert.AreEqual("Button1", testPanel.Children[0].DisplayName);
                Assert.AreEqual(CommandComponentType.Separator, testPanel.Children[1].Type);
                Assert.AreEqual("---", testPanel.Children[1].DisplayName);
                Assert.AreEqual("Button2", testPanel.Children[2].DisplayName);
                Assert.AreEqual("Button3", testPanel.Children[3].DisplayName);
                
                TestContext.Out.WriteLine("Panel with separator test passed!");
            }
            finally
            {
                if (Directory.Exists(tempDir))
                    Directory.Delete(tempDir, true);
            }
        }

        [Test]
        public void TestPulldownWithSeparatorsInLayout()
        {
            // Create a temporary test pulldown with separators in layout
            var tempDir = Path.Combine(Path.GetTempPath(), "TestSeparatorPulldown.extension");
            var tabDir = Path.Combine(tempDir, "TestTab.tab");
            var panelDir = Path.Combine(tabDir, "TestPanel.panel");
            var pulldownDir = Path.Combine(panelDir, "TestPulldown.pulldown");
            var button1Dir = Path.Combine(pulldownDir, "Button1.pushbutton");
            var button2Dir = Path.Combine(pulldownDir, "Button2.pushbutton");
            var button3Dir = Path.Combine(pulldownDir, "Button3.pushbutton");
            var button4Dir = Path.Combine(pulldownDir, "Button4.pushbutton");
            
            try
            {
                Directory.CreateDirectory(button1Dir);
                Directory.CreateDirectory(button2Dir);
                Directory.CreateDirectory(button3Dir);
                Directory.CreateDirectory(button4Dir);
                
                // Create script files
                File.WriteAllText(Path.Combine(button1Dir, "script.py"), "print('Button 1')");
                File.WriteAllText(Path.Combine(button2Dir, "script.py"), "print('Button 2')");
                File.WriteAllText(Path.Combine(button3Dir, "script.py"), "print('Button 3')");
                File.WriteAllText(Path.Combine(button4Dir, "script.py"), "print('Button 4')");
                
                // Create bundle.yaml with multiple separators (like the Sheets.pulldown example)
                var bundlePath = Path.Combine(pulldownDir, "bundle.yaml");
                var bundleContent = @"title:
  en_us: Test Pulldown
layout:
  - Button1
  - Button2
  - -----
  - Button3
  - -----
  - Button4";
                
                File.WriteAllText(bundlePath, bundleContent);
                
                // Parse the extension
                var extensions = ParseInstalledExtensions(new[] { tempDir });
                var extension = extensions.FirstOrDefault();
                
                Assert.IsNotNull(extension, "Extension should be parsed");
                
                var testPulldown = FindComponentRecursively(extension, "TestPulldown");
                Assert.IsNotNull(testPulldown, "TestPulldown should be found");
                Assert.IsNotNull(testPulldown.Children, "Pulldown should have children");
                Assert.AreEqual(6, testPulldown.Children.Count, "Pulldown should have 6 children (4 buttons + 2 separators)");
                
                // Verify the order and separator placements
                Assert.AreEqual("Button1", testPulldown.Children[0].DisplayName);
                Assert.AreEqual("Button2", testPulldown.Children[1].DisplayName);
                Assert.AreEqual(CommandComponentType.Separator, testPulldown.Children[2].Type);
                Assert.AreEqual("Button3", testPulldown.Children[3].DisplayName);
                Assert.AreEqual(CommandComponentType.Separator, testPulldown.Children[4].Type);
                Assert.AreEqual("Button4", testPulldown.Children[5].DisplayName);
                
                TestContext.Out.WriteLine("Pulldown with separators test passed!");
            }
            finally
            {
                if (Directory.Exists(tempDir))
                    Directory.Delete(tempDir, true);
            }
        }

        [Test]
        public void TestMultipleSeparatorsInRow()
        {
            // Test that consecutive separators are handled correctly
            var tempDir = Path.Combine(Path.GetTempPath(), "TestMultipleSeparators.extension");
            var tabDir = Path.Combine(tempDir, "TestTab.tab");
            var panelDir = Path.Combine(tabDir, "TestPanel.panel");
            var button1Dir = Path.Combine(panelDir, "Button1.pushbutton");
            var button2Dir = Path.Combine(panelDir, "Button2.pushbutton");
            
            try
            {
                Directory.CreateDirectory(button1Dir);
                Directory.CreateDirectory(button2Dir);
                
                File.WriteAllText(Path.Combine(button1Dir, "script.py"), "print('Button 1')");
                File.WriteAllText(Path.Combine(button2Dir, "script.py"), "print('Button 2')");
                
                var bundlePath = Path.Combine(panelDir, "bundle.yaml");
                var bundleContent = @"layout:
  - Button1
  - -----
  - -----
  - Button2";
                
                File.WriteAllText(bundlePath, bundleContent);
                
                var extensions = ParseInstalledExtensions(new[] { tempDir });
                var extension = extensions.FirstOrDefault();
                
                Assert.IsNotNull(extension);
                
                var testPanel = FindComponentRecursively(extension, "TestPanel");
                Assert.IsNotNull(testPanel);
                Assert.AreEqual(4, testPanel.Children.Count, "Should have 2 buttons and 2 separators");
                
                var separatorCount = testPanel.Children.Count(c => c.Type == CommandComponentType.Separator);
                Assert.AreEqual(2, separatorCount, "Should have exactly 2 separators");
                
                TestContext.Out.WriteLine("Multiple separators test passed!");
            }
            finally
            {
                if (Directory.Exists(tempDir))
                    Directory.Delete(tempDir, true);
            }
        }

        // Helper method to find a component recursively by name
        private ParsedComponent? FindComponentRecursively(ParsedComponent? root, string componentName)
        {
            if (root == null)
                return null;

            if (root.Name == componentName || root.DisplayName == componentName)
                return root;

            if (root.Children != null)
            {
                foreach (var child in root.Children)
                {
                    var found = FindComponentRecursively(child, componentName);
                    if (found != null)
                        return found;
                }
            }

            return null;
        }
    }
}
