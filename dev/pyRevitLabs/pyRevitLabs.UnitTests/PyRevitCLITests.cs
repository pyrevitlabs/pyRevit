using Microsoft.VisualStudio.TestTools.UnitTesting;
using System;
using System.IO;
using pyRevitCLI;

namespace pyRevitLabs.UnitTests
{
    [TestClass]
    public class PyRevitCLITests
    {
        [TestMethod]
        public void TestHelpMessageColors()
        {
            // Redirect console output to a StringWriter
            var stringWriter = new StringWriter();
            var originalOutput = Console.Out;
            Console.SetOut(stringWriter);

            try
            {
                // Call the method that prints the help message
                PyRevitCLIAppHelps.PrintHelp(PyRevitCLICommandType.Main, 0);
            }
            catch (Exception)
            {
                // The PrintHelp method calls Environment.Exit, which throws an exception in the test runner.
                // We can ignore this exception as we are only interested in the console output.
            }
            finally
            {
                // Restore the original console output
                Console.SetOut(originalOutput);
            }

            // Get the output
            var output = stringWriter.ToString();

            // Assert that the output contains color codes
            // This is a simple check to ensure that Colorful.Console is being used.
            // A more robust test would check for specific colors on specific parts of the text.
            Assert.IsTrue(output.Contains("\u001b["));
        }
    }
}
