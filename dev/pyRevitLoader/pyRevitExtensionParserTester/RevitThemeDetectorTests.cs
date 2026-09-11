using pyRevitAssemblyBuilder.SessionManager;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    [NonParallelizable]
    public class RevitThemeDetectorTests
    {
        [SetUp]
        public void ClearThemeCacheBeforeTest() => RevitThemeDetector.ClearCache();

        [TearDown]
        public void ClearThemeCacheAfterTest() => RevitThemeDetector.ClearCache();

        [Test]
        public void DarkThemeNameIsDetectedRegardlessOfBaselineRevitVersion()
        {
            var detector = new RevitThemeDetector(new MockLogger(), () => "Dark");

            Assert.That(detector.IsDarkTheme(), Is.True);
            Assert.That(detector.GetThemeName(), Is.EqualTo("Dark"));
        }

        [Test]
        public void MissingThemeSupportFallsBackToLight()
        {
            var detector = new RevitThemeDetector(new MockLogger(), () => null);

            Assert.That(detector.IsDarkTheme(), Is.False);
            Assert.That(detector.GetThemeName(), Is.EqualTo("Light"));
        }

        [Test]
        public void ThemeReadFailureFallsBackToLightAndIsLogged()
        {
            var logger = new MockLogger();
            var detector = new RevitThemeDetector(
                logger,
                () => throw new InvalidOperationException("no theme api"));

            Assert.That(detector.IsDarkTheme(), Is.False);
            Assert.That(logger.Errors, Has.Count.EqualTo(1));
        }

        [Test]
        public void ThemeIsReadOnceUntilTheCacheIsCleared()
        {
            var reads = 0;
            var themeName = "Light";
            var detector = new RevitThemeDetector(
                new MockLogger(),
                () =>
                {
                    reads++;
                    return themeName;
                });

            Assert.That(detector.IsDarkTheme(), Is.False);
            themeName = "Dark";
            Assert.That(detector.IsDarkTheme(), Is.False);
            Assert.That(reads, Is.EqualTo(1));

            RevitThemeDetector.ClearCache();

            Assert.That(detector.IsDarkTheme(), Is.True);
            Assert.That(reads, Is.EqualTo(2));
        }

        [Test]
        public void ReadCurrentThemeNameReturnsNullWhenThemeManagerIsUnavailable()
        {
            Assert.That(RevitThemeDetector.ReadCurrentThemeName(typeof(string)), Is.Null);
            Assert.That(RevitThemeDetector.ReadCurrentThemeName(null), Is.Null);
        }
    }
}
