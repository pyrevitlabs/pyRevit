using NUnit.Framework;
using pyRevitAssemblyBuilder.UIManager.Buttons;

namespace pyRevitExtensionParserTest
{
    /// <summary>
    /// Regression tests for #4047: the availability class is only assigned when the button has a context, never an empty value that Revit rejects.
    /// </summary>
    [TestFixture]
    [Category("HostFree")]
    [Category("Unit")]
    public class AvailabilityBindingTests
    {
        [TestCase("Cmd_abc", "doc-open", "Cmd_abc_avail")]
        [TestCase("Cmd_abc", "", null)]
        [TestCase("Cmd_abc", null, null)]
        public void ForContext_ReturnsNullWhenThereIsNoContext(string className, string? context, string? expected)
        {
            Assert.That(AvailabilityBinding.ForContext(className, context), Is.EqualTo(expected));
        }
    }
}
