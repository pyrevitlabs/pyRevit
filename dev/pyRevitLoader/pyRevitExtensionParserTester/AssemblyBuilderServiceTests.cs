using pyRevitAssemblyBuilder.AssemblyMaker;

namespace pyRevitExtensionParserTester
{
    /// <summary>
    /// Unit tests for AssemblyBuilderService.
    /// </summary>
    [TestFixture]
    public class AssemblyBuilderServiceTests
    {
        private AssemblyBuilderService _service;
        private const string TestRevitVersion = "2024";
        private object _mockPythonLogger;

        [SetUp]
        public void SetUp()
        {
            // Create a mock python logger (can be null for tests or a mock object)
            _mockPythonLogger = new MockPythonLogger();
            _service = new AssemblyBuilderService(TestRevitVersion, AssemblyBuildStrategy.ILPack, _mockPythonLogger);
        }

        [Test]
        public void Constructor_WithNullRevitVersion_ThrowsArgumentNullException()
        {
            // Act & Assert
            Assert.Throws<ArgumentNullException>(() => 
                new AssemblyBuilderService(null, AssemblyBuildStrategy.ILPack, _mockPythonLogger));
        }

        [Test]
        public void Constructor_WithValidParameters_CreatesInstance()
        {
            // Act
            var service = new AssemblyBuilderService(TestRevitVersion, AssemblyBuildStrategy.Roslyn, _mockPythonLogger);

            // Assert
            Assert.IsNotNull(service);
        }

        [Test]
        public void BuildExtensionAssembly_WithNullExtension_ThrowsArgumentNullException()
        {
            // Act & Assert
            Assert.Throws<ArgumentNullException>(() => 
                _service.BuildExtensionAssembly(null));
        }

        // Note: Additional tests for BuildExtensionAssembly would require:
        // - Mock ParsedExtension objects
        // - Mock Revit API dependencies
        // - Test file system setup
        // These are complex integration tests that require significant setup.
    }

    /// <summary>
    /// Mock Python logger for testing purposes.
    /// </summary>
    public class MockPythonLogger
    {
        public void debug(string message) { }
        public void info(string message) { }
        public void warning(string message) { }
        public void error(string message) { }
    }
}

