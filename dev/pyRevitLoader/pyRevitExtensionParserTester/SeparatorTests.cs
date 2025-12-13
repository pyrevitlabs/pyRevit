using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;
using System.IO;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class SeparatorTests : TempFileTestBase
    {
        [Test]
        public void TestPanelWithSeparatorInLayout()
        {
            // Use TestExtensionBuilder to create extension structure
            var builder = new TestExtensionBuilder(TestTempDir, "TestSeparatorPanel");
            var panelBuilder = builder.Create()
                .AddTab("TestTab")
                .AddPanel("TestPanel");
            
            // Add buttons using the helper
            TestExtensionBuilder.CreatePushButton(panelBuilder.PanelPath, "Button1", "print('Button 1')");
            TestExtensionBuilder.CreatePushButton(panelBuilder.PanelPath, "Button2", "print('Button 2')");
            TestExtensionBuilder.CreatePushButton(panelBuilder.PanelPath, "Button3", "print('Button 3')");
            
            // Create bundle.yaml with separator
            var bundleContent = @"layout:
  - Button1
  - -----
  - Button2
  - Button3";
            
            TestExtensionBuilder.WriteBundleYaml(panelBuilder.PanelPath, bundleContent);
            
            // Parse the extension
            var extensions = ParseInstalledExtensions(new[] { builder.ExtensionPath });
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

        [Test]
        public void TestPulldownWithSeparatorsInLayout()
        {
            // Use TestExtensionBuilder to create extension structure
            var builder = new TestExtensionBuilder(TestTempDir, "TestSeparatorPulldown");
            var panelBuilder = builder.Create()
                .AddTab("TestTab")
                .AddPanel("TestPanel");
            
            var pulldownPath = TestExtensionBuilder.CreatePulldown(panelBuilder.PanelPath, "TestPulldown");
            
            // Add buttons to pulldown
            TestExtensionBuilder.CreatePushButton(pulldownPath, "Button1", "print('Button 1')");
            TestExtensionBuilder.CreatePushButton(pulldownPath, "Button2", "print('Button 2')");
            TestExtensionBuilder.CreatePushButton(pulldownPath, "Button3", "print('Button 3')");
            TestExtensionBuilder.CreatePushButton(pulldownPath, "Button4", "print('Button 4')");
            
            // Create bundle.yaml with multiple separators
            var bundleContent = @"title:
  en_us: Test Pulldown
layout:
  - Button1
  - Button2
  - -----
  - Button3
  - -----
  - Button4";
            
            TestExtensionBuilder.WriteBundleYaml(pulldownPath, bundleContent);
            
            // Parse the extension
            var extensions = ParseInstalledExtensions(new[] { builder.ExtensionPath });
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

        [Test]
        public void TestMultipleSeparatorsInRow()
        {
            // Test that consecutive separators are handled correctly using TestExtensionBuilder
            var builder = new TestExtensionBuilder(TestTempDir, "TestMultipleSeparators");
            var panelBuilder = builder.Create()
                .AddTab("TestTab")
                .AddPanel("TestPanel");
            
            TestExtensionBuilder.CreatePushButton(panelBuilder.PanelPath, "Button1", "print('Button 1')");
            TestExtensionBuilder.CreatePushButton(panelBuilder.PanelPath, "Button2", "print('Button 2')");
            
            var bundleContent = @"layout:
  - Button1
  - -----
  - -----
  - Button2";
            
            TestExtensionBuilder.WriteBundleYaml(panelBuilder.PanelPath, bundleContent);
            
            var extensions = ParseInstalledExtensions(new[] { builder.ExtensionPath });
            var extension = extensions.FirstOrDefault();
            
            Assert.IsNotNull(extension);
            
            var testPanel = FindComponentRecursively(extension, "TestPanel");
            Assert.IsNotNull(testPanel);
            Assert.AreEqual(4, testPanel.Children.Count, "Should have 2 buttons and 2 separators");
            
            var separatorCount = testPanel.Children.Count(c => c.Type == CommandComponentType.Separator);
            Assert.AreEqual(2, separatorCount, "Should have exactly 2 separators");
            
            TestContext.Out.WriteLine("Multiple separators test passed!");
        }

        [Test]
        public void TestPanelWithSlideoutMarker()
        {
            // Test that slideout marker (>>>>>) creates a slideout but NOT a separator
            var builder = new TestExtensionBuilder(TestTempDir, "TestSlideoutPanel");
            var panelBuilder = builder.Create()
                .AddTab("TestTab")
                .AddPanel("TestPanel");
            
            TestExtensionBuilder.CreatePushButton(panelBuilder.PanelPath, "Button1", "print('Button 1')");
            TestExtensionBuilder.CreatePushButton(panelBuilder.PanelPath, "Button2", "print('Button 2')");
            TestExtensionBuilder.CreatePushButton(panelBuilder.PanelPath, "Button3", "print('Button 3')");
            
            var bundleContent = @"layout:
  - Button1
  - '>>>>>'
  - Button2
  - Button3";
            
            TestExtensionBuilder.WriteBundleYaml(panelBuilder.PanelPath, bundleContent);
            
            var extensions = ParseInstalledExtensions(new[] { builder.ExtensionPath });
            var extension = extensions.FirstOrDefault();
            
            Assert.IsNotNull(extension, "Extension should be parsed");
            
            var testPanel = FindComponentRecursively(extension, "TestPanel");
            Assert.IsNotNull(testPanel, "TestPanel should be found");
            Assert.IsNotNull(testPanel.Children, "Panel should have children");
            
            // Should have 3 buttons + 1 slideout marker = 4 children
            Assert.AreEqual(4, testPanel.Children.Count, "Panel should have 4 children (3 buttons + 1 slideout marker)");
            
            // Find the slideout marker
            var slideoutMarker = testPanel.Children.FirstOrDefault(c => c.HasSlideout);
            Assert.IsNotNull(slideoutMarker, "Should have a slideout marker component");
            Assert.AreEqual(CommandComponentType.Separator, slideoutMarker.Type, "Slideout marker should have Separator type");
            Assert.IsTrue(slideoutMarker.HasSlideout, "Slideout marker should have HasSlideout = true");
            Assert.AreEqual(">>>", slideoutMarker.DisplayName, "Slideout marker should be named '>>>'");
            
            // Verify layout order
            Assert.AreEqual("Button1", testPanel.Children[0].DisplayName);
            Assert.IsTrue(testPanel.Children[1].HasSlideout, "Second element should be the slideout marker");
            Assert.AreEqual("Button2", testPanel.Children[2].DisplayName);
            Assert.AreEqual("Button3", testPanel.Children[3].DisplayName);
            
            TestContext.Out.WriteLine("Panel with slideout marker test passed!");
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
