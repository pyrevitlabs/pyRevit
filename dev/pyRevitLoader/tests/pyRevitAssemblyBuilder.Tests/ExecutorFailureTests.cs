#nullable enable
using NUnit.Framework;
using pyRevitAssemblyBuilder.UIManager;
using pyRevitLoader.Tests.TestSupport;

namespace pyRevitAssemblyBuilder.Tests
{
    [TestFixture]
    [Category("HostFree")]
    [Category("Unit")]
    public class ExecutorFailureTests
    {
        private sealed class FakeExecutor
        {
            public string? Message { get; set; }
        }

        private sealed class ExecutorWithoutMessage
        {
        }

        [Test]
        public void ReportIfFailed_MessageSet_LogsOneErrorNamingTheBundle()
        {
            var logger = new MockLogger();
            var executor = new FakeExecutor { Message = "unexpected token ':'" };

            ExecutorFailure.ReportIfFailed(executor, "SmartButton", "BrokenSmart", logger);

            Assert.That(logger.Errors, Has.Count.EqualTo(1));
            Assert.That(logger.Errors[0], Does.Contain("SmartButton 'BrokenSmart'"));
            Assert.That(logger.Errors[0], Does.Contain("unexpected token ':'"));
        }

        [TestCase(null)]
        [TestCase("")]
        public void ReportIfFailed_NoMessage_LogsNothing(string? message)
        {
            var logger = new MockLogger();

            ExecutorFailure.ReportIfFailed(new FakeExecutor { Message = message }, "ComboBox", "Fine", logger);

            Assert.That(logger.Errors, Is.Empty);
        }

        [Test]
        public void ReportIfFailed_ExecutorWithoutMessageProperty_LogsNothing()
        {
            var logger = new MockLogger();

            ExecutorFailure.ReportIfFailed(new ExecutorWithoutMessage(), "CheckBox", "Fine", logger);

            Assert.That(logger.Errors, Is.Empty);
        }
    }
}
