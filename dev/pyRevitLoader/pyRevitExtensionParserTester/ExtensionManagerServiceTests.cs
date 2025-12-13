using pyRevitAssemblyBuilder.SessionManager;

namespace pyRevitExtensionParserTester
{
    /// <summary>
    /// Unit tests for ExtensionManagerService.
    /// </summary>
    [TestFixture]
    public class ExtensionManagerServiceTests
    {
        private ExtensionManagerService _service;

        [SetUp]
        public void SetUp()
        {
            _service = new ExtensionManagerService();
        }

        [Test]
        public void GetInstalledExtensions_ReturnsNonDisabledExtensions()
        {
            // Arrange & Act
            var extensions = _service.GetInstalledExtensions().ToList();

            // Assert
            Assert.IsNotNull(extensions);
            // All returned extensions should not be disabled
            foreach (var ext in extensions)
            {
                Assert.IsFalse(ext.Config?.Disabled == true, $"Extension '{ext.Name}' should not be disabled");
            }
        }

        [Test]
        public void GetInstalledUIExtensions_ReturnsOnlyExtensionFiles()
        {
            // Arrange & Act
            var extensions = _service.GetInstalledUIExtensions().ToList();

            // Assert
            Assert.IsNotNull(extensions);
            foreach (var ext in extensions)
            {
                Assert.IsTrue(ext.Directory.EndsWith(".extension", System.StringComparison.OrdinalIgnoreCase),
                    $"Extension '{ext.Name}' should end with .extension");
                Assert.IsFalse(ext.Config?.Disabled == true, $"Extension '{ext.Name}' should not be disabled");
            }
        }

        [Test]
        public void GetInstalledLibraryExtensions_ReturnsOnlyLibFiles()
        {
            // Arrange & Act
            var extensions = _service.GetInstalledLibraryExtensions().ToList();

            // Assert
            Assert.IsNotNull(extensions);
            foreach (var ext in extensions)
            {
                Assert.IsTrue(ext.Directory.EndsWith(".lib", System.StringComparison.OrdinalIgnoreCase),
                    $"Extension '{ext.Name}' should end with .lib");
                Assert.IsFalse(ext.Config?.Disabled == true, $"Extension '{ext.Name}' should not be disabled");
            }
        }

        [Test]
        public void GetInstalledExtensions_ExcludesDisabledExtensions()
        {
            // Arrange & Act
            var allExtensions = _service.GetInstalledExtensions().ToList();
            var uiExtensions = _service.GetInstalledUIExtensions().ToList();
            var libExtensions = _service.GetInstalledLibraryExtensions().ToList();

            // Assert
            // UI and lib extensions should be subsets of all extensions (compare by name since ParsedExtension doesn't implement equality)
            var allExtensionNames = allExtensions.Select(e => e.Name).ToHashSet();
            Assert.IsTrue(uiExtensions.All(e => allExtensionNames.Contains(e.Name)),
                "UI extensions should be a subset of all extensions");
            Assert.IsTrue(libExtensions.All(e => allExtensionNames.Contains(e.Name)),
                "Library extensions should be a subset of all extensions");
        }
    }
}

