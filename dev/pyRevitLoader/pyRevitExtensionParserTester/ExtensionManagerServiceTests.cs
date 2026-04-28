using pyRevitAssemblyBuilder.SessionManager;
using pyRevitExtensionParser;
using System.Reflection;

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

        [Test]
        public void IsExtensionAllowed_CachesUnauthorizedExtensions()
        {
            var logger = new pyRevitExtensionParserTest.MockLogger();
            var service = new ExtensionManagerService(logger: logger);
            var extension = new ParsedExtension
            {
                Name = "UnauthorizedExtension",
                Directory = @"C:\extensions\unauthorized.extension",
                AuthorizedUsers = new List<string> { "someone_else" }
            };

            Assert.IsFalse(InvokeIsExtensionAllowed(service, extension));
            Assert.IsFalse(InvokeIsExtensionAllowed(service, extension));
            Assert.AreEqual(1, logger.Warnings.Count);
        }

        [Test]
        public void IsExtensionAllowed_UsesDirectoryAsCacheKey()
        {
            var service = new ExtensionManagerService();
            var currentUser = GetExpectedCurrentUser();

            var unauthorizedExtension = new ParsedExtension
            {
                Name = "SharedName",
                Directory = @"C:\extensions\shared-a.extension",
                AuthorizedUsers = new List<string> { "someone_else" }
            };

            var authorizedExtension = new ParsedExtension
            {
                Name = "SharedName",
                Directory = @"C:\extensions\shared-b.extension",
                AuthorizedUsers = new List<string> { currentUser }
            };

            Assert.IsFalse(InvokeIsExtensionAllowed(service, unauthorizedExtension));
            Assert.IsTrue(InvokeIsExtensionAllowed(service, authorizedExtension));
        }

        [Test]
        public void ClearParserCaches_ClearsAuthorizationDecisionCaches()
        {
            var service = new ExtensionManagerService();
            var extension = new ParsedExtension
            {
                Name = "MutableExtension",
                Directory = @"C:\extensions\mutable.extension",
                AuthorizedUsers = new List<string> { "someone_else" }
            };

            Assert.IsFalse(InvokeIsExtensionAllowed(service, extension));

            extension.AuthorizedUsers = new List<string> { GetExpectedCurrentUser() };
            service.ClearParserCaches();

            Assert.IsTrue(InvokeIsExtensionAllowed(service, extension));
        }

        private static bool InvokeIsExtensionAllowed(ExtensionManagerService service, ParsedExtension extension)
        {
            var method = typeof(ExtensionManagerService).GetMethod("IsExtensionAllowed", BindingFlags.Instance | BindingFlags.NonPublic);
            Assert.That(method, Is.Not.Null);

            return (bool)method!.Invoke(service, new object[] { extension })!;
        }

        private static string GetExpectedCurrentUser()
        {
            var userName = Environment.UserName;
            var atIndex = userName.IndexOf('@');
            if (atIndex > 0)
                userName = userName.Substring(0, atIndex);

            return userName.Replace(".", "");
        }
    }
}

