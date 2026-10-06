using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Markup;
using System.Windows.Media;
using System.Windows.Threading;

using pyRevitLabs.Json.Linq;
using pyRevitLabs.NLog;
using pyRevitLabs.PyRevit;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// The page Revit hosts in the agent pane. Builds its view the first time it is shown, so a
    /// Revit session that never opens the panel pays almost nothing for it.
    /// </summary>
    /// <remarks>
    /// The view is XAML embedded in this assembly and loaded at runtime, with no code-behind:
    /// it only binds to <see cref="AgentPanelViewModel"/>. Session, activity and host changes
    /// arrive on any thread and are marshalled to this page's dispatcher before the view model
    /// is refreshed.
    /// </remarks>
    internal sealed class AgentPanelPage : Page {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();
        private static readonly TimeSpan WaitingRefreshInterval = TimeSpan.FromSeconds(1);

        private AgentPanelViewModel viewModel;

        public AgentPanelPage(bool dark) {
            AgentPanelTheme.Apply(this, dark);
            Background = (Brush)Resources["AgentPanel.Background"];
            Loaded += OnLoaded;
        }

        private void OnLoaded(object sender, RoutedEventArgs e) {
            if (viewModel != null)
                return;
            try {
                Resources.MergedDictionaries.Add(AgentPanelResources.LoadStrings());
                var view = (FrameworkElement)AgentPanelResources.Load("AgentPanel.View.xaml");
                viewModel = new AgentPanelViewModel(new AgentPanelBackend(Dispatcher), key => TryFindResource(key) as string);
                view.DataContext = viewModel;
                Content = view;

                AgentSessions.Tracker.Changed += QueueRefresh;
                AgentHost.Activity.Changed += QueueRefresh;
                AgentHost.StateChanged += QueueRefresh;
                AgentPanel.ActiveDocumentChanged += QueueRefresh;
                new DispatcherTimer(WaitingRefreshInterval, DispatcherPriority.Background, RefreshWhileWaiting, Dispatcher).Start();
            }
            catch (Exception ex) {
                logger.Error(ex, "Could not build the agent panel");
                Content = new TextBlock {
                    Text = "The agent panel could not be shown: " + ex.Message,
                    TextWrapping = TextWrapping.Wrap,
                    Margin = new Thickness(12),
                    Foreground = (Brush)Resources["AgentPanel.Foreground"],
                };
            }
        }

        private void QueueRefresh() {
            Dispatcher.BeginInvoke(new Action(() => viewModel?.Refresh()));
        }

        private void RefreshWhileWaiting(object sender, EventArgs e) {
            if (AgentHost.Activity.Current != null)
                viewModel?.Refresh();
        }
    }

    /// <summary>
    /// Connects the panel's view model to the host: sessions, activity, policy and the open
    /// Revit windows.
    /// </summary>
    internal sealed class AgentPanelBackend : IAgentPanelBackend {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        private readonly Dispatcher uiDispatcher;

        public AgentPanelBackend(Dispatcher uiDispatcher) {
            this.uiDispatcher = uiDispatcher;
        }

        public bool HostRunning => AgentHost.IsRunning;

        public string Policy {
            get {
                try {
                    return PyRevitConfigs.GetAgentPolicy();
                }
                catch (Exception) {
                    return PyRevitConsts.ConfigsAgentPolicyDefault;
                }
            }
        }

        public string ActiveDocumentTitle => AgentPanel.ActiveDocumentTitle;

        public JObject Session => AgentSessions.Describe();

        public AgentActivity Activity => AgentHost.Activity;

        public IList<string> OpenDialogs() {
            var ownTitle = "'" + AgentPanel.Title + "'";
            return AgentWindows.OpenDialogs()
                .Where(window => !window.StartsWith(ownTitle, StringComparison.Ordinal))
                .ToList();
        }

        /// <remarks>
        /// Posted to the agent dispatcher instead of run here: the button click is on Revit's
        /// main thread but outside a Revit API context, where starting a session must not read the
        /// active document.
        /// </remarks>
        public void Start(Action<string> onError) {
            void Report(string message) {
                uiDispatcher.BeginInvoke(new Action(() => onError(message)));
            }

            var dispatcher = AgentHost.Dispatcher;
            if (dispatcher == null) {
                onError("The agent host is not running.");
                return;
            }
            var posted = dispatcher.Post(app => {
                try {
                    AgentSessions.Start(app);
                }
                catch (AgentException ex) {
                    Report(ex.Message);
                }
                catch (Exception ex) {
                    logger.Error(ex, "Could not start an agent session from the panel");
                    Report(ex.Message);
                }
            });
            if (!posted)
                onError("Revit is busy and could not start the session. Try again in a moment.");
        }

        public void Pause() {
            AgentSessions.Pause();
        }

        public void Resume() {
            AgentSessions.Resume();
        }

        public void End() {
            AgentSessions.End();
        }

        public void Decline() {
            AgentSessions.Decline();
        }
    }

    /// <summary>
    /// Loads the panel's XAML, which is embedded in this assembly as resources named
    /// <c>PyRevitLabs.PyRevit.Runtime.Agent.&lt;file name&gt;</c>.
    /// </summary>
    /// <remarks>
    /// Important: string files are named <c>AgentPanel.Strings_&lt;locale&gt;.xaml</c>. With a
    /// <c>.&lt;locale&gt;</c> suffix, MSBuild takes the locale for a culture and moves the file
    /// into a satellite assembly that is never deployed, so the panel can't find its strings.
    /// </remarks>
    internal static class AgentPanelResources {
        private const string Prefix = "PyRevitLabs.PyRevit.Runtime.Agent.";
        private const string DefaultLocale = "en_us";

        public static object Load(string fileName) {
            var assembly = typeof(AgentPanelResources).Assembly;
            using (var stream = assembly.GetManifestResourceStream(Prefix + fileName)) {
                if (stream == null)
                    throw new FileNotFoundException("The agent panel resource is missing.", fileName);
                return XamlReader.Load(stream);
            }
        }

        /// <summary>
        /// The panel's strings in the user's pyRevit locale, or in English when the panel has no
        /// translation for it.
        /// </summary>
        public static ResourceDictionary LoadStrings() {
            var localized = StringsFile(UserLocale());
            var assembly = typeof(AgentPanelResources).Assembly;
            var name = assembly.GetManifestResourceNames().Contains(Prefix + localized)
                ? localized
                : StringsFile(DefaultLocale);
            return (ResourceDictionary)Load(name);
        }

        private static string StringsFile(string locale) {
            return "AgentPanel.Strings_" + locale + ".xaml";
        }

        private static string UserLocale() {
            try {
                var locale = PyRevitConfigs.GetUserLocale();
                return string.IsNullOrWhiteSpace(locale) ? DefaultLocale : locale.Trim().ToLowerInvariant();
            }
            catch (Exception) {
                return DefaultLocale;
            }
        }
    }

    /// <summary>
    /// The panel's light and dark palettes, applied as named brushes on the page so the view's
    /// <c>DynamicResource</c> references follow Revit's theme.
    /// </summary>
    internal static class AgentPanelTheme {
        private static readonly Dictionary<string, (int Light, int Dark)> Palette = new Dictionary<string, (int, int)> {
            ["AgentPanel.Background"] = (0xFFFFFF, 0x1F2D3D),
            ["AgentPanel.Foreground"] = (0x1E1E1E, 0xD4D4D4),
            ["AgentPanel.Muted"] = (0x666666, 0x9AA7B4),
            ["AgentPanel.Card"] = (0xF3F3F3, 0x2A3847),
            ["AgentPanel.Border"] = (0xD6D6D6, 0x39495C),
            ["AgentPanel.Notice"] = (0xFFF4CE, 0x4A3F1F),
            ["AgentPanel.Button"] = (0xE8E8E8, 0x39495C),
            ["AgentPanel.ButtonHover"] = (0xD9D9D9, 0x46586B),
            ["AgentPanel.Active"] = (0x3D9142, 0x6CC26C),
            ["AgentPanel.Paused"] = (0xB97A00, 0xE0A93B),
            ["AgentPanel.Idle"] = (0x8A8A8A, 0x8A99A8),
            ["AgentPanel.Error"] = (0xC42B1C, 0xF1707A),
        };

        public static void Apply(FrameworkElement root, bool dark) {
            foreach (var entry in Palette) {
                var rgb = dark ? entry.Value.Dark : entry.Value.Light;
                var brush = new SolidColorBrush(Color.FromRgb((byte)(rgb >> 16), (byte)(rgb >> 8), (byte)rgb));
                brush.Freeze();
                root.Resources[entry.Key] = brush;
            }
        }
    }
}
