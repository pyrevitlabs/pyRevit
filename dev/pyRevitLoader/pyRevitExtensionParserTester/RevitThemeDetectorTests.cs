using pyRevitAssemblyBuilder.SessionManager;

namespace pyRevitExtensionParserTest
{
    /// <summary>
    /// Verifies theme detection independently of the Revit API version available at compile time.
    /// </summary>
    [TestFixture]
    [NonParallelizable]
    public class RevitThemeDetectorTests
    {
        [SetUp]
        public void ClearThemeCacheBeforeTest() => RevitThemeDetector.ClearCache();

        [TearDown]
        public void ClearThemeCacheAfterTest() => RevitThemeDetector.ClearCache();

        /// <summary>
        /// Confirms that a dark theme is returned by the detector.
        /// </summary>
        [Test]
        public void DarkThemeNameIsDetectedRegardlessOfBaselineRevitVersion()
        {
            var detector = new RevitThemeDetector(new MockLogger(), () => "Dark");

            Assert.That(detector.IsDarkTheme(), Is.True);
            Assert.That(detector.GetThemeName(), Is.EqualTo("Dark"));
        }

        /// <summary>
        /// Confirms that Revit 2021-2023 always uses light icons regardless of the API-reported theme.
        /// </summary>
        [Test]
        [TestCase(2021)]
        [TestCase(2022)]
        [TestCase(2023)]
        public void Pre2024RevitYearsAlwaysReportLightTheme(int revitYear)
        {
            var detector = new RevitThemeDetector(new MockLogger(), () => "Dark", revitYear);

            Assert.That(detector.IsDarkTheme(), Is.False,
                $"Revit {revitYear} ribbon stays light; dark icons must not be used.");
            Assert.That(detector.GetThemeName(), Is.EqualTo("Light"));
        }

        /// <summary>
        /// Confirms that Revit 2024+ honours the API-reported dark theme.
        /// </summary>
        [Test]
        [TestCase(2024)]
        [TestCase(2025)]
        [TestCase(2026)]
        public void Revit2024AndLaterHonoursDarkTheme(int revitYear)
        {
            var detector = new RevitThemeDetector(new MockLogger(), () => "Dark", revitYear);

            Assert.That(detector.IsDarkTheme(), Is.True,
                $"Revit {revitYear} ribbon supports dark theme; dark icons should be used.");
        }

        /// <summary>
        /// Confirms that unavailable theme support uses the light-theme fallback.
        /// </summary>
        [Test]
        public void MissingThemeSupportFallsBackToLight()
        {
            var detector = new RevitThemeDetector(new MockLogger(), () => null);

            Assert.That(detector.IsDarkTheme(), Is.False);
            Assert.That(detector.GetThemeName(), Is.EqualTo("Light"));
        }

        /// <summary>
        /// Confirms that failed theme reads use the light-theme fallback and are logged.
        /// </summary>
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

        /// <summary>
        /// Confirms that a detected theme remains cached until the cache is cleared.
        /// </summary>
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

        /// <summary>
        /// Confirms that the reflection reader returns no theme when the API is unavailable.
        /// </summary>
        [Test]
        public void ReadCurrentThemeNameReturnsNullWhenThemeManagerIsUnavailable()
        {
            Assert.That(RevitThemeDetector.ReadCurrentThemeName(typeof(string)), Is.Null);
            Assert.That(RevitThemeDetector.ReadCurrentThemeName(null), Is.Null);
        }
    }
}
