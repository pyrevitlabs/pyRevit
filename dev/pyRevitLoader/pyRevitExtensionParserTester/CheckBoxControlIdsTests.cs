using NUnit.Framework;
using pyRevitAssemblyBuilder.UIManager.Builders;

namespace pyRevitExtensionParserTest
{
    /// <summary>
    /// The AdWindows ids of checkbox controls keep checkboxes that share a name apart, so reloads and
    /// the ribbon scanner find each control again.
    /// </summary>
    [TestFixture]
    [Category("HostFree")]
    [Category("Unit")]
    public class CheckBoxControlIdsTests
    {
        private const string TabName = "Annotate";
        private const string PanelName = "Leaders";

        [Test]
        public void ForCheckBox_NamesTheTabPanelAndCheckBox()
        {
            Assert.That(
                CheckBoxControlIds.ForCheckBox(TabName, PanelName, "Leader"),
                Is.EqualTo("pyRevitCheckBox%Annotate%Leaders%Leader"));
        }

        [Test]
        public void ForStackedCheckBox_AlsoNamesTheStack()
        {
            Assert.That(
                CheckBoxControlIds.ForStackedCheckBox(TabName, PanelName, "Options", "Leader"),
                Is.EqualTo("pyRevitCheckBox%Annotate%Leaders%Options%Leader"));
        }

        [Test]
        public void ForStack_NamesTheTabPanelAndStack()
        {
            Assert.That(
                CheckBoxControlIds.ForStack(TabName, PanelName, "Options"),
                Is.EqualTo("pyRevitCheckBoxStack%Annotate%Leaders%Options"));
        }

        [Test]
        public void StandaloneAndStackedCheckBoxWithTheSameName_GetDifferentIds()
        {
            Assert.That(
                CheckBoxControlIds.ForStackedCheckBox(TabName, PanelName, "Options", "Leader"),
                Is.Not.EqualTo(CheckBoxControlIds.ForCheckBox(TabName, PanelName, "Leader")));
        }

        [Test]
        public void CheckBoxesWithTheSameNameInTwoStacks_GetDifferentIds()
        {
            Assert.That(
                CheckBoxControlIds.ForStackedCheckBox(TabName, PanelName, "Options", "Leader"),
                Is.Not.EqualTo(CheckBoxControlIds.ForStackedCheckBox(TabName, PanelName, "Extras", "Leader")));
        }

        [Test]
        public void ForStack_DiffersFromTheIdOfACheckBoxNamedLikeTheStack()
        {
            Assert.That(
                CheckBoxControlIds.ForStack(TabName, PanelName, "Options"),
                Is.Not.EqualTo(CheckBoxControlIds.ForCheckBox(TabName, PanelName, "Options")));
        }
    }
}
