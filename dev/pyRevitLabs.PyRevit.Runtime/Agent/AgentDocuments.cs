using System;
using System.Collections.Generic;
using System.Linq;

using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Tracks the documents open in Revit: the keys agents name them by, and the background
    /// documents a run leaves behind, which it closes.
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
        /// <summary>The keys agents name open documents by in this Revit process.</summary>
        public static readonly AgentDocumentKeys Keys = new AgentDocumentKeys();

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
                ["key"] = Keys.KeyOf(open),
                ["title"] = open.Title,
                ["path"] = open.PathName,
                ["active"] = active != null && active.Equals(open),
                ["linked"] = open.IsLinked,
                ["background"] = IsBackground(open),
                ["modified"] = open.IsModified,
            }));
        }
    }

    /// <summary>
    /// The keys agents name open documents by: <c>key</c> in the context's
    /// <c>open_documents</c> and <c>document</c>.
    /// </summary>
    /// <remarks>
    /// A key is an opaque id given to a document the first time it is described. Titles aren't
    /// unique and unsaved documents have no path, so neither can name a document.
    /// Invariants: a key names one document for the life of the process and is never given to
    /// another. A closed document's key names nothing, and the same file opened again gets a new
    /// key, so element ids read before it closed are never applied to what replaced it.
    /// Comparing documents uses the Revit API, so call members on the Revit main thread.
    /// </remarks>
    internal sealed class AgentDocumentKeys {
        private const string Prefix = "doc-";

        private readonly object sync = new object();
        private readonly List<(Document Document, string Key)> known = new List<(Document, string)>();
        private int issued;

        /// <summary>The document's key, given now if it has none yet.</summary>
        public string KeyOf(Document document) {
            if (document == null)
                throw new ArgumentNullException(nameof(document));
            lock (sync) {
                ForgetClosed();
                foreach (var entry in known)
                    if (AgentDocuments.IsSame(entry.Document, document))
                        return entry.Key;
                var key = Prefix + ++issued;
                known.Add((document, key));
                return key;
            }
        }

        /// <summary>The open document <paramref name="key"/> names, or null when it names none.</summary>
        public Document Find(string key) {
            if (string.IsNullOrEmpty(key))
                return null;
            lock (sync) {
                ForgetClosed();
                foreach (var entry in known)
                    if (entry.Key == key)
                        return entry.Document;
                return null;
            }
        }

        private void ForgetClosed() {
            known.RemoveAll(entry => !IsOpen(entry.Document));
        }

        private static bool IsOpen(Document document) {
            try {
                return document.IsValidObject;
            }
            catch (Exception) {
                return false;
            }
        }
    }
}
