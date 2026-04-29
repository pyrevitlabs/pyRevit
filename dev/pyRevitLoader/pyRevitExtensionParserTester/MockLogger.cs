#nullable enable

using pyRevitAssemblyBuilder.SessionManager;

namespace pyRevitExtensionParserTest
{
    /// <summary>
    /// Mock logger for testing purposes that implements ILogger.
    /// Outputs messages to NUnit TestContext.Out for visibility during test execution.
    /// Stores warnings and errors in lists for test assertion.
    /// </summary>
    public class MockLogger : ILogger
    {
        public List<string> Warnings { get; } = new List<string>();
        public List<string> Errors { get; } = new List<string>();
        public List<string> Infos { get; } = new List<string>();
        public List<string> Debugs { get; } = new List<string>();

        public void Debug(string message)
        {
            Debugs.Add(message);
            TestContext.Out.WriteLine($"[DEBUG] {message}");
        }

        public void Info(string message)
        {
            Infos.Add(message);
            TestContext.Out.WriteLine($"[INFO] {message}");
        }

        public void Warning(string message)
        {
            Warnings.Add(message);
            TestContext.Out.WriteLine($"[WARN] {message}");
        }

        public void Error(string message)
        {
            Errors.Add(message);
            TestContext.Out.WriteLine($"[ERROR] {message}");
        }
    }
}
