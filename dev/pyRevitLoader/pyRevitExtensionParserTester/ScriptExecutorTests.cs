using System;
using PyRevitLoader;

namespace pyRevitExtensionParserTest
{
    /// <summary>
    /// Verifies ScriptExecutor setup guards its required host application handle.
    /// </summary>
    public class ScriptExecutorTests
    {
        [Test]
        /// <summary>
        /// Verifies a parameterless executor rejects environment setup.
        /// </summary>
        public void SetupEnvironment_WithoutUIApplication_ThrowsInvalidOperationException()
        {
            var executor = new ScriptExecutor();

            var exception = Assert.Throws<InvalidOperationException>(() =>
                executor.SetupEnvironment(null, null));

            Assert.That(exception.Message, Does.Contain("no UIApplication handle"));
        }
    }
}
