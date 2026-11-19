using System.Collections.Generic;
using System.Linq;
using System.Runtime.InteropServices;
using System.Threading;
using Autodesk.Windows;
using NUnit.Framework;
using pyRevitAssemblyBuilder.UIManager.Builders;
using pyRevitAssemblyBuilder.UIManager.Panels;
using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    /// <summary>
    /// The checkbox builder adds AdWindows checkboxes and checkbox stacks, finds them again on a
    /// reload instead of adding more, and hides the stacked rows a reload no longer shows.
    /// </summary>
    /// <remarks>
    /// Runs the AdWindows.dll of an installed Revit, so it is tagged Revit and CI never selects it.
    /// The fixture is ignored when no installed Revit has an AdWindows.dll for the runtime the tests
    /// run on; see the project README.
    /// </remarks>
    [TestFixture]
    [Category("Revit")]
    [Category("Integration")]
    [Apartment(ApartmentState.STA)]
    [NonParallelizable]
    public class CheckBoxBuilderAdWindowsTests
    {
        private const string TabName = "Annotate";
        private const string PanelName = "Leaders";
        private const string StackName = "Options";

        private string _adWindowsPath = string.Empty;
        private MockLogger _logger = null!;
        private CheckBoxBuilder _builder = null!;
        private RibbonPanelSource _panel = null!;

        [OneTimeSetUp]
        public void LoadInstalledAdWindows()
        {
            var adWindowsPath = InstalledAdWindows.Register();
            if (adWindowsPath == null)
                Assert.Ignore($"No installed Revit has an AdWindows.dll that runs on {RuntimeInformation.FrameworkDescription}.");

            _adWindowsPath = adWindowsPath;
        }

        [OneTimeTearDown]
        public void StopResolvingAdWindows()
        {
            InstalledAdWindows.Unregister();
        }

        [SetUp]
        public void SetUp()
        {
            TestContext.Out.WriteLine($"AdWindows: {_adWindowsPath} on {RuntimeInformation.FrameworkDescription}");
            _logger = new MockLogger();
            _builder = new CheckBoxBuilder(_logger, new PanelStyleManager(_logger));
            _panel = new RibbonPanelSource();
        }

        [Test]
        public void CreateOrUpdateCheckBox_AddsACheckBoxAndReturnsItsId()
        {
            var id = _builder.CreateOrUpdateCheckBox(CheckBox("Leader", isChecked: true), _panel, PanelName, TabName);

            var checkBox = _panel.Items.OfType<RibbonCheckBox>().Single();
            Assert.That(id, Is.EqualTo(CheckBoxControlIds.ForCheckBox(TabName, PanelName, "Leader")));
            Assert.That(checkBox.Id, Is.EqualTo(id));
            Assert.That(checkBox.Text, Is.EqualTo("Leader"));
            Assert.That(checkBox.IsChecked, Is.True);
        }

        [Test]
        public void CreateOrUpdateCheckBox_Reload_RefreshesTheSameControlAndKeepsItsState()
        {
            _builder.CreateOrUpdateCheckBox(CheckBox("Leader", isChecked: true), _panel, PanelName, TabName);
            var checkBox = _panel.Items.OfType<RibbonCheckBox>().Single();
            checkBox.IsChecked = false;

            _builder.CreateOrUpdateCheckBox(CheckBox("Leader", isChecked: true, title: "Leader Lines"), _panel, PanelName, TabName);

            Assert.That(_panel.Items.Single(), Is.SameAs(checkBox));
            Assert.That(checkBox.Text, Is.EqualTo("Leader Lines"));
            Assert.That(checkBox.IsChecked, Is.False);
        }

        [Test]
        public void CreateOrUpdateCheckBoxStack_PutsEachCheckBoxOnItsOwnRowAndReturnsTheirIds()
        {
            var ids = _builder.CreateOrUpdateCheckBoxStack(Stack(), CheckBoxes("Leader", "Shoulder"), _panel, PanelName, TabName);

            var rowPanel = _panel.Items.OfType<RibbonRowPanel>().Single();
            Assert.That(rowPanel.Id, Is.EqualTo(CheckBoxControlIds.ForStack(TabName, PanelName, StackName)));
            Assert.That(rowPanel.Items[0], Is.InstanceOf<RibbonCheckBox>());
            Assert.That(rowPanel.Items[1], Is.InstanceOf<RibbonRowBreak>());
            Assert.That(rowPanel.Items[2], Is.InstanceOf<RibbonCheckBox>());
            Assert.That(ShownRowIds(), Is.EqualTo(StackedIds("Leader", "Shoulder")));
            Assert.That(ids, Is.EquivalentTo(StackedIds("Leader", "Shoulder")));
        }

        [Test]
        public void CreateOrUpdateCheckBoxStack_FourCheckBoxes_ShowsAndReturnsTheFirstThree()
        {
            var ids = _builder.CreateOrUpdateCheckBoxStack(Stack(), CheckBoxes("A", "B", "C", "D"), _panel, PanelName, TabName);

            Assert.That(ShownRowIds(), Is.EqualTo(StackedIds("A", "B", "C")));
            Assert.That(ids, Is.EquivalentTo(StackedIds("A", "B", "C")));
            Assert.That(_logger.Warnings.Count(warning => warning.Contains("only the first 3")), Is.EqualTo(1));
        }

        [Test]
        public void CreateOrUpdateCheckBoxStack_Reload_ReusesTheRowPanelAndItsCheckBoxes()
        {
            _builder.CreateOrUpdateCheckBoxStack(Stack(), CheckBoxes("Leader", "Shoulder"), _panel, PanelName, TabName);
            var rowPanel = _panel.Items.OfType<RibbonRowPanel>().Single();
            var leader = StackedCheckBox("Leader");
            var shoulder = StackedCheckBox("Shoulder");

            _builder.CreateOrUpdateCheckBoxStack(Stack(), CheckBoxes("Leader", "Shoulder"), _panel, PanelName, TabName);

            Assert.That(_panel.Items.Single(), Is.SameAs(rowPanel));
            Assert.That(rowPanel.Items.Count, Is.EqualTo(3));
            Assert.That(StackedCheckBox("Leader"), Is.SameAs(leader));
            Assert.That(StackedCheckBox("Shoulder"), Is.SameAs(shoulder));
        }

        [Test]
        public void CreateOrUpdateCheckBoxStack_CheckBoxPushedPastTheThirdRow_IsHiddenOnReload()
        {
            _builder.CreateOrUpdateCheckBoxStack(Stack(), CheckBoxes("A", "B", "C"), _panel, PanelName, TabName);

            var ids = _builder.CreateOrUpdateCheckBoxStack(Stack(), CheckBoxes("New", "A", "B", "C"), _panel, PanelName, TabName);

            Assert.That(ids, Is.EquivalentTo(StackedIds("New", "A", "B")));
            Assert.That(ShownRowIds(), Is.EquivalentTo(StackedIds("New", "A", "B")));
            Assert.That(StackedCheckBox("C").IsVisible, Is.False);
            Assert.That(StackedCheckBox("C").IsEnabled, Is.False);
        }

        [Test]
        public void CreateOrUpdateCheckBoxStack_CheckBoxRemovedFromTheStack_IsHiddenOnReload()
        {
            _builder.CreateOrUpdateCheckBoxStack(Stack(), CheckBoxes("Leader", "Shoulder"), _panel, PanelName, TabName);

            var ids = _builder.CreateOrUpdateCheckBoxStack(Stack(), CheckBoxes("Leader"), _panel, PanelName, TabName);

            Assert.That(ids, Is.EquivalentTo(StackedIds("Leader")));
            Assert.That(ShownRowIds(), Is.EqualTo(StackedIds("Leader")));
            Assert.That(StackedCheckBox("Shoulder").IsVisible, Is.False);
            Assert.That(StackedCheckBox("Shoulder").IsEnabled, Is.False);
        }

        [Test]
        public void StandaloneAndStackedCheckBoxWithTheSameName_KeepTheirOwnControlsAcrossReloads()
        {
            _builder.CreateOrUpdateCheckBoxStack(Stack(), CheckBoxes("Leader"), _panel, PanelName, TabName);

            _builder.CreateOrUpdateCheckBox(CheckBox("Leader"), _panel, PanelName, TabName);
            _builder.CreateOrUpdateCheckBox(CheckBox("Leader"), _panel, PanelName, TabName);

            var standalone = _panel.Items.OfType<RibbonCheckBox>().Single();
            Assert.That(standalone.Id, Is.EqualTo(CheckBoxControlIds.ForCheckBox(TabName, PanelName, "Leader")));
            Assert.That(ShownRowIds(), Is.EqualTo(StackedIds("Leader")));
        }

        private RibbonCheckBox StackedCheckBox(string name)
        {
            var id = CheckBoxControlIds.ForStackedCheckBox(TabName, PanelName, StackName, name);
            return RowPanelCheckBoxes().Single(checkBox => checkBox.Id == id);
        }

        private List<string> ShownRowIds()
        {
            return RowPanelCheckBoxes()
                .Where(checkBox => checkBox.IsVisible)
                .Select(checkBox => checkBox.Id)
                .ToList();
        }

        private IEnumerable<RibbonCheckBox> RowPanelCheckBoxes()
        {
            return _panel.Items.OfType<RibbonRowPanel>().Single().Items.OfType<RibbonCheckBox>();
        }

        private static List<string> StackedIds(params string[] names)
        {
            return names
                .Select(name => CheckBoxControlIds.ForStackedCheckBox(TabName, PanelName, StackName, name))
                .ToList();
        }

        private static ParsedComponent Stack()
        {
            return new ParsedComponent
            {
                Name = StackName,
                DisplayName = StackName,
                Type = CommandComponentType.Stack
            };
        }

        private static List<ParsedComponent> CheckBoxes(params string[] names)
        {
            return names.Select(name => CheckBox(name)).ToList();
        }

        private static ParsedComponent CheckBox(string name, bool isChecked = false, string? title = null)
        {
            return new ParsedComponent
            {
                Name = name,
                DisplayName = name,
                Title = title,
                Type = CommandComponentType.CheckBox,
                IsChecked = isChecked
            };
        }
    }
}
