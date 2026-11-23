using System.Linq;
using NUnit.Framework;
using pyRevitAssemblyBuilder.UIManager;
using pyRevitAssemblyBuilder.UIManager.Builders;
using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    /// <summary>
    /// The ribbon scanner keys a checkbox by its full id and every other item by the last segment of
    /// its id, which are the keys the UI manager marks as touched, so a reload hides only the items it
    /// did not build.
    /// </summary>
    [TestFixture]
    [Category("HostFree")]
    [Category("Unit")]
    public class RibbonScannerTests
    {
        private const string TabName = "Annotate";
        private const string PanelName = "Leaders";

        [Test]
        public void GetButtonIdentifier_CheckBox_IsItsFullId()
        {
            var id = CheckBoxControlIds.ForCheckBox(TabName, PanelName, "Leader");

            Assert.That(RibbonScanner.GetButtonIdentifier(id, isCheckBox: true, automationName: "Leader"), Is.EqualTo(id));
        }

        [Test]
        public void GetButtonIdentifier_StandaloneAndStackedCheckBoxWithTheSameName_GetDifferentKeys()
        {
            var standaloneId = CheckBoxControlIds.ForCheckBox(TabName, PanelName, "Leader");
            var stackedId = CheckBoxControlIds.ForStackedCheckBox(TabName, PanelName, "Options", "Leader");

            Assert.That(
                RibbonScanner.GetButtonIdentifier(stackedId, isCheckBox: true, automationName: "Leader"),
                Is.Not.EqualTo(RibbonScanner.GetButtonIdentifier(standaloneId, isCheckBox: true, automationName: "Leader")));
        }

        [Test]
        public void GetButtonIdentifier_Button_IsTheLastIdSegment()
        {
            Assert.That(
                RibbonScanner.GetButtonIdentifier("CustomCtrl_%CustomCtrl_%Annotate%Leaders%Align", isCheckBox: false, automationName: "Align Text"),
                Is.EqualTo("Align"));
        }

        [Test]
        public void GetButtonIdentifier_ButtonIdWithoutSegments_IsTheWholeId()
        {
            Assert.That(RibbonScanner.GetButtonIdentifier("Align", isCheckBox: false, automationName: "Align Text"), Is.EqualTo("Align"));
        }

        [TestCase(null, true)]
        [TestCase("", true)]
        [TestCase(null, false)]
        public void GetButtonIdentifier_NoId_IsTheAutomationName(string? id, bool isCheckBox)
        {
            Assert.That(RibbonScanner.GetButtonIdentifier(id, isCheckBox, automationName: "Leader"), Is.EqualTo("Leader"));
        }

        [Test]
        public void GetButtonIdentifier_StackedItems_MatchTheKeysTheirStackMarks()
        {
            var stackItems = StackItemSplit.Of(new[]
            {
                Component("Align", CommandComponentType.PushButton),
                Component("Distribute", CommandComponentType.PushButton),
                Component("Leader", CommandComponentType.CheckBox)
            });
            var leaderId = CheckBoxControlIds.ForStackedCheckBox(TabName, PanelName, "Options", "Leader");
            var markedKeys = stackItems.ScannerKeys(new[] { leaderId }).ToList();

            var scannedKeys = new[]
            {
                RibbonScanner.GetButtonIdentifier("CustomCtrl_%CustomCtrl_%Annotate%Leaders%Align", isCheckBox: false, automationName: "Align"),
                RibbonScanner.GetButtonIdentifier("CustomCtrl_%CustomCtrl_%Annotate%Leaders%Distribute", isCheckBox: false, automationName: "Distribute"),
                RibbonScanner.GetButtonIdentifier(leaderId, isCheckBox: true, automationName: "Leader")
            };

            Assert.That(scannedKeys, Is.EquivalentTo(markedKeys));
        }

        private static ParsedComponent Component(string name, CommandComponentType type)
        {
            return new ParsedComponent
            {
                Name = name,
                DisplayName = name,
                Type = type
            };
        }
    }
}
