using System.Collections.Generic;
using System.IO;
using System.Linq;
using NUnit.Framework;
using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    /// <summary>
    /// Tests for min_revit_version / max_revit_version filtering in ExtensionParser.
    /// All tests use temporary on-disk extension structures and call ParseInstalledExtensions
    /// directly so filtering behaviour is verified at the parser level, independently of
    /// ExtensionManagerService or any real installed extensions.
    /// </summary>
    [TestFixture]
    public class VersionFilteringTests : TempFileTestBase
    {
        // -------------------------------------------------------------------------
        // Test 1 — Extension excluded by min_revit_version
        // -------------------------------------------------------------------------

        [Test]
        public void Extension_WithMinVersion_IsExcluded_WhenRevitYearIsTooLow()
        {
            // Arrange — extension requires Revit 2025, running 2024
            var builder = new TestExtensionBuilder(TestTempDir, "MinVersionExtension");
            builder.Create();
            TestExtensionBuilder.WriteBundleYaml(builder.ExtensionPath, "min_revit_version: \"2025\"");
            builder.AddTab("Tab").AddPanel("Panel").AddPushButton("Button", "pass");

            // Act
            var results = ParseInstalledExtensions(new[] { builder.ExtensionPath }, revitYear: 2024).ToList();

            // Assert
            Assert.IsEmpty(results, "Extension should be excluded when running Revit version is below min_revit_version");
        }

        // -------------------------------------------------------------------------
        // Test 2 — Extension excluded by max_revit_version
        // -------------------------------------------------------------------------

        [Test]
        public void Extension_WithMaxVersion_IsExcluded_WhenRevitYearIsTooHigh()
        {
            // Arrange — extension supports up to Revit 2022, running 2024
            var builder = new TestExtensionBuilder(TestTempDir, "MaxVersionExtension");
            builder.Create();
            TestExtensionBuilder.WriteBundleYaml(builder.ExtensionPath, "max_revit_version: \"2022\"");
            builder.AddTab("Tab").AddPanel("Panel").AddPushButton("Button", "pass");

            // Act
            var results = ParseInstalledExtensions(new[] { builder.ExtensionPath }, revitYear: 2024).ToList();

            // Assert
            Assert.IsEmpty(results, "Extension should be excluded when running Revit version is above max_revit_version");
        }

        // -------------------------------------------------------------------------
        // Test 3 — Incompatible button excluded while compatible sibling survives
        // -------------------------------------------------------------------------

        [Test]
        public void Button_WithMinVersion_IsExcluded_WhileCompatibleSiblingSurvives()
        {
            // Arrange — two buttons in the same panel; one requires Revit 2025, one has no constraint
            var builder = new TestExtensionBuilder(TestTempDir, "MixedButtonExtension");
            builder.Create();
            var panel = builder.AddTab("Tab").AddPanel("Panel");

            // Button that should be filtered out
            panel.AddPushButton("FutureButton", "pass", "min_revit_version: \"2025\"");

            // Button that should survive
            panel.AddPushButton("CompatibleButton", "pass");

            // Act
            var extension = ParseInstalledExtensions(new[] { builder.ExtensionPath }, revitYear: 2024)
                .Single();
            var allButtons = GetAllButtons(extension);

            // Assert
            Assert.IsFalse(allButtons.Any(b => b.Name == "FutureButton"),
                "Button with min_revit_version: 2025 should be excluded when running Revit 2024");
            Assert.IsTrue(allButtons.Any(b => b.Name == "CompatibleButton"),
                "Button with no version constraint should survive");
        }

        // -------------------------------------------------------------------------
        // Test 4 — Invalid version string is handled gracefully (no exception)
        // -------------------------------------------------------------------------

        [Test]
        public void Extension_WithInvalidVersionString_IsExcluded_WithoutThrowing()
        {
            // Arrange — min_revit_version contains a non-integer value
            var builder = new TestExtensionBuilder(TestTempDir, "InvalidVersionExtension");
            builder.Create();
            TestExtensionBuilder.WriteBundleYaml(builder.ExtensionPath, "min_revit_version: \"not_a_year\"");
            builder.AddTab("Tab").AddPanel("Panel").AddPushButton("Button", "pass");

            // Act & Assert — should not throw, and the extension should be excluded
            List<ParsedExtension>? results = null;
            Assert.DoesNotThrow(() =>
            {
                results = ParseInstalledExtensions(new[] { builder.ExtensionPath }, revitYear: 2024).ToList();
            }, "Parsing an invalid version string should not throw an exception");

            Assert.That(results, Is.Not.Null);
            Assert.IsEmpty(results, "Extension with an unparseable version string should be excluded");
        }

        // -------------------------------------------------------------------------
        // Test 5 — revitYear = 0 bypasses all filtering
        // -------------------------------------------------------------------------

        [Test]
        public void Extension_WithAnyVersionConstraint_IsIncluded_WhenRevitYearIsZero()
        {
            // Arrange — extension nominally requires a future Revit version
            var builder = new TestExtensionBuilder(TestTempDir, "FarFutureExtension");
            builder.Create();
            TestExtensionBuilder.WriteBundleYaml(builder.ExtensionPath, "min_revit_version: \"2099\"");
            builder.AddTab("Tab").AddPanel("Panel").AddPushButton("Button", "pass");

            // Act — revitYear: 0 means Revit version is unknown; filtering should be skipped
            var results = ParseInstalledExtensions(new[] { builder.ExtensionPath }, revitYear: 0).ToList();

            // Assert
            Assert.IsNotEmpty(results, "Extension should be included when revitYear is 0 (version unknown, filtering disabled)");
        }

        // -------------------------------------------------------------------------
        // Helper
        // -------------------------------------------------------------------------

        /// <summary>
        /// Recursively collects all pushbutton-level components from an extension.
        /// </summary>
        private static List<ParsedComponent> GetAllButtons(ParsedComponent root)
        {
            var result = new List<ParsedComponent>();
            if (root.Children == null) return result;

            foreach (var child in root.Children)
            {
                if (child.Type == CommandComponentType.PushButton)
                    result.Add(child);
                else
                    result.AddRange(GetAllButtons(child));
            }

            return result;
        }
    }
}
