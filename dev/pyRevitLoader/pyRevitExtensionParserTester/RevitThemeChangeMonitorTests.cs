using pyRevitAssemblyBuilder.SessionManager;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class RevitThemeChangeMonitorTests
    {
        [Test]
        public void ThemeTransitionClearsCacheAndRequestsReload()
        {
            var source = new FakeThemeSource("Dark");
            var cacheClearCount = 0;
            var requestedThemes = new List<string>();
            using var monitor = CreateMonitor(
                source,
                requestedThemes.Add,
                () => cacheClearCount++);

            monitor.Start();
            monitor.SetSessionReady();
            source.ChangeTheme("Light");

            Assert.That(cacheClearCount, Is.EqualTo(1));
            Assert.That(requestedThemes, Is.EqualTo(new[] { "Light" }));
        }

        [Test]
        public void DuplicateOrCanvasOnlyEventDoesNotRequestReload()
        {
            var source = new FakeThemeSource("Dark");
            var cacheClearCount = 0;
            var requestedThemes = new List<string>();
            using var monitor = CreateMonitor(
                source,
                requestedThemes.Add,
                () => cacheClearCount++);

            monitor.Start();
            monitor.SetSessionReady();
            source.RaiseThemeChanged();
            source.RaiseThemeChanged();

            Assert.That(cacheClearCount, Is.Zero);
            Assert.That(requestedThemes, Is.Empty);
        }

        [Test]
        public void StartupTransitionDefersNotificationUntilSessionIsReady()
        {
            var source = new FakeThemeSource("Dark");
            var cacheClearCount = 0;
            var requestedThemes = new List<string>();
            using var monitor = CreateMonitor(
                source,
                requestedThemes.Add,
                () => cacheClearCount++);

            monitor.Start();
            source.ChangeTheme("Light");
            Assert.That(requestedThemes, Is.Empty);

            monitor.SetSessionReady();

            Assert.That(cacheClearCount, Is.EqualTo(1));
            Assert.That(requestedThemes, Is.EqualTo(new[] { "Light" }));
        }

        [Test]
        public void DisposeStopsThemeMonitoring()
        {
            var source = new FakeThemeSource("Dark");
            var cacheClearCount = 0;
            var requestedThemes = new List<string>();
            var monitor = CreateMonitor(
                source,
                requestedThemes.Add,
                () => cacheClearCount++);

            monitor.Start();
            monitor.SetSessionReady();
            monitor.Dispose();
            source.ChangeTheme("Light");

            Assert.That(source.IsSubscribed, Is.False);
            Assert.That(cacheClearCount, Is.Zero);
            Assert.That(requestedThemes, Is.Empty);
        }

        [Test]
        public void StartIsIdempotent()
        {
            var source = new FakeThemeSource("Dark");
            using var monitor = CreateMonitor(source, _ => { }, () => { });

            monitor.Start();
            monitor.Start();

            Assert.That(source.SubscriptionCount, Is.EqualTo(1));
        }

        [Test]
        public void ReflectionThemeSourceForwardsTypedEvent()
        {
            var eventHost = new FakeThemeEventHost();
            var source = new ReflectionRevitThemeSource(eventHost, typeof(FakeThemeEventHost));
            var eventCount = 0;

            Assert.That(source.Subscribe((_, _) => eventCount++), Is.True);
            eventHost.RaiseThemeChanged();
            source.Unsubscribe();
            eventHost.RaiseThemeChanged();

            Assert.That(eventCount, Is.EqualTo(1));
        }

        private static RevitThemeChangeMonitor CreateMonitor(
            IRevitThemeSource source,
            Action<string> themeChanged,
            Action clearThemeCache)
        {
            return new RevitThemeChangeMonitor(
                source,
                new MockLogger(),
                themeChanged,
                clearThemeCache);
        }

        private sealed class FakeThemeSource : IRevitThemeSource
        {
            private EventHandler? _handler;

            public FakeThemeSource(string initialTheme)
            {
                CurrentTheme = initialTheme;
            }

            public string CurrentTheme { get; private set; }
            public bool IsSubscribed => _handler != null;
            public int SubscriptionCount { get; private set; }

            public string GetCurrentTheme()
            {
                return CurrentTheme;
            }

            public bool Subscribe(EventHandler handler)
            {
                _handler = handler;
                SubscriptionCount++;
                return true;
            }

            public void Unsubscribe()
            {
                _handler = null;
            }

            public void ChangeTheme(string theme)
            {
                CurrentTheme = theme;
                RaiseThemeChanged();
            }

            public void RaiseThemeChanged()
            {
                _handler?.Invoke(this, EventArgs.Empty);
            }
        }

        private sealed class FakeThemeEventHost
        {
            public event EventHandler<FakeThemeChangedEventArgs>? ThemeChanged;

            public void RaiseThemeChanged()
            {
                ThemeChanged?.Invoke(this, new FakeThemeChangedEventArgs());
            }
        }

        private sealed class FakeThemeChangedEventArgs : EventArgs
        {
        }
    }
}
