using pyRevitAssemblyBuilder.UIManager.Icons;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    [NonParallelizable]
    public class RibbonIconRegistryTests
    {
        [SetUp]
        public void SetUp()
        {
            RibbonIconRegistry.Clear();
        }

        [TearDown]
        public void TearDown()
        {
            RibbonIconRegistry.Clear();
        }

        [Test]
        public void RefreshAllAppliesRequestedThemeWithoutReloadingSession()
        {
            var item = new object();
            var themes = new List<bool>();
            RibbonIconRegistry.Register(item, themes.Add);

            RibbonIconRegistry.RefreshAll(true);
            RibbonIconRegistry.RefreshAll(false);

            Assert.That(themes, Is.EqualTo(new[] { true, false }));
        }

        [Test]
        public void RegisteringSameControlReplacesItsPreviousUpdater()
        {
            var item = new object();
            var firstCalls = 0;
            var secondCalls = 0;
            RibbonIconRegistry.Register(item, _ => firstCalls++);
            RibbonIconRegistry.Register(item, _ => secondCalls++);

            RibbonIconRegistry.RefreshAll(true);

            Assert.That(RibbonIconRegistry.Count, Is.EqualTo(1));
            Assert.That(firstCalls, Is.Zero);
            Assert.That(secondCalls, Is.EqualTo(1));
        }

        [Test]
        public void BrokenControlDoesNotPreventOtherIconsFromRefreshing()
        {
            var successfulCalls = 0;
            RibbonIconRegistry.Register(new object(), _ => throw new InvalidOperationException());
            RibbonIconRegistry.Register(new object(), _ => successfulCalls++);

            Assert.DoesNotThrow(() => RibbonIconRegistry.RefreshAll(true));
            Assert.That(successfulCalls, Is.EqualTo(1));
        }
    }
}
