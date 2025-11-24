using pyRevitAssemblyBuilder.AssemblyMaker;

namespace pyRevitExtensionParserTester
{
    /// <summary>
    /// Unit tests for AssemblyBuilderService.
    /// Note: These tests require Revit API mocking for full implementation.
    /// </summary>
    [TestFixture]
    public class AssemblyBuilderServiceTests
    {
        private AssemblyBuilderService _service;
        private const string TestRevitVersion = "2024";

        [SetUp]
        public void SetUp()
        {
            _service = new AssemblyBuilderService(TestRevitVersion, AssemblyBuildStrategy.ILPack);
        }

        [Test]
        public void Constructor_WithNullRevitVersion_ThrowsArgumentNullException()
        {
            // Act & Assert
            Assert.Throws<ArgumentNullException>(() => 
                new AssemblyBuilderService(null, AssemblyBuildStrategy.ILPack));
        }

        [Test]
        public void Constructor_WithValidParameters_CreatesInstance()
        {
            // Act
            var service = new AssemblyBuilderService(TestRevitVersion, AssemblyBuildStrategy.Roslyn);

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
}

