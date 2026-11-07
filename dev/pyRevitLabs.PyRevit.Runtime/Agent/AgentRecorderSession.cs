using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

using Autodesk.Revit.ApplicationServices;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Events;
using Autodesk.Revit.UI;
using Autodesk.Revit.UI.Events;

using pyRevitLabs.Json.Linq;
using pyRevitLabs.NLog;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// The Revit event subscriptions of one recording: element changes per transaction, view
    /// changes, selection changes, dialogs, failures and throttled screenshots.
    /// </summary>
    /// <remarks>
    /// Read-only by design: no handler cancels, answers or changes anything in Revit, and a
    /// handler that throws is logged and swallowed so recording can never break a command.
    /// Screenshots are never taken inside an event handler: a trigger only marks one as
    /// pending, and it is taken on the next <c>Idling</c> when the throttle allows, because
    /// Revit can't export an image while it is inside a transaction or a dialog.
    /// Native Revit commands are visible only through their transaction names, since Revit
    /// offers no event for an arbitrary command; this is the best effort the recorder makes.
    /// Invariant: <see cref="Dispose"/> unsubscribes every handler.
    /// </remarks>
    internal sealed class AgentRecorderSession : IDisposable {
        private const int MaxElementsPerChange = 25;
        private const int MaxSelectionIds = 20;
        private const int MaxElementsScanned = 200;

        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        private readonly UIApplication uiApp;
        private readonly Application app;
        private readonly AgentRecordingStore store;
        private readonly AgentScreenshotThrottle throttle;
        private string pendingScreenshot;
        private HashSet<long> lastSelection = new HashSet<long>();

        public AgentRecorderSession(UIApplication uiApp, AgentRecordingStore store) {
            this.uiApp = uiApp;
            app = uiApp.Application;
            this.store = store;
            throttle = new AgentScreenshotThrottle(
                TimeSpan.FromSeconds(store.Options.ScreenshotIntervalSeconds), store.Options.MaxScreenshots);
        }

        public void Attach() {
            app.DocumentChanged += OnDocumentChanged;
            app.FailuresProcessing += OnFailuresProcessing;
            uiApp.ViewActivated += OnViewActivated;
            uiApp.DialogBoxShowing += OnDialogBoxShowing;
            uiApp.Idling += OnIdling;
        }

        public void Dispose() {
            app.DocumentChanged -= OnDocumentChanged;
            app.FailuresProcessing -= OnFailuresProcessing;
            uiApp.ViewActivated -= OnViewActivated;
            uiApp.DialogBoxShowing -= OnDialogBoxShowing;
            uiApp.Idling -= OnIdling;
        }

        private void OnDocumentChanged(object sender, DocumentChangedEventArgs e) {
            Guarded(() => {
                var doc = e.GetDocument();
                var added = e.GetAddedElementIds();
                var modified = e.GetModifiedElementIds();
                var deleted = e.GetDeletedElementIds();
                if (added.Count == 0 && modified.Count == 0 && deleted.Count == 0)
                    return;
                AgentRecorder.Append("element_changes", new JObject {
                    ["document"] = doc.Title,
                    ["operation"] = e.Operation.ToString(),
                    ["transactions"] = new JArray(e.GetTransactionNames()),
                    ["added_count"] = added.Count,
                    ["modified_count"] = modified.Count,
                    ["deleted_count"] = deleted.Count,
                    ["added"] = DescribeElements(doc, added),
                    ["modified"] = DescribeElements(doc, modified),
                    ["deleted_ids"] = new JArray(deleted.Take(MaxElementsPerChange).Select(AgentIds.ToValue)),
                });
                RequestScreenshot("commit");
            });
        }

        private void OnFailuresProcessing(object sender, FailuresProcessingEventArgs e) {
            Guarded(() => {
                var accessor = e.GetFailuresAccessor();
                var messages = new JArray();
                foreach (var message in accessor.GetFailureMessages().Take(MaxElementsPerChange))
                    messages.Add(new JObject {
                        ["severity"] = message.GetSeverity().ToString(),
                        ["description"] = AgentRecordingStore.Truncate(message.GetDescriptionText()),
                    });
                if (messages.Count > 0)
                    AgentRecorder.Append("failures", new JObject {
                        ["transaction"] = accessor.GetTransactionName(),
                        ["messages"] = messages,
                    });
            });
        }

        private void OnViewActivated(object sender, ViewActivatedEventArgs e) {
            Guarded(() => AgentRecorder.Append("view_activated", new JObject {
                ["document"] = e.Document?.Title,
                ["view"] = e.CurrentActiveView?.Name,
                ["view_id"] = e.CurrentActiveView == null ? (long?)null : AgentIds.ToValue(e.CurrentActiveView.Id),
                ["view_type"] = e.CurrentActiveView?.ViewType.ToString(),
            }));
        }

        private void OnDialogBoxShowing(object sender, DialogBoxShowingEventArgs e) {
            Guarded(() => {
                AgentRecorder.Append("dialog", new JObject {
                    ["dialog_id"] = e.DialogId,
                    ["message"] = AgentRecordingStore.Truncate((e as TaskDialogShowingEventArgs)?.Message),
                });
                RequestScreenshot("dialog");
            });
        }

        private void OnIdling(object sender, Autodesk.Revit.UI.Events.IdlingEventArgs e) {
            if (!AgentRecorder.IsCurrent(store)) {
                Dispose();
                return;
            }
            Guarded(() => {
                AgentRecorder.FlushOutput();
                if (store.Elapsed.TotalSeconds >= store.Options.MaxDurationSeconds) {
                    AgentRecorder.StopIfActive("max_duration");
                    return;
                }
                RecordSelectionChange();
                TakePendingScreenshot();
            });
        }

        private void RecordSelectionChange() {
            var uidoc = uiApp.ActiveUIDocument;
            if (uidoc == null)
                return;
            var selected = new HashSet<long>(uidoc.Selection.GetElementIds().Select(AgentIds.ToValue));
            if (selected.SetEquals(lastSelection))
                return;
            lastSelection = selected;
            var ids = selected.OrderBy(id => id).ToList();
            AgentRecorder.Append("selection_changed", new JObject {
                ["document"] = uidoc.Document.Title,
                ["count"] = ids.Count,
                ["ids"] = new JArray(ids.Take(MaxSelectionIds)),
            });
        }

        private void RequestScreenshot(string reason) {
            if (store.Options.Screenshots && pendingScreenshot == null)
                pendingScreenshot = reason;
        }

        private void TakePendingScreenshot() {
            var reason = pendingScreenshot;
            if (reason == null || uiApp.ActiveUIDocument == null || !throttle.TryAcquire(store.Elapsed))
                return;
            pendingScreenshot = null;
            try {
                var request = AgentCapture.Parse(new JObject { ["mode"] = "export", ["width"] = 1024 });
                var captured = (JObject)AgentCapture.Capture(uiApp, request);
                var source = captured.Value<string>("path");
                Directory.CreateDirectory(store.ScreenshotsDirectory);
                var name = "shot-" + throttle.Taken.ToString("D3") + ".png";
                File.Move(source, Path.Combine(store.ScreenshotsDirectory, name));
                AgentRecorder.Append("screenshot", new JObject {
                    ["reason"] = reason,
                    ["file"] = "screenshots/" + name,
                    ["view"] = captured["view"],
                });
            }
            catch (Exception ex) {
                throttle.Refund();
                AgentRecorder.Append("screenshot_failed", new JObject {
                    ["reason"] = reason,
                    ["error"] = AgentRecordingStore.Truncate(ex.Message),
                });
            }
        }

        private static JArray DescribeElements(Document doc, ICollection<ElementId> ids) {
            var described = new JArray();
            var candidates = ids.Take(MaxElementsScanned).OrderBy(id => doc.GetElement(id)?.Category == null);
            foreach (var id in candidates.Take(MaxElementsPerChange)) {
                var element = doc.GetElement(id);
                described.Add(new JObject {
                    ["id"] = AgentIds.ToValue(id),
                    ["category"] = element?.Category?.Name,
                    ["name"] = DescribeName(element),
                    ["location"] = DescribeLocation(element),
                });
            }
            return described;
        }

        private static string DescribeName(Element element) {
            try {
                if (element is FamilyInstance instance && instance.Symbol != null)
                    return instance.Symbol.FamilyName + ": " + instance.Symbol.Name;
                return element?.Name;
            }
            catch (Exception) {
                return null;
            }
        }

        private static JToken DescribeLocation(Element element) {
            try {
                if (element?.Location is LocationPoint point)
                    return new JObject { ["point"] = ToArray(point.Point) };
                if (element?.Location is LocationCurve curve)
                    return new JObject {
                        ["start"] = ToArray(curve.Curve.GetEndPoint(0)),
                        ["end"] = ToArray(curve.Curve.GetEndPoint(1)),
                    };
                var box = element?.get_BoundingBox(null);
                if (box != null)
                    return new JObject { ["min"] = ToArray(box.Min), ["max"] = ToArray(box.Max) };
            }
            catch (Exception) {
            }
            return null;
        }

        private static JArray ToArray(XYZ point) => new JArray(point.X, point.Y, point.Z);

        private void Guarded(Action action) {
            if (!AgentRecorder.IsCurrent(store))
                return;
            try {
                action();
            }
            catch (Exception ex) {
                logger.Debug("Session recorder handler failed: {0}", ex.Message);
            }
        }
    }
}
