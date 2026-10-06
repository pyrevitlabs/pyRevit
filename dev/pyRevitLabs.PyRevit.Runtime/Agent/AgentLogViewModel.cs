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
    /// An element a run added or changed, which the user can click to select and zoom to.
    /// </summary>
    internal sealed class AgentLogElement {
        public AgentLogElement(long id, string label, string document, Action<AgentLogElement> select) {
            Id = id;
            Label = label;
            Document = document;
            SelectCommand = new AgentPanelCommand(() => select(this));
        }

        public long Id { get; }
        public string Label { get; }

        /// <summary>Title of the document the element belongs to.</summary>
        public string Document { get; }

        public ICommand SelectCommand { get; }
    }

    /// <summary>
    /// One request in the agent log: a one-line summary, and details shown when expanded.
    /// </summary>
    internal sealed class AgentLogEntryViewModel : INotifyPropertyChanged {
        private bool isExpanded;
        private bool isVisible = true;

        public AgentLogEntryViewModel(AgentRequestRecord record, Func<string, string> text, Action<AgentLogElement> select) {
            var log = new AgentLogText(text);
            var details = record.Details;
            var kind = log.Text("AgentPanel.Kind." + record.Kind);

            Id = record.Id;
            IsLookup = record.IsLookup;
            Title = string.IsNullOrEmpty(record.Title) ? kind : record.Title;
            StatusKind = StatusOf(record.Outcome);
            Summary = log.Summary(record, kind);
            Reason = string.IsNullOrEmpty(record.Reason) ? null : log.Format("AgentPanel.Log.Reason", record.Reason);
            Flags = log.Flags(details);
            Changes = log.Changes(details);
            Categories = CategoriesOf(details);
            Elements = ElementsOf(details, select);
            Script = details?.Value<string>("script");
            Output = details?.Value<string>("output");
            Error = ErrorOf(details);
            Engine = string.IsNullOrEmpty(details?.Value<string>("engine")) ? null : log.Format("AgentPanel.Log.Engine", details.Value<string>("engine"));
            RunFolder = string.IsNullOrEmpty(details?.Value<string>("run_dir")) ? null : log.Format("AgentPanel.Log.RunFolder", details.Value<string>("run_dir"));
            ToggleCommand = new AgentPanelCommand(() => IsExpanded = !IsExpanded);
        }

        public event PropertyChangedEventHandler PropertyChanged;

        public long Id { get; }
        public bool IsLookup { get; }
        public string Title { get; }

        /// <summary><c>ok</c>, <c>committed</c>, <c>rejected</c> or <c>error</c>.</summary>
        public string StatusKind { get; }

        public string Summary { get; }
        public string Reason { get; }
        public IList<string> Flags { get; }
        public string Changes { get; }
        public string Categories { get; }
        public IList<AgentLogElement> Elements { get; }
        public string Script { get; }
        public string Output { get; }
        public string Error { get; }
        public string Engine { get; }
        public string RunFolder { get; }

        public bool HasReason => Reason != null;
        public bool HasFlags => Flags.Count > 0;
        public bool HasChanges => Changes != null;
        public bool HasCategories => Categories != null;
        public bool HasElements => Elements.Count > 0;
        public bool HasScript => !string.IsNullOrEmpty(Script);
        public bool HasOutput => !string.IsNullOrEmpty(Output);
        public bool HasError => Error != null;
        public bool HasEngine => Engine != null;
        public bool HasRunFolder => RunFolder != null;

        public ICommand ToggleCommand { get; }

        public bool IsExpanded {
            get => isExpanded;
            set {
                if (isExpanded == value)
                    return;
                isExpanded = value;
                PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(IsExpanded)));
            }
        }

        public bool IsVisible {
            get => isVisible;
            set {
                if (isVisible == value)
                    return;
                isVisible = value;
                PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(IsVisible)));
            }
        }

        private static string StatusOf(string outcome) {
            switch (outcome) {
                case "ok":
                case "committed":
                case "rejected":
                    return outcome;
                default:
                    return "error";
            }
        }

        private static string CategoriesOf(JObject details) {
            if (!(details?["by_category"] is JObject byCategory) || byCategory.Count == 0)
                return null;
            return string.Join("\n", byCategory.Properties().Select(category => category.Name + ": " + category.Value));
        }

        private static IList<AgentLogElement> ElementsOf(JObject details, Action<AgentLogElement> select) {
            var document = details?.Value<string>("document");
            return (details?["elements"] as JArray ?? new JArray())
                .OfType<JObject>()
                .Where(element => element["id"] != null)
                .Select(element => {
                    var id = element.Value<long>("id");
                    var name = element.Value<string>("name") ?? element.Value<string>("category");
                    var label = string.IsNullOrEmpty(name) ? id.ToString(CultureInfo.InvariantCulture) : name + " " + id.ToString(CultureInfo.InvariantCulture);
                    return new AgentLogElement(id, label, document, select);
                })
                .ToList();
        }

        private static string ErrorOf(JObject details) {
            if (!(details?["error"] is JObject error))
                return null;
            var heading = string.Join(": ", new[] { error.Value<string>("type"), error.Value<string>("message") }.Where(part => !string.IsNullOrEmpty(part)));
            var traceback = error.Value<string>("traceback");
            return string.IsNullOrEmpty(traceback) ? heading : heading + "\n\n" + traceback;
        }
    }

    /// <summary>
    /// The requests of one session, or of requests made without one, newest first.
    /// </summary>
    internal sealed class AgentLogGroupViewModel : INotifyPropertyChanged {
        private bool isVisible = true;

        public AgentLogGroupViewModel(string key, string header) {
            Key = key;
            Header = header;
        }

        public event PropertyChangedEventHandler PropertyChanged;

        /// <summary>The session id, or an empty string for requests made without a session.</summary>
        public string Key { get; }

        public string Header { get; }
        public ObservableCollection<AgentLogEntryViewModel> Entries { get; } = new ObservableCollection<AgentLogEntryViewModel>();

        public bool IsVisible {
            get => isVisible;
            set {
                if (isVisible == value)
                    return;
                isVisible = value;
                PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(IsVisible)));
            }
        }
    }

    /// <summary>
    /// The agent log the panel shows: finished requests grouped by session, the group with the
    /// latest request first.
    /// </summary>
    /// <remarks>
    /// <see cref="Update"/> changes the collections in place, adding new requests and dropping
    /// ones the history no longer holds, so rows the user expanded stay expanded. Must be used
    /// on the UI thread. Lookups are hidden unless <see cref="ShowLookups"/> is on.
    /// </remarks>
    internal sealed class AgentLogViewModel : INotifyPropertyChanged {
        private readonly Func<string, string> text;
        private readonly Action<AgentLogElement> select;
        private readonly Dictionary<long, AgentLogEntryViewModel> entries = new Dictionary<long, AgentLogEntryViewModel>();
        private bool showLookups;

        public AgentLogViewModel(Func<string, string> text, Action<AgentLogElement> select) {
            this.text = text;
            this.select = select;
        }

        public event PropertyChangedEventHandler PropertyChanged;

        public ObservableCollection<AgentLogGroupViewModel> Groups { get; } = new ObservableCollection<AgentLogGroupViewModel>();

        public bool ShowLookups {
            get => showLookups;
            set {
                if (showLookups == value)
                    return;
                showLookups = value;
                ApplyFilter();
                PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(ShowLookups)));
            }
        }

        public bool IsEmpty { get; private set; } = true;

        /// <param name="history">Finished requests, oldest first.</param>
        public void Update(IReadOnlyList<AgentRequestRecord> history) {
            var kept = new HashSet<long>(history.Select(record => record.Id));
            foreach (var group in Groups.ToList()) {
                foreach (var entry in group.Entries.Where(entry => !kept.Contains(entry.Id)).ToList()) {
                    group.Entries.Remove(entry);
                    entries.Remove(entry.Id);
                }
                if (group.Entries.Count == 0)
                    Groups.Remove(group);
            }

            foreach (var record in history) {
                if (entries.ContainsKey(record.Id))
                    continue;
                var entry = new AgentLogEntryViewModel(record, text, select);
                entries[record.Id] = entry;
                GroupFor(record).Entries.Insert(0, entry);
            }
            ApplyFilter();
        }

        private AgentLogGroupViewModel GroupFor(AgentRequestRecord record) {
            var key = record.SessionId ?? string.Empty;
            var group = Groups.FirstOrDefault(candidate => candidate.Key == key);
            if (group == null) {
                group = new AgentLogGroupViewModel(key, Header(record));
                Groups.Insert(0, group);
            }
            else if (Groups.IndexOf(group) != 0)
                Groups.Move(Groups.IndexOf(group), 0);
            return group;
        }

        private string Header(AgentRequestRecord record) {
            var log = new AgentLogText(text);
            if (record.SessionId == null)
                return log.Text("AgentPanel.Log.NoSession");
            return log.Format("AgentPanel.Log.Session", record.SessionDocument ?? record.SessionId, AgentLogText.LocalTime(record.ArrivedUtc, "HH:mm"));
        }

        private void ApplyFilter() {
            var anyVisible = false;
            foreach (var group in Groups) {
                var groupVisible = false;
                foreach (var entry in group.Entries) {
                    entry.IsVisible = showLookups || !entry.IsLookup;
                    groupVisible |= entry.IsVisible;
                }
                group.IsVisible = groupVisible;
                anyVisible |= groupVisible;
            }
            IsEmpty = !anyVisible;
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(nameof(IsEmpty)));
        }
    }

    /// <summary>
    /// The log's wording, from the panel's string resources.
    /// </summary>
    internal sealed class AgentLogText {
        private readonly Func<string, string> text;

        public AgentLogText(Func<string, string> text) {
            this.text = text;
        }

        public string Text(string key) {
            return text(key) ?? key;
        }

        public string Format(string key, params object[] values) {
            return string.Format(CultureInfo.CurrentCulture, Text(key), values);
        }

        public static string LocalTime(DateTime utc, string format) {
            return utc.ToLocalTime().ToString(format, CultureInfo.CurrentCulture);
        }

        public string Summary(AgentRequestRecord record, string kind) {
            var finished = record.FinishedUtc ?? record.ArrivedUtc;
            var summary = Format("AgentPanel.Log.Summary", kind, LocalTime(finished, "HH:mm:ss"), record.Outcome, Duration(record));
            var approval = record.Details?.Value<string>("approval");
            return string.IsNullOrEmpty(approval)
                ? summary
                : Format("AgentPanel.Log.WithApproval", summary, Text("AgentPanel.Log.Approval." + approval));
        }

        public IList<string> Flags(JObject details) {
            var flags = new List<string>();
            if (details == null)
                return flags;
            var unreverted = (details["unreverted_documents"] as JArray)?.Values<string>().ToList() ?? new List<string>();
            if (unreverted.Count > 0)
                flags.Add(Format("AgentPanel.Log.Flag.CloseWithoutSaving", string.Join(", ", unreverted)));
            else if ((details.Value<int?>("other_documents") ?? 0) > 0)
                flags.Add(Text("AgentPanel.Log.Flag.OtherDocument"));
            if (details.Value<string>("mode") == "modify" && details.Value<string>("decision") == "no_changes")
                flags.Add(Text("AgentPanel.Log.Flag.NoChanges"));
            var warning = (details["warnings"] as JArray)?.FirstOrDefault()?.ToString();
            if (!string.IsNullOrEmpty(warning))
                flags.Add(Format("AgentPanel.Log.Flag.Warning", warning));
            return flags;
        }

        public string Changes(JObject details) {
            if (details == null)
                return null;
            var added = details.Value<int?>("added") ?? 0;
            var modified = details.Value<int?>("modified") ?? 0;
            var deleted = details.Value<int?>("deleted") ?? 0;
            return added + modified + deleted == 0 ? null : Format("AgentPanel.Log.Changes", added, modified, deleted);
        }

        private string Duration(AgentRequestRecord record) {
            var elapsedMs = record.Details?.Value<double?>("elapsed_ms");
            var seconds = elapsedMs.HasValue
                ? elapsedMs.Value / 1000
                : ((record.FinishedUtc ?? record.ArrivedUtc) - (record.StartedUtc ?? record.ArrivedUtc)).TotalSeconds;
            return Format("AgentPanel.Log.Duration", seconds);
        }
    }
}
