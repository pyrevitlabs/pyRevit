using System.IO;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class DiagnosticTests
    {
        [Test]
        public void DiagnosticPathTest()
        {
            TestContext.Out.WriteLine("=== Diagnostic Path Information ===");
            TestContext.Out.WriteLine($"Current Directory: {Directory.GetCurrentDirectory()}");
            TestContext.Out.WriteLine($"Test Directory: {TestContext.CurrentContext.TestDirectory}");
            
            // Check if Resources directory exists in various locations
            var currentDirResources = Path.Combine(Directory.GetCurrentDirectory(), "Resources");
            var testDirResources = Path.Combine(TestContext.CurrentContext.TestDirectory, "Resources");
            
            TestContext.Out.WriteLine($"Resources in current dir: {Directory.Exists(currentDirResources)}");
            TestContext.Out.WriteLine($"Resources in test dir: {Directory.Exists(testDirResources)}");
            
            if (Directory.Exists(currentDirResources))
            {
                TestContext.Out.WriteLine("Files in current dir Resources:");
                var files = Directory.GetFiles(currentDirResources, "*", SearchOption.AllDirectories);
                foreach (var file in files.Take(10)) // Limit output
                {
                    TestContext.Out.WriteLine($"  {file}");
                }
            }
            
            if (Directory.Exists(testDirResources))
            {
                TestContext.Out.WriteLine("Files in test dir Resources:");
                var files = Directory.GetFiles(testDirResources, "*", SearchOption.AllDirectories);
                foreach (var file in files.Take(10)) // Limit output
                {
                    TestContext.Out.WriteLine($"  {file}");
                }
            }
            
            Assert.Pass("Diagnostic completed");
        }
    }
}