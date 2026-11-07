using System;
using System.Collections.Generic;
using System.Linq;

using Autodesk.Revit.DB;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Remembers a sample of the elements the last committed agent run created, and reports
    /// when they disappear.
    /// </summary>
    /// <remarks>
    /// A dry run's rollback must never touch committed work, but it did once: rolling back a
    /// dry run right after a commit that used <c>StairsEditScope</c> took that commit with it,
    /// silently, and Revit only logged "UndoElement::simplify PROBLEMS" in its journal. This
    /// check turns such a loss into a warning in the very run that caused it. It also catches
    /// the user undoing or deleting agent work between runs, which is legitimate but worth
    /// telling the agent before it builds on elements that are gone.
    /// Each open document keeps its own last commit, held by the <see cref="Document"/> itself
    /// rather than its title or path, so two unsaved documents with the same title, or a commit
    /// to another document, never mix up the samples. Closed documents are forgotten.
    /// Only touched on the Revit main thread.
    /// </remarks>
    internal static class AgentCommitSentinel {
        private const int SampleSize = 200;

        private sealed class Commit {
            public Document Document;
            public string RunId;
            public string Title;
            public List<ElementId> Sample;
        }

        private static readonly List<Commit> commits = new List<Commit>();

        /// <summary>
        /// Remembers a commit to <paramref name="doc"/>, replacing only that document's last one.
        /// </summary>
        public static void Remember(Document doc, string committedRunId, string committedTitle, IEnumerable<ElementId> added) {
            commits.RemoveAll(commit => !IsOpen(commit.Document) || commit.Document.Equals(doc));
            var sample = added.Take(SampleSize).ToList();
            if (sample.Count > 0)
                commits.Add(new Commit { Document = doc, RunId = committedRunId, Title = committedTitle, Sample = sample });
        }

        /// <summary>
        /// Returns a warning when elements from the last commit to <paramref name="doc"/> no
        /// longer exist, or null. Forgets that commit once it has warned, so the warning is given
        /// once.
        /// </summary>
        /// <param name="afterRollback">
        /// True when checking right after this run rolled back, which makes the warning say the
        /// rollback removed them.
        /// </param>
        public static string Check(Document doc, bool afterRollback) {
            commits.RemoveAll(commit => !IsOpen(commit.Document));
            var last = commits.FirstOrDefault(commit => commit.Document.Equals(doc));
            if (last == null)
                return null;
            var missing = last.Sample.Count(id => doc.GetElement(id) == null);
            if (missing == 0)
                return null;

            var message = afterRollback
                ? $"Rolling back this run removed {missing} of {last.Sample.Count} checked elements that run {last.RunId} ('{last.Title}') "
                    + "had committed. Revit undid that commit together with this run. Rebuild that stage, and verify it after "
                    + "the next dry run."
                : $"{missing} of {last.Sample.Count} checked elements committed by run {last.RunId} ('{last.Title}') no longer exist. "
                    + "They were undone or deleted since; check before building on them.";
            commits.Remove(last);
            return message;
        }

        private static bool IsOpen(Document doc) {
            try {
                return doc.IsValidObject;
            }
            catch (Exception) {
                return false;
            }
        }
    }
}
