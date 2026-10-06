using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Globalization;
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
        /// Selects and zooms to elements of <paramref name="document"/>, refusing when another
        /// document is active. A failure is reported through <paramref name="onError"/> on the UI
        /// thread.
        /// </summary>
        void ShowElements(IList<long> ids, string document, Action<string> onError);

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
        private readonly IAgentPanelBackend backend;
        private readonly Func<string, string> text;
        private string errorText;

        public AgentPanelViewModel(IAgentPanelBackend backend, Func<string, string> text) {
            this.backend = backend;
            this.text = text;
            StartCommand = new AgentPanelCommand(Start);
            PauseCommand = new AgentPanelCommand(() => Act(backend.Pause));
            ResumeCommand = new AgentPanelCommand(() => Act(backend.Resume));
            EndCommand = new AgentPanelCommand(() => Act(backend.End));
            AcceptCommand = new AgentPanelCommand(() => {
                if (StateKind == "paused")
                    Act(backend.Resume);
                else
                    Start();
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
        public string StartLabel { get; private set; }
        public bool CanStart { get; private set; }
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
            var activeTitle = backend.ActiveDocumentTitle;
            StateKind = running ? session.Value<string>("state") ?? "inactive" : "off";

            StateLabel = Text("AgentPanel.State." + Capitalize(StateKind));
            CanStart = StateKind == "inactive" && activeTitle != null;
            CanPause = StateKind == "active";
            CanResume = StateKind == "paused";
            CanEnd = CanPause || CanResume;
            StartLabel = activeTitle == null ? string.Empty : Format("AgentPanel.Start", activeTitle);
            DocumentLine = DescribeDocument(session, activeTitle);

            var request = running ? session["pending_request"] as JObject : null;
            HasRequest = request != null;
            RequestReason = request?.Value<string>("reason") ?? Text("AgentPanel.Request.NoReason");
            RequestTime = request == null ? string.Empty : Format("AgentPanel.Request.Time", LocalTime(request.Value<string>("requested")));
            CanAccept = StateKind == "paused" || CanStart;
            AcceptLabel = StateKind == "paused" ? Text("AgentPanel.Resume") : StartLabel;

            PolicyText = Text("AgentPanel.Policy." + Capitalize(backend.Policy ?? "ask"));
            var activity = backend.Activity;
            ClientText = activity?.Client ?? Text("AgentPanel.Client.Unknown");
            DescribeLast(activity?.Last);
            DescribeWaiting(activity);
            Log.Update(activity?.History ?? new AgentRequestRecord[0]);

            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(string.Empty));
        }

        private void ShowElement(AgentLogElement element) {
            errorText = null;
            backend.ShowElements(new[] { element.Id }, element.Document, message => {
                errorText = message;
                Refresh();
            });
            Refresh();
        }

        private void Start() {
            errorText = null;
            backend.Start(message => {
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

        private string DescribeDocument(JObject session, string activeTitle) {
            switch (StateKind) {
                case "off":
                    return Text("AgentPanel.Document.HostOff");
                case "active":
                case "paused":
                    return Format("AgentPanel.Document.Bound", session.Value<string>("document"), LocalTime(session.Value<string>("started")));
                default:
                    if (activeTitle == null)
                        return Text("AgentPanel.Document.NoDocument");
                    return Text(session.Value<bool?>("required") == false ? "AgentPanel.Document.Optional" : "AgentPanel.Document.Ready");
            }
        }

        private void DescribeLast(AgentRequestRecord last) {
            HasLast = last != null && last.FinishedUtc.HasValue;
            LastText = HasLast
                ? Format("AgentPanel.Last", Name(last), LocalTime(last.FinishedUtc.Value), last.Outcome)
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
                WaitingText = Format("AgentPanel.Waiting.Approval", Name(current));
                return;
            }
            if (current.Started) {
                WaitingText = Format("AgentPanel.Waiting.Running", Name(current));
                return;
            }
            var dialogs = backend.OpenDialogs();
            WaitingText = dialogs != null && dialogs.Count > 0
                ? Format("AgentPanel.Waiting.Dialog", Name(current), string.Join(", ", dialogs))
                : Format("AgentPanel.Waiting.Revit", Name(current));
        }

        private string Name(AgentRequestRecord record) {
            var kind = Text("AgentPanel.Kind." + record.Kind);
            return string.IsNullOrEmpty(record.Title) ? kind : kind + ": " + record.Title;
        }

        private string Text(string key) {
            return text(key) ?? key;
        }

        private string Format(string key, params object[] values) {
            return string.Format(CultureInfo.CurrentCulture, Text(key), values);
        }

        private static string LocalTime(string utc) {
            return DateTime.TryParse(utc, CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out var parsed)
                ? LocalTime(parsed)
                : string.Empty;
        }

        private static string LocalTime(DateTime utc) {
            return utc.ToLocalTime().ToString("HH:mm", CultureInfo.CurrentCulture);
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
