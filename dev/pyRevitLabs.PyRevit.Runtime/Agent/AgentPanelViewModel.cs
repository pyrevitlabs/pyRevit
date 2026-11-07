using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Globalization;
using System.Linq;
using System.Windows.Input;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// What the agent panel reads and does, so its view model has no Revit dependency.
    /// </summary>
    internal interface IAgentPanelBackend {
        bool HostRunning { get; }

        /// <summary><c>readonly</c>, <c>ask</c> or <c>auto</c>.</summary>
        string Policy { get; }

        /// <summary>Title of the active document, or null when none is active.</summary>
        string ActiveDocumentTitle { get; }

        /// <summary>The session as <c>session_status</c> describes it.</summary>
        JObject Session { get; }

        AgentActivity Activity { get; }

        /// <summary>Revit windows open besides its main window, which keep it from taking requests.</summary>
        IList<string> OpenDialogs();

        /// <summary>
        /// Starts a session on the active document. Revit does the work later, so a failure is
        /// reported through <paramref name="onError"/> on the UI thread.
        /// </summary>
        void Start(Action<string> onError);

        /// <summary>
        /// Adds the active document to the open session. Revit does the work later, so a failure
        /// is reported through <paramref name="onError"/> on the UI thread.
        /// </summary>
        void Add(Action<string> onError);

        /// <summary>
        /// Selects and zooms to elements of <paramref name="document"/>, refusing when another
        /// document is active. A failure is reported through <paramref name="onError"/> on the UI
        /// thread.
        /// </summary>
        /// <param name="documentPath">The document's path, or null when it was never saved.</param>
        void ShowElements(IList<long> ids, string document, string documentPath, Action<string> onError);

        void Pause();
        void Resume();
        void End();
        void Decline();
    }

    internal sealed class AgentPanelCommand : ICommand {
        private readonly Action execute;

        public AgentPanelCommand(Action execute) {
            this.execute = execute;
        }

        public event EventHandler CanExecuteChanged {
            add { }
            remove { }
        }

        public bool CanExecute(object parameter) {
            return true;
        }

        public void Execute(object parameter) {
            execute();
        }
    }

    /// <summary>
    /// The agent panel's state and actions: the session, what an agent is waiting for, the
    /// last request it made, and the log of everything agents did in this Revit session.
    /// </summary>
    /// <remarks>
    /// Must be used on the UI thread. <see cref="Refresh"/> rereads everything from the backend,
    /// so code on other threads marshals a call to it instead of changing properties.
    /// All text comes through <c>text</c>, keyed like <c>AgentPanel.State.Active</c>, so the
    /// panel's strings live in its resource dictionary and can be translated there.
    /// Buttons are shown only when their action applies, so the commands are always executable.
    /// </remarks>
    internal sealed class AgentPanelViewModel : INotifyPropertyChanged {
        private const string TimeFormat = "HH:mm";

        private readonly IAgentPanelBackend backend;
        private readonly AgentLogText strings;
        private string errorText;

        public AgentPanelViewModel(IAgentPanelBackend backend, Func<string, string> text) {
            this.backend = backend;
            strings = new AgentLogText(text);
            StartCommand = new AgentPanelCommand(() => Post(backend.Start));
            AddCommand = new AgentPanelCommand(() => Post(backend.Add));
            PauseCommand = new AgentPanelCommand(() => Act(backend.Pause));
            ResumeCommand = new AgentPanelCommand(() => Act(backend.Resume));
            EndCommand = new AgentPanelCommand(() => Act(backend.End));
            AcceptCommand = new AgentPanelCommand(() => {
                if (StateKind == "paused")
                    Act(backend.Resume);
                else
                    Post(backend.Start);
            });
            DeclineCommand = new AgentPanelCommand(() => Act(backend.Decline));
            Log = new AgentLogViewModel(text, ShowElement);
            Refresh();
        }

        public event PropertyChangedEventHandler PropertyChanged;

        /// <summary><c>off</c>, <c>inactive</c>, <c>active</c> or <c>paused</c>.</summary>
        public string StateKind { get; private set; }

        public string StateLabel { get; private set; }
        public string DocumentLine { get; private set; }
        public bool HasPausedReason { get; private set; }
        public string PausedReason { get; private set; }
        public string StartLabel { get; private set; }
        public bool CanStart { get; private set; }

        /// <summary>
        /// Whether the active document is outside a session the user started, so agents can't work
        /// in it until the user adds it.
        /// </summary>
        public bool IsActiveOutside { get; private set; }

        public string ActiveOutsideText { get; private set; }
        public bool CanAdd { get; private set; }
        public string AddLabel { get; private set; }
        public bool CanPause { get; private set; }
        public bool CanResume { get; private set; }
        public bool CanEnd { get; private set; }

        public bool HasRequest { get; private set; }
        public string RequestReason { get; private set; }
        public string RequestTime { get; private set; }
        public string AcceptLabel { get; private set; }
        public bool CanAccept { get; private set; }

        public string PolicyText { get; private set; }
        public string ClientText { get; private set; }
        public bool HasLast { get; private set; }
        public string LastText { get; private set; }
        public bool HasWaiting { get; private set; }
        public string WaitingText { get; private set; }

        public bool HasError => !string.IsNullOrEmpty(errorText);
        public string ErrorText => errorText;

        public ICommand StartCommand { get; }
        public ICommand AddCommand { get; }
        public ICommand PauseCommand { get; }
        public ICommand ResumeCommand { get; }
        public ICommand EndCommand { get; }
        public ICommand AcceptCommand { get; }
        public ICommand DeclineCommand { get; }

        public AgentLogViewModel Log { get; }

        public void Refresh() {
            var session = backend.Session ?? new JObject();
            var running = backend.HostRunning;
            var activeTitle = backend.ActiveDocumentTitle;
            StateKind = running ? session.Value<string>("state") ?? "inactive" : "off";

            var startsAutomatically = session.Value<string>("start") == "auto";
            StateLabel = strings.Text("AgentPanel.State." + Capitalize(StateKind));
            CanStart = StateKind == "inactive" && activeTitle != null && !startsAutomatically;
            CanPause = StateKind == "active";
            CanResume = StateKind == "paused";
            var isOpen = CanPause || CanResume;
            CanEnd = isOpen && !startsAutomatically;
            StartLabel = activeTitle == null ? string.Empty : strings.Format("AgentPanel.Start", activeTitle);
            var titles = isOpen ? Titles(session) : new List<string>();
            IsActiveOutside = isOpen && session.Value<bool?>("automatic") != true
                && activeTitle != null && !titles.Contains(activeTitle);
            CanAdd = IsActiveOutside;
            AddLabel = CanAdd ? strings.Format("AgentPanel.Add", activeTitle) : string.Empty;
            ActiveOutsideText = IsActiveOutside ? strings.Format("AgentPanel.Document.NotInSession", activeTitle) : string.Empty;
            DocumentLine = DescribeDocument(session, titles, activeTitle, startsAutomatically);
            DescribePause(session);

            var request = running ? session["pending_request"] as JObject : null;
            HasRequest = request != null;
            RequestReason = request?.Value<string>("reason") ?? strings.Text("AgentPanel.Request.NoReason");
            RequestTime = request == null ? string.Empty : strings.Format("AgentPanel.Request.Time", LocalTime(request.Value<string>("requested")));
            CanAccept = StateKind == "paused" || CanStart;
            AcceptLabel = StateKind == "paused" ? strings.Text("AgentPanel.Resume") : StartLabel;

            PolicyText = strings.Text("AgentPanel.Policy." + Capitalize(backend.Policy ?? "ask"));
            var activity = backend.Activity;
            ClientText = activity?.Client ?? strings.Text("AgentPanel.Client.Unknown");
            DescribeLast(activity?.Last);
            DescribeWaiting(activity);
            Log.Update(activity?.History ?? new AgentRequestRecord[0]);

            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(string.Empty));
        }

        private void ShowElement(AgentLogElement element) {
            Post(onError => backend.ShowElements(new[] { element.Id }, element.Document, element.DocumentPath, onError));
        }

        /// <summary>
        /// Runs an action Revit carries out later, showing its failure when it is reported.
        /// </summary>
        private void Post(Action<Action<string>> action) {
            errorText = null;
            action(message => {
                errorText = message;
                Refresh();
            });
            Refresh();
        }

        private void Act(Action action) {
            errorText = null;
            try {
                action();
            }
            catch (AgentException ex) {
                errorText = ex.Message;
            }
            Refresh();
        }

        private string DescribeDocument(JObject session, List<string> titles, string activeTitle, bool startsAutomatically) {
            switch (StateKind) {
                case "off":
                    return strings.Text("AgentPanel.Document.HostOff");
                case "active":
                case "paused":
                    return strings.Format("AgentPanel.Document.Bound", string.Join(", ", titles), LocalTime(session.Value<string>("started")));
                default:
                    if (startsAutomatically)
                        return strings.Text("AgentPanel.Document.Auto");
                    if (activeTitle == null)
                        return strings.Text("AgentPanel.Document.NoDocument");
                    return strings.Text("AgentPanel.Document.Ready");
            }
        }

        private static List<string> Titles(JObject session) {
            return (session["documents"] as JArray ?? new JArray())
                .OfType<JObject>()
                .Select(document => document.Value<string>("title"))
                .Where(title => !string.IsNullOrEmpty(title))
                .ToList();
        }

        private void DescribePause(JObject session) {
            var pausedReason = StateKind == "paused" ? session.Value<string>("paused_reason") : null;
            HasPausedReason = !string.IsNullOrEmpty(pausedReason);
            if (!HasPausedReason)
                PausedReason = string.Empty;
            else if (session.Value<string>("paused_cause") == AgentSessionPauseCauses.PanelHidden)
                PausedReason = strings.Text("AgentPanel.Paused.PanelHidden");
            else if (session.Value<string>("paused_cause") == AgentSessionPauseCauses.Agent)
                PausedReason = strings.Text("AgentPanel.Paused.ByAgent");
            else
                PausedReason = strings.Format("AgentPanel.Paused.ByHost", pausedReason);
        }

        private void DescribeLast(AgentRequestRecord last) {
            HasLast = last != null && last.FinishedUtc.HasValue;
            LastText = HasLast
                ? strings.Format("AgentPanel.Last", Name(last), AgentLogText.LocalTime(last.FinishedUtc.Value, TimeFormat), last.Outcome)
                : string.Empty;
        }

        private void DescribeWaiting(AgentActivity activity) {
            var current = activity?.Current;
            HasWaiting = current != null;
            if (current == null) {
                WaitingText = string.Empty;
                return;
            }
            if (activity.AwaitingApproval) {
                WaitingText = strings.Format("AgentPanel.Waiting.Approval", Name(current));
                return;
            }
            if (current.Started) {
                WaitingText = strings.Format("AgentPanel.Waiting.Running", Name(current));
                return;
            }
            var dialogs = backend.OpenDialogs();
            WaitingText = dialogs != null && dialogs.Count > 0
                ? strings.Format("AgentPanel.Waiting.Dialog", Name(current), string.Join(", ", dialogs))
                : strings.Format("AgentPanel.Waiting.Revit", Name(current));
        }

        private string Name(AgentRequestRecord record) {
            var kind = strings.Text("AgentPanel.Kind." + record.Kind);
            return string.IsNullOrEmpty(record.Title) ? kind : kind + ": " + record.Title;
        }

        private static string LocalTime(string utc) {
            return DateTime.TryParse(utc, CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out var parsed)
                ? AgentLogText.LocalTime(parsed, TimeFormat)
                : string.Empty;
        }

        private static string Capitalize(string value) {
            if (string.IsNullOrEmpty(value))
                return value;
            var words = value.Split('_');
            for (var index = 0; index < words.Length; index++)
                if (words[index].Length > 0)
                    words[index] = char.ToUpperInvariant(words[index][0]) + words[index].Substring(1);
            return string.Concat(words);
        }
    }
}
