using System;
using System.IO;
using NUnit.Framework;

namespace pyRevitExtensionParserTest
{
    /// <summary>
    /// Provides shared test configuration and paths for all test classes.
    /// </summary>
    public static class TestConfiguration
    {
        /// <summary>
        /// Gets the absolute path to the pyRevitDevTools extension used for testing.
        /// This path is calculated relative to the test output directory.
        /// </summary>
        public static string TestExtensionPath
        {
            get
            {
                var testDirectory = TestContext.CurrentContext.TestDirectory;
                return Path.Combine(
                    testDirectory,
                    "..", "..", "..", "..", "..", "..",
                    "extensions", "pyRevitDevTools.extension"
                );
            }
        }

        /// <summary>
        /// Gets the absolute path to the pyRevitDev tab within the test extension.
        /// </summary>
        public static string TestTabPath => Path.Combine(TestExtensionPath, "pyRevitDev.tab");

        /// <summary>
        /// Validates that the test extension path exists.
        /// Throws an Assert.Fail if the path is not found.
        /// </summary>
        public static void ValidateTestExtensionExists()
        {
            if (!Directory.Exists(TestExtensionPath))
            {
                Assert.Fail($"Test extension path not found: {TestExtensionPath}");
            }
        }

        /// <summary>
        /// Gets a path to a specific panel within the test tab.
        /// </summary>
        /// <param name="panelName">The name of the panel (e.g., "TestPanelOne.panel")</param>
        public static string GetPanelPath(string panelName)
        {
            return Path.Combine(TestTabPath, panelName);
        }

        /// <summary>
        /// Gets a path to a specific component within a panel.
        /// </summary>
        /// <param name="panelName">The name of the panel (e.g., "TestPanelOne.panel")</param>
        /// <param name="componentName">The name of the component (e.g., "PanelOneButton1.pushbutton")</param>
        public static string GetComponentPath(string panelName, string componentName)
        {
            return Path.Combine(GetPanelPath(panelName), componentName);
        }
    }
}
