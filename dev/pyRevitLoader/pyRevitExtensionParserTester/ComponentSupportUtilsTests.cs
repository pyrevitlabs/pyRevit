#nullable enable

using System.Collections.Generic;
using NUnit.Framework;
using pyRevitAssemblyBuilder.UIManager;
using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class ComponentSupportUtilsTests
    {
        private readonly MockLogger _logger = new MockLogger();

        [SetUp]
        public void SetUp()
        {
            _logger.Debugs.Clear();
            _logger.Infos.Clear();
            _logger.Warnings.Clear();
            _logger.Errors.Clear();
        }

        [Test]
        public void IsSupported_HidesBetaComponent_WhenLoadBetaIsDisabled()
        {
            var component = CreateComponent("BetaTool", CommandComponentType.PushButton, isBeta: true);

            var isSupported = ComponentSupportUtils.IsSupported(component, "2025", loadBeta: false, _logger);

            Assert.IsFalse(isSupported, "Beta component should be hidden when beta tools are disabled.");
        }

        [Test]
        public void IsSupported_HidesVersionIncompatibleComponent()
        {
            var component = CreateComponent(
                "FutureTool",
                CommandComponentType.PushButton,
                minRevitVersion: "2026");

            var isSupported = ComponentSupportUtils.IsSupported(component, "2025", loadBeta: true, _logger);

            Assert.IsFalse(isSupported, "Component should be hidden when the current Revit version is below min_revit_version.");
        }

        [Test]
        public void GetVisibleButtonGroupChildren_RemovesHiddenButtonsAndOrphanSeparators()
        {
            var children = new List<ParsedComponent>
            {
                CreateComponent("VisibleOne", CommandComponentType.PushButton),
                CreateSeparator(),
                CreateComponent("BetaOnly", CommandComponentType.PushButton, isBeta: true),
                CreateSeparator(),
                CreateComponent("VisibleTwo", CommandComponentType.PushButton)
            };

            var visibleChildren = ComponentSupportUtils.GetVisibleButtonGroupChildren(
                children,
                "2025",
                loadBeta: false,
                _logger);

            Assert.That(visibleChildren.Count, Is.EqualTo(3), "Only visible buttons and the separator between them should remain.");
            Assert.That(visibleChildren[0].DisplayName, Is.EqualTo("VisibleOne"));
            Assert.That(visibleChildren[1].Type, Is.EqualTo(CommandComponentType.Separator));
            Assert.That(visibleChildren[2].DisplayName, Is.EqualTo("VisibleTwo"));
        }

        [Test]
        public void HasVisibleButtonGroupChildren_ReturnsFalse_WhenAllChildrenAreFilteredOut()
        {
            var group = CreateComponent("GroupedTools", CommandComponentType.PullDown);
            group.Children = new List<ParsedComponent>
            {
                CreateComponent("BetaOnly", CommandComponentType.PushButton, isBeta: true)
            };

            var hasVisibleChildren = ComponentSupportUtils.HasVisibleButtonGroupChildren(
                group,
                "2025",
                loadBeta: false,
                _logger);

            Assert.IsFalse(hasVisibleChildren, "Pulldown should be considered empty when all child commands are filtered out.");
        }

        [Test]
        public void HasVisibleButtonGroupChildren_ReturnsTrue_WithSingleVisibleChild()
        {
            var group = CreateComponent("GroupedTools", CommandComponentType.PullDown);
            group.Children = new List<ParsedComponent>
            {
                CreateSeparator(),
                CreateComponent("OnlyVisible", CommandComponentType.PushButton),
                CreateSeparator()
            };

            var hasVisibleChildren = ComponentSupportUtils.HasVisibleButtonGroupChildren(
                group,
                "2025",
                loadBeta: false,
                _logger);

            Assert.IsTrue(hasVisibleChildren, "Pulldown with at least one supported non-separator child should be visible.");
        }

        [Test]
        public void IsSupported_HidesComponentAboveMaxRevitVersion()
        {
            var component = CreateComponent(
                "LegacyTool",
                CommandComponentType.PushButton,
                maxRevitVersion: "2024");

            var isSupported = ComponentSupportUtils.IsSupported(component, "2025", loadBeta: true, _logger);

            Assert.IsFalse(isSupported, "Component should be hidden when the current Revit version is above max_revit_version.");
        }

        [Test]
        public void GetVisibleButtonGroupChildren_DropsLeadingAndTrailingSeparators()
        {
            var children = new List<ParsedComponent>
            {
                CreateSeparator(),
                CreateComponent("VisibleOne", CommandComponentType.PushButton),
                CreateSeparator(),
                CreateSeparator(),
                CreateComponent("VisibleTwo", CommandComponentType.PushButton),
                CreateSeparator()
            };

            var visibleChildren = ComponentSupportUtils.GetVisibleButtonGroupChildren(
                children,
                "2025",
                loadBeta: false,
                _logger);

            Assert.That(visibleChildren.Count, Is.EqualTo(3), "Leading and trailing separators should be dropped; consecutive separators collapse.");
            Assert.That(visibleChildren[0].DisplayName, Is.EqualTo("VisibleOne"));
            Assert.That(visibleChildren[1].Type, Is.EqualTo(CommandComponentType.Separator));
            Assert.That(visibleChildren[2].DisplayName, Is.EqualTo("VisibleTwo"));
        }

        [Test]
        public void GetVisibleButtonGroupChildren_ReturnsEmpty_WhenChildrenIsNull()
        {
            var visibleChildren = ComponentSupportUtils.GetVisibleButtonGroupChildren(
                children: null,
                "2025",
                loadBeta: false,
                _logger);

            Assert.That(visibleChildren, Is.Empty);
        }

        [Test]
        public void IsStackChildVisible_ReturnsFalse_ForPulldownWithAllChildrenFilteredOut()
        {
            var pulldown = CreateComponent("EmptyPulldown", CommandComponentType.PullDown);
            pulldown.Children = new List<ParsedComponent>
            {
                CreateComponent("BetaOnly", CommandComponentType.PushButton, isBeta: true)
            };

            var isVisible = ComponentSupportUtils.IsStackChildVisible(pulldown, "2025", loadBeta: false, _logger);

            Assert.IsFalse(isVisible, "A pulldown stack child with no visible commands should not be shown.");
        }

        [Test]
        public void IsStackChildVisible_ReturnsTrue_ForPushButtonIgnoringChildren()
        {
            var pushButton = CreateComponent("Normal", CommandComponentType.PushButton);

            var isVisible = ComponentSupportUtils.IsStackChildVisible(pushButton, "2025", loadBeta: false, _logger);

            Assert.IsTrue(isVisible);
        }

        [TestCase("2025", ExpectedResult = 2025)]
        [TestCase("20", ExpectedResult = 2020)]
        [TestCase("99", ExpectedResult = 2099)]
        [TestCase("v2025.1", ExpectedResult = 20251)]
        [TestCase("", ExpectedResult = 0)]
        [TestCase("abc", ExpectedResult = 0)]
        public int NormalizeVersionNumber_HandlesExpectedFormats(string input)
        {
            return ComponentSupportUtils.NormalizeVersionNumber(input);
        }

        private static ParsedComponent CreateComponent(
            string displayName,
            CommandComponentType type,
            bool isBeta = false,
            string? minRevitVersion = null,
            string? maxRevitVersion = null)
        {
            return new ParsedComponent
            {
                Name = displayName,
                DisplayName = displayName,
                Type = type,
                IsBeta = isBeta,
                MinRevitVersion = minRevitVersion,
                MaxRevitVersion = maxRevitVersion,
                Directory = @"C:\test"
            };
        }

        private static ParsedComponent CreateSeparator()
        {
            return new ParsedComponent
            {
                Name = "---",
                DisplayName = "---",
                Type = CommandComponentType.Separator,
                Directory = @"C:\test"
            };
        }
    }
}
