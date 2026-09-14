using pyRevitAssemblyBuilder.UIManager.Panels;
using pyRevitExtensionParser;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class PanelBackgroundResolverTests
    {
        [Test]
        public void ResolveReturnsLightColorsInLightTheme()
        {
            var component = new ParsedComponent
            {
                PanelBackground = "#BB005591",
                TitleBackground = "#E2A000",
                SlideoutBackground = "#E25200",
                DarkPanelBackground = "#1E3A5F",
                DarkTitleBackground = "#7A5600",
                DarkSlideoutBackground = "#7A2C00",
            };

            var colors = PanelBackgroundResolver.Resolve(component, isDarkTheme: false);

            Assert.AreEqual("#BB005591", colors.Panel);
            Assert.AreEqual("#E2A000", colors.Title);
            Assert.AreEqual("#E25200", colors.Slideout);
        }

        [Test]
        public void ResolveReturnsDarkColorsInDarkTheme()
        {
            var component = new ParsedComponent
            {
                PanelBackground = "#BB005591",
                TitleBackground = "#E2A000",
                SlideoutBackground = "#E25200",
                DarkPanelBackground = "#1E3A5F",
                DarkTitleBackground = "#7A5600",
                DarkSlideoutBackground = "#7A2C00",
            };

            var colors = PanelBackgroundResolver.Resolve(component, isDarkTheme: true);

            Assert.AreEqual("#1E3A5F", colors.Panel);
            Assert.AreEqual("#7A5600", colors.Title);
            Assert.AreEqual("#7A2C00", colors.Slideout);
        }

        [Test]
        public void ResolveFallsBackPerAreaWhenDarkOverrideIsPartial()
        {
            var component = new ParsedComponent
            {
                PanelBackground = "#BB005591",
                TitleBackground = "#E2A000",
                SlideoutBackground = "#E25200",
                DarkTitleBackground = "#7A5600",
            };

            var colors = PanelBackgroundResolver.Resolve(component, isDarkTheme: true);

            Assert.AreEqual("#BB005591", colors.Panel, "Panel should fall back to the light color");
            Assert.AreEqual("#7A5600", colors.Title, "Title should use the dark override");
            Assert.AreEqual("#E25200", colors.Slideout, "Slideout should fall back to the light color");
        }

        [Test]
        public void ResolvePaintsNothingInLightThemeForDarkOnlyBundle()
        {
            var component = new ParsedComponent
            {
                DarkPanelBackground = "#1E3A5F",
            };

            var lightColors = PanelBackgroundResolver.Resolve(component, isDarkTheme: false);
            var darkColors = PanelBackgroundResolver.Resolve(component, isDarkTheme: true);

            Assert.IsTrue(lightColors.IsEmpty, "A dark-only bundle must not paint in light theme");
            Assert.AreEqual("#1E3A5F", darkColors.Panel);
        }

        [Test]
        public void HasBackgroundColorsDetectsDarkOnlyDeclarations()
        {
            var darkOnly = new ParsedComponent { DarkSlideoutBackground = "#7A2C00" };
            var none = new ParsedComponent();

            Assert.IsTrue(PanelBackgroundResolver.HasBackgroundColors(darkOnly));
            Assert.IsFalse(PanelBackgroundResolver.HasBackgroundColors(none));
            Assert.IsFalse(PanelBackgroundResolver.HasBackgroundColors(null));
        }
    }
}
