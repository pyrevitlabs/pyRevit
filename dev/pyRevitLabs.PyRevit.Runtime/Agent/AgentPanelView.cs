using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Markup;
using System.Windows.Media;
using System.Windows.Threading;

using Autodesk.Revit.UI;

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
    /// is refreshed; changes that arrive before that refresh runs share it. While a request is in
    /// flight the page also refreshes once a second, because a Revit dialog that blocks it raises
    /// no event.
    /// </remarks>
    internal sealed class AgentPanelPage : Page {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();
        private static readonly TimeSpan WaitingRefreshInterval = TimeSpan.FromSeconds(1);

        private AgentPanelViewModel viewModel;
        private DispatcherTimer waitingTimer;
        private int refreshQueued;

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
                waitingTimer = new DispatcherTimer(WaitingRefreshInterval, DispatcherPriority.Background, (_, __) => Refresh(), Dispatcher);
                Refresh();
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
            if (Interlocked.Exchange(ref refreshQueued, 1) == 1)
                return;
            Dispatcher.BeginInvoke(new Action(() => {
                Interlocked.Exchange(ref refreshQueued, 0);
                Refresh();
            }));
        }

        private void Refresh() {
            viewModel?.Refresh();
            if (waitingTimer != null)
                waitingTimer.IsEnabled = AgentHost.Activity.Current != null;
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
            return AgentWindows.OpenDialogs();
        }

        public void Start(Action<string> onError) {
            PostToRevit("start the session", onError, app => {
                AgentSessions.Start(app);
                return null;
            });
        }

        public void Move(Action<string> onError) {
            PostToRevit("move the session", onError, app => {
                AgentSessions.Move(app);
                return null;
            });
        }

        /// <remarks>
        /// Uses the same presenter as <c>show_elements</c>, with the document title as a guard,
        /// so a click can't select whatever elements happen to have those ids in another
        /// document. Not behind the session gate: the user is acting, not the agent.
        /// </remarks>
        public void ShowElements(IList<long> ids, string document, Action<string> onError) {
            var request = new AgentPresenter.Request { Action = "select", Zoom = true, DocumentTitle = document };
            request.Ids.AddRange(ids);
            PostToRevit("show the elements", onError, app => {
                using (var dialogs = new AgentDialogCapture(app)) {
                    var missing = (AgentPresenter.Show(app, request, dialogs) as JObject)?["missing_ids"] as JArray;
                    return missing == null || missing.Count == 0
                        ? null
                        : $"Element {string.Join(", ", missing.Values<long>())} no longer exists in '{document}'.";
                }
            });
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

        /// <summary>
        /// Runs a panel action on Revit's main thread through the agent dispatcher, and shows
        /// what went wrong through <paramref name="onError"/> on the UI thread.
        /// </summary>
        /// <remarks>
        /// A button click is on Revit's main thread but outside a Revit API context, where the
        /// action must not touch the model or read the active document, so it is posted instead
        /// of run here.
        /// </remarks>
        /// <param name="action">What the user asked for, to finish "Could not ...".</param>
        /// <param name="work">The action; returns a problem to show, or null.</param>
        private void PostToRevit(string action, Action<string> onError, Func<UIApplication, string> work) {
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
                    var problem = work(app);
                    if (problem != null)
                        Report(problem);
                }
                catch (AgentException ex) {
                    Report(ex.Message);
                }
                catch (Exception ex) {
                    logger.Error(ex, "Could not {0} from the agent panel", action);
                    Report(ex.Message);
                }
            });
            if (!posted)
                onError($"Revit is busy and could not {action}. Try again in a moment.");
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
