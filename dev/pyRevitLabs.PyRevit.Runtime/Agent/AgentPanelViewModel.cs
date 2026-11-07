using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
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

        /// <summary>The open documents, links left out, with the active one marked.</summary>
        IList<AgentPanelOpenDocument> OpenDocuments { get; }

        /// <summary>The session as <c>session_status</c> describes it.</summary>
        JObject Session { get; }

        AgentActivity Activity { get; }

        /// <summary>Revit windows open besides its main window, which keep it from taking requests.</summary>
        IList<string> OpenDialogs();

        /// <summary>
        /// Starts a session on the documents with <paramref name="keys"/>. Revit does the work
        /// later, so a failure is reported through <paramref name="onError"/> on the UI thread.
        /// </summary>
        void Start(IList<string> keys, Action<string> onError);

        /// <summary>
        /// Adds the document with <paramref name="key"/> to the open session. Revit does the work
        /// later, so a failure is reported through <paramref name="onError"/> on the UI thread.
        /// </summary>
        void Add(string key, Action<string> onError);

        /// <summary>Takes the document with <paramref name="key"/> out of the open session.</summary>
        /// <exception cref="AgentException">When the session refuses.</exception>
        void Remove(string key);

        /// <summary>
        /// Closes, without saving, a document an agent opened in the session. Revit does the work
        /// later, so a failure is reported through <paramref name="onError"/> on the UI thread.
        /// </summary>
        void Close(string key, Action<string> onError);

        /// <summary>
        /// Selects and zooms to elements of <paramref name="document"/>, refusing when another
        /// document is active. A failure is reported through <paramref name="onError"/> on the UI
        /// thread.
        /// </summary>
        /// <param name="documentPath">The document's path, or null when it was never saved.</param>
        void ShowElements(IList<long> ids, string document, string documentPath, Action<string> onError);

        void Pause();
        void Resume();

        /// <summary>
        /// Ends the session. Revit does the work later, because ending closes the documents agents
        /// opened, so a failure is reported through <paramref name="onError"/> on the UI thread.
        /// </summary>
        void End(Action<string> onError);

        void Decline();
    }

    /// <summary>
    /// An open document as the panel knows it from Revit's events.
    /// </summary>
    internal sealed class AgentPanelOpenDocument : IEquatable<AgentPanelOpenDocument> {
        public AgentPanelOpenDocument(string key, string title, bool isActive, bool isBackground) {
            Key = key;
            Title = title;
            IsActive = isActive;
            IsBackground = isBackground;
        }

        public string Key { get; }
        public string Title { get; }
        public bool IsActive { get; }

        /// <summary>
        /// Open with no view in Revit, as a family an agent opened is. The user can't see it, so
        /// the panel doesn't offer it.
        /// </summary>
        public bool IsBackground { get; }

        public bool Equals(AgentPanelOpenDocument other) {
            return other != null && Key == other.Key && Title == other.Title && IsActive == other.IsActive
                && IsBackground == other.IsBackground;
        }

        public override bool Equals(object obj) {
            return Equals(obj as AgentPanelOpenDocument);
        }

        public override int GetHashCode() {
            return (Key ?? string.Empty).GetHashCode();
        }
    }

    /// <summary>
    /// A document in one of the panel's lists: one to choose for a new session, one in the
    /// session, or one open beside it. Each action is offered only when its command is set.
    /// </summary>
    internal sealed class AgentPanelDocumentRow : INotifyPropertyChanged {
        private bool isChosen;

        public AgentPanelDocumentRow(string key, string title, string note) {
            Key = key;
            Title = title;
            Note = note;
        }

        public event PropertyChangedEventHandler PropertyChanged;

        public string Key { get; }
        public string Title { get; }

        /// <summary>A muted word after the title, such as that the document is the active one.</summary>
        public string Note { get; }

        public bool HasNote => !string.IsNullOrEmpty(Note);

        /// <summary>Whether the user ticked the document to start a session on.</summary>
        public bool IsChosen {
            get => isChosen;
            set {
                if (isChosen == value)
                    return;
                ShowChosen(value);
                ChosenChanged?.Invoke();
            }
        }

        public ICommand RemoveCommand { get; set; }
        public ICommand CloseCommand { get; set; }
        public ICommand AddCommand { get; set; }
        public bool CanRemove => RemoveCommand != null;
        public bool CanClose => CloseCommand != null;
        public bool CanAdd => AddCommand != null;

        internal Action ChosenChanged { get; set; }

        /// <summary>What the row shows apart from its tick, so a list is rebuilt only when that changes.</summary>
        internal string Signature => string.Join("|", Key, Title, Note, CanRemove, CanClose, CanAdd);

        /// <summary>Sets the tick without telling the panel, as the panel does when it rereads.</summary>
        internal void ShowChosen(bool chosen) {
            if (isChosen == chosen)
                return;
            isChosen = chosen;
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(IsChosen)));
        }
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
    /// The agent panel's state and actions: the session and its documents, what an agent is
    /// waiting for, the last request it made, and the log of everything agents did in this Revit
    /// session.
    /// </summary>
    /// <remarks>
    /// Must be used on the UI thread. <see cref="Refresh"/> rereads everything from the backend,
    /// so code on other threads marshals a call to it instead of changing properties.
    /// All text comes through <c>text</c>, keyed like <c>AgentPanel.State.Active</c>, so the
    /// panel's strings live in its resource dictionary and can be translated there.
    /// Buttons are shown only when their action applies, so the commands are always executable.
    /// Documents are told apart by key, never by title, since titles aren't unique. Before a
    /// session starts, the active document is ticked until the user ticks another; after that the
    /// user's choice stands until a session starts.
    /// </remarks>
    internal sealed class AgentPanelViewModel : INotifyPropertyChanged {
        private const string TimeFormat = "HH:mm";

        private readonly IAgentPanelBackend backend;
        private readonly AgentLogText strings;
        private string errorText;
        private HashSet<string> chosenKeys;

        public AgentPanelViewModel(IAgentPanelBackend backend, Func<string, string> text) {
            this.backend = backend;
            strings = new AgentLogText(text);
            StartCommand = new AgentPanelCommand(StartChosen);
            PauseCommand = new AgentPanelCommand(() => Act(backend.Pause));
            ResumeCommand = new AgentPanelCommand(() => Act(backend.Resume));
            EndCommand = new AgentPanelCommand(() => Post(backend.End));
            AcceptCommand = new AgentPanelCommand(() => {
                if (StateKind == "paused")
                    Act(backend.Resume);
                else
                    StartChosen();
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

        /// <summary>Whether the user picks the documents for a new session.</summary>
        public bool IsChoosing { get; private set; }

        /// <summary>Open documents to tick for a new session, the active one first ticked.</summary>
        public ObservableCollection<AgentPanelDocumentRow> ChoiceDocuments { get; } = new ObservableCollection<AgentPanelDocumentRow>();

        /// <summary>Whether no document is ticked, so there is nothing to start on.</summary>
        public bool HasChooseHint { get; private set; }

        public string StartLabel { get; private set; }
        public bool CanStart { get; private set; }

        public bool HasSessionDocuments { get; private set; }

        /// <summary>
        /// The session's documents. The user's can be taken out while more than one remains;
        /// the ones an agent opened can be closed.
        /// </summary>
        public ObservableCollection<AgentPanelDocumentRow> SessionDocuments { get; } = new ObservableCollection<AgentPanelDocumentRow>();

        public bool HasOtherDocuments { get; private set; }

        /// <summary>Open documents outside a session the user started, each offered to add.</summary>
        public ObservableCollection<AgentPanelDocumentRow> OtherDocuments { get; } = new ObservableCollection<AgentPanelDocumentRow>();

        /// <summary>
        /// Whether the active document is outside a session the user started, so agents can't work
        /// in it until the user adds it.
        /// </summary>
        public bool IsActiveOutside { get; private set; }

        public string ActiveOutsideText { get; private set; }
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
        public ICommand PauseCommand { get; }
        public ICommand ResumeCommand { get; }
        public ICommand EndCommand { get; }
        public ICommand AcceptCommand { get; }
        public ICommand DeclineCommand { get; }

        public AgentLogViewModel Log { get; }

        public void Refresh() {
            var session = backend.Session ?? new JObject();
            var running = backend.HostRunning;
            var open = backend.OpenDocuments ?? new List<AgentPanelOpenDocument>();
            var visible = open.Where(document => !document.IsBackground).ToList();
            var active = open.FirstOrDefault(document => document.IsActive);
            StateKind = running ? session.Value<string>("state") ?? "inactive" : "off";

            var startsAutomatically = session.Value<string>("start") == "auto";
            var automatic = session.Value<bool?>("automatic") == true;
            StateLabel = strings.Text("AgentPanel.State." + Capitalize(StateKind));
            CanPause = StateKind == "active";
            CanResume = StateKind == "paused";
            var isOpen = CanPause || CanResume;
            CanEnd = isOpen && !startsAutomatically;
            var inSession = isOpen ? Entries(session) : new List<JObject>();
            var sessionKeys = new HashSet<string>(inSession.Select(entry => entry.Value<string>("key")));

            DescribeChoice(visible, StateKind == "inactive" && !startsAutomatically);
            DescribeSession(inSession, automatic);
            DescribeOthers(isOpen && !automatic
                ? visible.Where(document => !sessionKeys.Contains(document.Key)).ToList()
                : new List<AgentPanelOpenDocument>());
            IsActiveOutside = isOpen && !automatic && active != null && !active.IsBackground && !sessionKeys.Contains(active.Key);
            ActiveOutsideText = IsActiveOutside ? strings.Format("AgentPanel.Document.NotInSession", active.Title) : string.Empty;
            DocumentLine = DescribeDocument(session, visible.Count > 0, startsAutomatically);
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

        private void StartChosen() {
            var keys = ChoiceDocuments.Where(row => row.IsChosen).Select(row => row.Key).ToList();
            Post(onError => backend.Start(keys, onError));
        }

        private void OnChosenChanged() {
            chosenKeys = new HashSet<string>(ChoiceDocuments.Where(row => row.IsChosen).Select(row => row.Key));
            Refresh();
        }

        private void DescribeChoice(List<AgentPanelOpenDocument> visible, bool canChoose) {
            IsChoosing = canChoose && visible.Count > 0;
            if (!IsChoosing) {
                chosenKeys = null;
                Sync(ChoiceDocuments, new List<AgentPanelDocumentRow>());
                CanStart = false;
                HasChooseHint = false;
                StartLabel = string.Empty;
                return;
            }
            var chosen = new HashSet<string>(chosenKeys ?? visible.Where(document => document.IsActive).Select(document => document.Key));
            Sync(ChoiceDocuments, visible.Select(document => {
                var row = new AgentPanelDocumentRow(document.Key, document.Title, ActiveNote(document)) { ChosenChanged = OnChosenChanged };
                row.ShowChosen(chosen.Contains(document.Key));
                return row;
            }).ToList());
            var titles = visible.Where(document => chosen.Contains(document.Key)).Select(document => document.Title).ToList();
            CanStart = titles.Count > 0;
            HasChooseHint = titles.Count == 0;
            StartLabel = titles.Count == 1
                ? strings.Format("AgentPanel.Start", titles[0])
                : titles.Count > 1 ? strings.Format("AgentPanel.Start.Many", titles.Count) : string.Empty;
        }

        private void DescribeSession(List<JObject> entries, bool automatic) {
            HasSessionDocuments = entries.Count > 0;
            var removable = !automatic && entries.Count > 1;
            Sync(SessionDocuments, entries.Select(entry => {
                var key = entry.Value<string>("key");
                var byAgent = entry.Value<bool?>("opened_by_agent") == true;
                return new AgentPanelDocumentRow(key, entry.Value<string>("title"), byAgent ? strings.Text("AgentPanel.Documents.OpenedByAgent") : null) {
                    RemoveCommand = removable && !byAgent ? new AgentPanelCommand(() => Act(() => backend.Remove(key))) : null,
                    CloseCommand = byAgent ? new AgentPanelCommand(() => Post(onError => backend.Close(key, onError))) : null,
                };
            }).ToList());
        }

        private void DescribeOthers(List<AgentPanelOpenDocument> others) {
            HasOtherDocuments = others.Count > 0;
            Sync(OtherDocuments, others.Select(document => new AgentPanelDocumentRow(document.Key, document.Title, ActiveNote(document)) {
                AddCommand = new AgentPanelCommand(() => Post(onError => backend.Add(document.Key, onError))),
            }).ToList());
        }

        private string ActiveNote(AgentPanelOpenDocument document) {
            return document.IsActive ? strings.Text("AgentPanel.Documents.Active") : null;
        }

        /// <remarks>
        /// Keeps the rows the list shows when only ticks changed, so a click isn't lost to a list
        /// rebuilt under the mouse.
        /// </remarks>
        private static void Sync(ObservableCollection<AgentPanelDocumentRow> rows, List<AgentPanelDocumentRow> fresh) {
            if (rows.Select(row => row.Signature).SequenceEqual(fresh.Select(row => row.Signature))) {
                for (var index = 0; index < rows.Count; index++)
                    rows[index].ShowChosen(fresh[index].IsChosen);
                return;
            }
            rows.Clear();
            foreach (var row in fresh)
                rows.Add(row);
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

        private string DescribeDocument(JObject session, bool anyDocument, bool startsAutomatically) {
            switch (StateKind) {
                case "off":
                    return strings.Text("AgentPanel.Document.HostOff");
                case "active":
                case "paused":
                    return strings.Format("AgentPanel.Document.Since", LocalTime(session.Value<string>("started")));
                default:
                    if (startsAutomatically)
                        return strings.Text("AgentPanel.Document.Auto");
                    if (!anyDocument)
                        return strings.Text("AgentPanel.Document.NoDocument");
                    return strings.Text("AgentPanel.Document.Ready");
            }
        }

        private static List<JObject> Entries(JObject session) {
            return (session["documents"] as JArray ?? new JArray())
                .OfType<JObject>()
                .Where(document => !string.IsNullOrEmpty(document.Value<string>("key")))
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
