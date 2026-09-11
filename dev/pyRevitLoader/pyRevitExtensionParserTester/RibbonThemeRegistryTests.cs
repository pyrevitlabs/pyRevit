using pyRevitAssemblyBuilder.UIManager;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    [NonParallelizable]
    public class RibbonThemeRegistryTests
    {
        [SetUp]
        public void SetUp()
        {
            RibbonThemeRegistry.Clear();
        }

        [TearDown]
        public void TearDown()
        {
            RibbonThemeRegistry.Clear();
        }

        [Test]
        public void RefreshAllAppliesRequestedThemeWithoutReloadingSession()
        {
            var item = new object();
            var themes = new List<bool>();
            RibbonThemeRegistry.Register(item, themes.Add);

            RibbonThemeRegistry.RefreshAll(true);
            RibbonThemeRegistry.RefreshAll(false);

            Assert.That(themes, Is.EqualTo(new[] { true, false }));
        }

        [Test]
        public void RegisteringSameControlReplacesItsPreviousUpdater()
        {
            var item = new object();
            var firstCalls = 0;
            var secondCalls = 0;
            RibbonThemeRegistry.Register(item, _ => firstCalls++);
            RibbonThemeRegistry.Register(item, _ => secondCalls++);

            RibbonThemeRegistry.RefreshAll(true);

            Assert.That(RibbonThemeRegistry.Count, Is.EqualTo(1));
            Assert.That(firstCalls, Is.Zero);
            Assert.That(secondCalls, Is.EqualTo(1));
        }

        [Test]
        public void BrokenControlDoesNotPreventOtherIconsFromRefreshing()
        {
            var successfulCalls = 0;
            RibbonThemeRegistry.Register(new object(), _ => throw new InvalidOperationException());
            RibbonThemeRegistry.Register(new object(), _ => successfulCalls++);

            Assert.DoesNotThrow(() => RibbonThemeRegistry.RefreshAll(true));
            Assert.That(successfulCalls, Is.EqualTo(1));
        }
    }
}
