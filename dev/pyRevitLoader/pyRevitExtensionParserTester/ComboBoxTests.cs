using System;
using System.Collections.Generic;
using System.IO;
using NUnit.Framework;
using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;

namespace pyRevitExtensionParserTest
{
    /// <summary>
    /// Tests for ComboBox parsing functionality.
    /// </summary>
    [TestFixture]
    public class ComboBoxTests : TempFileTestBase
    {
        [Test]
        public void ParsesComboBoxMembers_FromBundleYaml()
        {
            // Arrange - create a bundle.yaml with members
            var bundleContent = @"title: Test ComboBox
tooltip: Test ComboBox functionality
icon: icon.png
members:
  - id: ""one""
    text: ""One""
  - id: ""two""
    text: ""Two""
";
            var bundlePath = CreateFile("bundle.yaml", bundleContent);

            // Act
            var bundle = BundleParser.BundleYamlParser.Parse(bundlePath);

            // Assert
            Assert.That(bundle, Is.Not.Null);
            Assert.That(bundle.Members, Is.Not.Null);
            Assert.That(bundle.Members.Count, Is.EqualTo(2));
            
            Assert.That(bundle.Members[0].Id, Is.EqualTo("one"));
            Assert.That(bundle.Members[0].Text, Is.EqualTo("One"));
            
            Assert.That(bundle.Members[1].Id, Is.EqualTo("two"));
            Assert.That(bundle.Members[1].Text, Is.EqualTo("Two"));
        }

        [Test]
        public void ParsesComboBoxMembers_WithTooltip()
        {
            // Arrange
            var bundleContent = @"title: Test ComboBox
members:
  - id: ""settings""
    text: ""Settings""
    tooltip: ""Open settings panel""
";
            var bundlePath = CreateFile("bundle.yaml", bundleContent);

            // Act
            var bundle = BundleParser.BundleYamlParser.Parse(bundlePath);

            // Assert
            Assert.That(bundle, Is.Not.Null);
            Assert.That(bundle.Members.Count, Is.EqualTo(1));
            Assert.That(bundle.Members[0].Id, Is.EqualTo("settings"));
            Assert.That(bundle.Members[0].Text, Is.EqualTo("Settings"));
            Assert.That(bundle.Members[0].Tooltip, Is.EqualTo("Open settings panel"));
        }

        [Test]
        public void ParsesComboBoxMembers_WithIcon()
        {
            // Arrange
            var bundleContent = @"title: Test ComboBox
members:
  - id: ""option1""
    text: ""Option 1""
    icon: ""option1.png""
";
            var bundlePath = CreateFile("bundle.yaml", bundleContent);

            // Act
            var bundle = BundleParser.BundleYamlParser.Parse(bundlePath);

            // Assert
            Assert.That(bundle, Is.Not.Null);
            Assert.That(bundle.Members.Count, Is.EqualTo(1));
            Assert.That(bundle.Members[0].Id, Is.EqualTo("option1"));
            Assert.That(bundle.Members[0].Text, Is.EqualTo("Option 1"));
            Assert.That(bundle.Members[0].Icon, Is.EqualTo("option1.png"));
        }

        [Test]
        public void ParsesComboBoxMembers_WithGroup()
        {
            // Arrange
            var bundleContent = @"title: Test ComboBox
members:
  - id: ""opt1""
    text: ""Option 1""
    group: ""Group A""
  - id: ""opt2""
    text: ""Option 2""
    group: ""Group B""
";
            var bundlePath = CreateFile("bundle.yaml", bundleContent);

            // Act
            var bundle = BundleParser.BundleYamlParser.Parse(bundlePath);

            // Assert
            Assert.That(bundle, Is.Not.Null);
            Assert.That(bundle.Members.Count, Is.EqualTo(2));
            Assert.That(bundle.Members[0].Group, Is.EqualTo("Group A"));
            Assert.That(bundle.Members[1].Group, Is.EqualTo("Group B"));
        }

        [Test]
        public void ParsesComboBoxExtension_AsComboBoxType()
        {
            // This test verifies that .combobox directories are parsed correctly
            // by the ExtensionParser
            
            // The type mapping should convert ".combobox" to CommandComponentType.ComboBox
            var type = ExtensionParser.CommandComponentTypeExtensions.FromExtension(".combobox");
            Assert.That(type, Is.EqualTo(ExtensionParser.CommandComponentType.ComboBox));
        }

        [Test]
        public void ComboBoxType_ToExtension_ReturnsCorrectValue()
        {
            // Verify reverse mapping
            var ext = ExtensionParser.CommandComponentType.ComboBox.ToExtension();
            Assert.That(ext, Is.EqualTo(".combobox"));
        }

        [Test]
        public void ParsesComboBoxMembers_WithAllProperties()
        {
            // Arrange - test all member properties
            var bundleContent = @"title: Full ComboBox
members:
  - id: ""full""
    text: ""Full Option""
    icon: ""full.png""
    tooltip: ""Full tooltip""
    group: ""Full Group""
    tooltip_image: ""tooltip.png""
";
            var bundlePath = CreateFile("bundle.yaml", bundleContent);

            // Act
            var bundle = BundleParser.BundleYamlParser.Parse(bundlePath);

            // Assert
            Assert.That(bundle, Is.Not.Null);
            Assert.That(bundle.Members.Count, Is.EqualTo(1));
            
            var member = bundle.Members[0];
            Assert.That(member.Id, Is.EqualTo("full"));
            Assert.That(member.Text, Is.EqualTo("Full Option"));
            Assert.That(member.Icon, Is.EqualTo("full.png"));
            Assert.That(member.Tooltip, Is.EqualTo("Full tooltip"));
            Assert.That(member.Group, Is.EqualTo("Full Group"));
            Assert.That(member.TooltipImage, Is.EqualTo("tooltip.png"));
        }

        [Test]
        public void ParsesEmptyMembers_ReturnsEmptyList()
        {
            // Arrange - bundle without members
            var bundleContent = @"title: No Members
tooltip: Button without members
";
            var bundlePath = CreateFile("bundle.yaml", bundleContent);

            // Act
            var bundle = BundleParser.BundleYamlParser.Parse(bundlePath);

            // Assert
            Assert.That(bundle, Is.Not.Null);
            Assert.That(bundle.Members, Is.Not.Null);
            Assert.That(bundle.Members.Count, Is.EqualTo(0));
        }

        [Test]
        public void ParsedComponent_HasMembersProperty()
        {
            // Verify that ParsedComponent has the Members property
            var component = new ParsedComponent();
            Assert.That(component.Members, Is.Not.Null);
            Assert.That(component.Members.Count, Is.EqualTo(0));
        }
    }
}
