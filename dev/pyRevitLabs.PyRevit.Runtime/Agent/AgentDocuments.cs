using System;
using System.Collections.Generic;
using System.Linq;

using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Tracks the documents open in Revit around an agent run, and closes the background
    /// documents a run leaves behind.
    /// </summary>
    /// <remarks>
    /// A background document is a non-linked document with no view open in Revit: one created
    /// with <c>NewProjectDocument</c> or <c>NewFamilyDocument</c>, or opened with
    /// <c>OpenDocumentFile</c> or <c>EditFamily</c>. A later run can't change it, because it was
    /// open when that run started, so leaving it open only holds memory. A session that leaked
    /// dozens of them ended in a native crash of Revit.
    /// Invariant: documents open when the run started, linked documents, and documents with an
    /// open view (such as one opened with <c>OpenAndActivateDocument</c>) are never closed.
    /// </remarks>
    internal static class AgentDocuments {
        public static List<Document> Snapshot(Autodesk.Revit.ApplicationServices.Application app) {
            return app.Documents.Cast<Document>().ToList();
        }

        /// <summary>
        /// Whether two references are the same open document. Documents are compared by Revit's
        /// identity, never by title or path, and a closed document matches nothing.
        /// </summary>
        public static bool IsSame(Document first, Document second) {
            if (first != null && ReferenceEquals(first, second))
                return true;
            try {
                return first != null && second != null && first.IsValidObject && second.IsValidObject && first.Equals(second);
            }
            catch (Exception) {
                return false;
            }
        }

        public static bool IsBackground(Document doc) {
            if (doc.IsLinked)
                return false;
            try {
                return new UIDocument(doc).GetOpenUIViews().Count == 0;
            }
            catch (Exception) {
                return false;
            }
        }

        /// <summary>
        /// Closes, without saving, every background document that wasn't open when the run
        /// started. Must run on the Revit main thread after the run guard is disposed.
        /// </summary>
        /// <returns>The closed documents' titles, and any that refused to close.</returns>
        public static JObject CloseLeftovers(Autodesk.Revit.ApplicationServices.Application app, List<Document> openAtStart) {
            var leftovers = app.Documents.Cast<Document>()
                .Where(open => !openAtStart.Any(before => before.Equals(open)) && IsBackground(open))
                .ToList();
            var closed = new JArray();
            var failed = new JArray();
            foreach (var leftover in leftovers) {
                var title = leftover.Title;
                try {
                    if (leftover.Close(false))
                        closed.Add(title);
                    else
                        failed.Add(title);
                }
                catch (Exception ex) {
                    failed.Add($"{title}: {ex.Message}");
                }
            }
            return new JObject { ["closed"] = closed, ["failed"] = failed };
        }

        public static JArray Describe(UIApplication uiApp) {
            var active = uiApp.ActiveUIDocument?.Document;
            return new JArray(uiApp.Application.Documents.Cast<Document>().Select(open => new JObject {
                ["title"] = open.Title,
                ["path"] = open.PathName,
                ["active"] = active != null && active.Equals(open),
                ["linked"] = open.IsLinked,
                ["background"] = IsBackground(open),
                ["modified"] = open.IsModified,
            }));
        }
    }
}
