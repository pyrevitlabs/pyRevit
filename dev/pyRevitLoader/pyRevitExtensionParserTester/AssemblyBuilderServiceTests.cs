using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitAssemblyBuilder.SessionManager;

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
        private ILogger _mockLogger;

        [SetUp]
        public void SetUp()
        {
            // Create a mock logger for tests
            _mockLogger = new MockPythonLogger();
            _service = new AssemblyBuilderService(TestRevitVersion, AssemblyBuildStrategy.Roslyn, _mockLogger);
        }

        [Test]
        public void Constructor_WithNullRevitVersion_ThrowsArgumentNullException()
        {
            // Act & Assert
            Assert.Throws<ArgumentNullException>(() => 
                new AssemblyBuilderService(null, AssemblyBuildStrategy.Roslyn, _mockLogger));
        }

        [Test]
        public void Constructor_WithValidParameters_CreatesInstance()
        {
            // Act
            var service = new AssemblyBuilderService(TestRevitVersion, AssemblyBuildStrategy.Roslyn, _mockLogger);

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
    /// Mock logger for testing purposes that implements ILogger.
    /// </summary>
    public class MockPythonLogger : ILogger
    {
        public void Debug(string message) { }
        public void Info(string message) { }
        public void Warning(string message) { }
        public void Error(string message) { }
    }
}

