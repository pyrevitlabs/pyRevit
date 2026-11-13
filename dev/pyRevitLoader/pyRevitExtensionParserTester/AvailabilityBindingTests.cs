using NUnit.Framework;
using pyRevitAssemblyBuilder.UIManager.Buttons;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    [Category("HostFree")]
    [Category("Unit")]
    public class AvailabilityBindingTests
    {
        [TestCase("Cmd_abc", "doc-open", "Cmd_abc_avail")]
        [TestCase("Cmd_abc", "", "")]
        [TestCase("Cmd_abc", null, "")]
        public void ForContext_ReturnsEmptyWhenContextIsRemoved(string className, string? context, string expected)
        {
            Assert.That(AvailabilityBinding.ForContext(className, context), Is.EqualTo(expected));
        }

        [TestCase("Cmd_abc_avail", "Cmd_abc_avail")]
        [TestCase(null, "")]
        [TestCase("", "")]
        public void ForResolved_ReturnsEmptyWhenNoAvailabilityClass(string? resolved, string expected)
        {
            Assert.That(AvailabilityBinding.ForResolved(resolved), Is.EqualTo(expected));
        }

        [TestCase(null, "", false)]
        [TestCase("", "", false)]
        [TestCase("Cmd_abc_avail", "", true)]
        [TestCase("", "Cmd_abc_avail", true)]
        [TestCase(null, "Cmd_abc_avail", true)]
        [TestCase("Cmd_abc_avail", "Cmd_abc_avail", false)]
        public void NeedsUpdate_SkipsTheSetterWhenNothingChanges(string? current, string desired, bool expected)
        {
            Assert.That(AvailabilityBinding.NeedsUpdate(current, desired), Is.EqualTo(expected));
        }
    }
}
