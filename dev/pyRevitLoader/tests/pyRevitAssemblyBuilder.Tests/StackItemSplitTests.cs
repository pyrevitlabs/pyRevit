using System.Linq;
using NUnit.Framework;
using pyRevitAssemblyBuilder.UIManager;
using pyRevitAssemblyBuilder.UIManager.Builders;
using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    /// <summary>
    /// A stack's checkboxes always go to the checkbox stack builder, its other items to a Revit API
    /// stack or, when there is only one, onto the panel on their own, and the ribbon scanner tracks
    /// the stacked checkboxes by the ids the checkbox stack builder returns.
    /// </summary>
    [TestFixture]
    [Category("HostFree")]
    [Category("Unit")]
    public class StackItemSplitTests
    {
        [Test]
        public void Of_OneButtonAndASeparator_IsASingleItem()
        {
            var split = StackItemSplit.Of(new[] { Button("Align"), Separator() });

            Assert.That(split.IsSingleItem, Is.True);
            Assert.That(split.OtherItems.Select(Name), Is.EqualTo(new[] { "Align" }));
        }

        [Test]
        public void Of_OneCheckBox_GoesToTheCheckBoxStackBuilder()
        {
            var split = StackItemSplit.Of(new[] { CheckBox("Leader") });

            Assert.That(split.IsSingleItem, Is.False);
            Assert.That(split.CheckBoxes.Select(Name), Is.EqualTo(new[] { "Leader" }));
            Assert.That(split.LoneOtherItem, Is.Null);
            Assert.That(split.HasRevitApiStack, Is.False);
        }

        [Test]
        public void Of_CheckBoxesAndOneButton_BuildsTheButtonOnItsOwn()
        {
            var align = Button("Align");

            var split = StackItemSplit.Of(new[] { CheckBox("Leader"), align, CheckBox("Shoulder") });

            Assert.That(split.IsMixed, Is.True);
            Assert.That(split.LoneOtherItem, Is.SameAs(align));
            Assert.That(split.HasRevitApiStack, Is.False);
            Assert.That(split.CheckBoxes.Select(Name), Is.EqualTo(new[] { "Leader", "Shoulder" }));
        }

        [Test]
        public void Of_CheckBoxAndTwoButtons_StacksTheButtonsWithoutTheCheckBox()
        {
            var split = StackItemSplit.Of(new[] { Button("Align"), CheckBox("Leader"), Button("Distribute") });

            Assert.That(split.IsMixed, Is.True);
            Assert.That(split.HasRevitApiStack, Is.True);
            Assert.That(split.LoneOtherItem, Is.Null);
            Assert.That(split.OtherItems.Select(Name), Is.EqualTo(new[] { "Align", "Distribute" }));
            Assert.That(split.CheckBoxes.Select(Name), Is.EqualTo(new[] { "Leader" }));
        }

        [Test]
        public void Of_ButtonsOnly_IsNotMixed()
        {
            var split = StackItemSplit.Of(new[] { Button("Align"), Separator(), Button("Distribute") });

            Assert.That(split.IsMixed, Is.False);
            Assert.That(split.HasRevitApiStack, Is.True);
            Assert.That(split.CheckBoxes, Is.Empty);
        }

        [Test]
        public void ScannerKeys_MarksTheCheckBoxesByIdAndTheOtherItemsByName()
        {
            var split = StackItemSplit.Of(new[] { Button("Align"), CheckBox("Leader"), Button("Distribute") });
            var leaderId = CheckBoxControlIds.ForStackedCheckBox("Annotate", "Leaders", "Options", "Leader");

            var keys = split.ScannerKeys(new[] { leaderId });

            Assert.That(keys, Is.EquivalentTo(new[] { "Align", "Distribute", leaderId }));
        }

        [Test]
        public void ScannerKeys_CheckBoxTheBuilderDidNotShow_IsNotMarked()
        {
            var split = StackItemSplit.Of(new[] { CheckBox("A"), CheckBox("B"), CheckBox("C"), CheckBox("D") });
            var shownIds = new[] { "id-A", "id-B", "id-C" };

            var keys = split.ScannerKeys(shownIds);

            Assert.That(keys, Is.EquivalentTo(shownIds));
        }

        private static string Name(ParsedComponent component)
        {
            return component.DisplayName;
        }

        private static ParsedComponent Button(string name)
        {
            return Component(name, CommandComponentType.PushButton);
        }

        private static ParsedComponent CheckBox(string name)
        {
            return Component(name, CommandComponentType.CheckBox);
        }

        private static ParsedComponent Separator()
        {
            return Component("---", CommandComponentType.Separator);
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
