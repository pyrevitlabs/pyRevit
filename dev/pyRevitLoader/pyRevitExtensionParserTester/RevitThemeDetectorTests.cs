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
        public void ClearThemeCacheBeforeTest()
        {
            RevitThemeDetector.ClearCache();
            RevitThemeDetector.SetHostRevitYearFromVersion(null);
        }

        [TearDown]
        public void ClearThemeCacheAfterTest()
        {
            RevitThemeDetector.ClearCache();
            RevitThemeDetector.SetHostRevitYearFromVersion(null);
        }

        private static RevitThemeDetector Detector(ILogger logger, string themeName, int revitYear)
        {
            return new RevitThemeDetector(logger, () => themeName, () => revitYear);
        }

        /// <summary>
        /// Confirms that a dark theme is returned by the detector.
        /// </summary>
        [Test]
        public void DarkThemeNameIsDetectedRegardlessOfBaselineRevitVersion()
        {
            var detector = Detector(new MockLogger(), "Dark", 2027);

            Assert.That(detector.IsDarkTheme(), Is.True);
            Assert.That(detector.GetThemeName(), Is.EqualTo("Dark"));
        }

        /// <summary>
        /// Confirms that unavailable theme support uses the light-theme fallback.
        /// </summary>
        [Test]
        public void MissingThemeSupportFallsBackToLight()
        {
            var detector = Detector(new MockLogger(), null, 2027);

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
                () => throw new InvalidOperationException("no theme api"),
                () => 2027);

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
                },
                () => 2027);

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

        /// <summary>
        /// Confirms that Revit 2021-2023 are the only years whose ribbon stays light while the
        /// host reports a dark theme, and that the boundary is exactly 2024 (#3742).
        /// </summary>
        [TestCase(2021)]
        [TestCase(2022)]
        [TestCase(2023)]
        public void Pre2024RevitYearsDoNotSupportADarkRibbon(int revitYear)
        {
            Assert.That(
                RevitThemeDetector.SupportsDarkRibbon(revitYear),
                Is.False,
                $"Revit {revitYear} keeps a light ribbon, so dark icons must not be used.");
        }

        [TestCase(2024)]
        [TestCase(2025)]
        [TestCase(2026)]
        [TestCase(2027)]
        public void Revit2024AndLaterSupportADarkRibbon(int revitYear)
        {
            Assert.That(
                RevitThemeDetector.SupportsDarkRibbon(revitYear),
                Is.True,
                $"Revit {revitYear} renders a dark ribbon under the Dark theme.");
        }

        /// <summary>
        /// Confirms an unreadable host year keeps the dark ribbon rather than losing dark icons.
        /// </summary>
        [Test]
        public void UnknownRevitYearStillSupportsADarkRibbon()
        {
            Assert.That(RevitThemeDetector.SupportsDarkRibbon(0), Is.True);
            Assert.That(RevitThemeDetector.SupportsDarkRibbon(-1), Is.True);
        }

        /// <summary>
        /// Confirms the host year is read from the version string the caller supplies, and that a
        /// missing or unparsable one reads as unknown.
        /// </summary>
        /// <remarks>
        /// Regression guard for two earlier attempts at this lookup. Reading
        /// <c>UIApplication.Application</c> as a static yields null, and reaching for the non-public
        /// static <c>UIApplication.Instance</c> works on Revit 2027 but not on 2021-2026 - verified
        /// against the installed RevitAPIUI.dll for every supported year. Either mistake leaves the
        /// year unknown, and unknown is treated as dark-capable, so the gate would silently do
        /// nothing on exactly the versions it exists for (#3742).
        /// </remarks>
        [TestCase("2021", 2021)]
        [TestCase("2022", 2022)]
        [TestCase("2023", 2023)]
        [TestCase("2024", 2024)]
        [TestCase("2027", 2027)]
        public void ReadRevitYearParsesTheHostVersion(string versionNumber, int expected)
        {
            Assert.That(RevitThemeDetector.ParseRevitYear(versionNumber), Is.EqualTo(expected));
        }

        [TestCase("")]
        [TestCase("not-a-year")]
        [TestCase("2023.1")]
        public void ReadRevitYearTreatsAnUnparsableVersionAsUnknown(string versionNumber)
        {
            Assert.That(RevitThemeDetector.ParseRevitYear(versionNumber), Is.EqualTo(0));
        }

        [Test]
        public void ReadRevitYearTreatsAMissingVersionAsUnknown()
        {
            Assert.That(RevitThemeDetector.ParseRevitYear(null), Is.EqualTo(0));
        }

        /// <summary>
        /// Confirms an unreadable host version lands on an unknown year rather than propagating.
        /// </summary>
        /// <remarks>
        /// <c>SetHostRevitYear</c> runs on the startup path, where an exception would abort the
        /// session load, so it swallows failures and records an unknown year - which the gate
        /// treats as dark-capable rather than as a broken build.
        /// <para>
        /// The <c>UIApplication</c> overload cannot be exercised here: referencing the type at all
        /// makes the JIT load RevitAPIUI, which is absent outside a Revit host. The
        /// <c>UIApplication</c> path is covered by the live run on Revit 2023 and 2027 instead.
        /// </para>
        /// </remarks>
        [Test]
        public void AnUnreadableHostVersionRecordsAnUnknownYear()
        {
            Assert.DoesNotThrow(() => RevitThemeDetector.SetHostRevitYearFromVersion(null));
            Assert.That(RevitThemeDetector.HostRevitYear(), Is.EqualTo(0));

            Assert.DoesNotThrow(() => RevitThemeDetector.SetHostRevitYearFromVersion("2023"));
            Assert.That(RevitThemeDetector.HostRevitYear(), Is.EqualTo(2023));
        }

        /// <summary>
        /// Confirms the recorded host year gates the detector, which is the whole point of the
        /// change: a 2023 host that reports "Dark" must resolve to light icons.
        /// </summary>
        [TestCase("2021", false)]
        [TestCase("2022", false)]
        [TestCase("2023", false)]
        [TestCase("2024", true)]
        [TestCase("2027", true)]
        public void TheRecordedHostYearGatesTheDetector(string versionNumber, bool expectDark)
        {
            RevitThemeDetector.SetHostRevitYearFromVersion(versionNumber);

            var detector = new RevitThemeDetector(new MockLogger(), () => "Dark");

            Assert.That(detector.IsDarkTheme(), Is.EqualTo(expectDark));
        }

        [Test]
        public void AnUnrecordedHostYearIsTreatedAsDarkCapable()
        {
            RevitThemeDetector.SetHostRevitYearFromVersion(null);

            Assert.That(RevitThemeDetector.HostRevitYear(), Is.EqualTo(0));

            var detector = new RevitThemeDetector(new MockLogger(), () => "Dark");

            Assert.That(detector.IsDarkTheme(), Is.True,
                "An unknown host keeps today's behaviour rather than losing dark icons.");
        }

        /// <summary>
        /// Confirms a host that reports "Dark" on Revit 2021-2023 still resolves to the light theme,
        /// which is the regression reported in #3742: dark icons drawn on a light ribbon are
        /// invisible.
        /// </summary>
        [TestCase(2021)]
        [TestCase(2022)]
        [TestCase(2023)]
        public void ADarkThemeOnPre2024ResolvesToTheLightRibbon(int revitYear)
        {
            var detector = Detector(new MockLogger(), "Dark", revitYear);

            Assert.That(detector.IsDarkTheme(), Is.False);
            Assert.That(detector.GetThemeName(), Is.EqualTo("Light"));
        }

        /// <summary>
        /// Confirms a host that reports "Dark" on Revit 2024 and later still resolves to the dark
        /// ribbon, so the fix does not disable dark mode where it works.
        /// </summary>
        [TestCase(2024)]
        [TestCase(2027)]
        public void ADarkThemeOn2024AndLaterResolvesToTheDarkRibbon(int revitYear)
        {
            var detector = Detector(new MockLogger(), "Dark", revitYear);

            Assert.That(detector.IsDarkTheme(), Is.True);
            Assert.That(detector.GetThemeName(), Is.EqualTo("Dark"));
        }

        /// <summary>
        /// Confirms a light theme stays light on every supported host year.
        /// </summary>
        [TestCase(2021)]
        [TestCase(2024)]
        [TestCase(2027)]
        public void ALightThemeStaysLightOnEveryHostYear(int revitYear)
        {
            var detector = Detector(new MockLogger(), "Light", revitYear);

            Assert.That(detector.IsDarkTheme(), Is.False);
            Assert.That(detector.GetThemeName(), Is.EqualTo("Light"));
        }

        /// <summary>
        /// Confirms the loader's live theme-change path applies the same gate as the detector, so a
        /// theme switch cannot repaint a pre-2024 ribbon with dark icons.
        /// </summary>
        [TestCase(2021)]
        [TestCase(2022)]
        [TestCase(2023)]
        public void TheLiveRefreshPathRejectsDarkOnPre2024(int revitYear)
        {
            Assert.That(RevitThemeDetector.IsDarkRibbonThemeFor("Dark", revitYear), Is.False);
        }

        /// <summary>
        /// Confirms the loader's live theme-change path still honours a real dark switch on the
        /// hosts that support one.
        /// </summary>
        [TestCase(2024)]
        [TestCase(2027)]
        public void TheLiveRefreshPathAcceptsDarkOn2024AndLater(int revitYear)
        {
            Assert.That(RevitThemeDetector.IsDarkRibbonThemeFor("Dark", revitYear), Is.True);
            Assert.That(RevitThemeDetector.IsDarkRibbonThemeFor("Light", revitYear), Is.False);
        }
    }
}
