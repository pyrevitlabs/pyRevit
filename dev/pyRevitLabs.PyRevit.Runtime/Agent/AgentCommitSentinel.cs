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
    /// Only touched on the Revit main thread.
    /// </remarks>
    internal static class AgentCommitSentinel {
        private const int SampleSize = 200;

        private static string documentKey;
        private static string runId;
        private static string title;
        private static List<ElementId> sample = new List<ElementId>();

        public static void Remember(Document doc, string committedRunId, string committedTitle, IEnumerable<ElementId> added) {
            documentKey = KeyOf(doc);
            runId = committedRunId;
            title = committedTitle;
            sample = added.Take(SampleSize).ToList();
        }

        /// <summary>
        /// Returns a warning when elements from the last commit no longer exist, or null.
        /// Forgets the commit once it has warned, so the warning is given once.
        /// </summary>
        /// <param name="afterRollback">
        /// True when checking right after this run rolled back, which makes the warning say the
        /// rollback removed them.
        /// </param>
        public static string Check(Document doc, bool afterRollback) {
            if (sample.Count == 0 || documentKey != KeyOf(doc))
                return null;
            var missing = sample.Count(id => doc.GetElement(id) == null);
            if (missing == 0)
                return null;

            var message = afterRollback
                ? $"Rolling back this run removed {missing} of {sample.Count} checked elements that run {runId} ('{title}') "
                    + "had committed. Revit undid that commit together with this run. Rebuild that stage, and verify it after "
                    + "the next dry run."
                : $"{missing} of {sample.Count} checked elements committed by run {runId} ('{title}') no longer exist. "
                    + "They were undone or deleted since; check before building on them.";
            sample = new List<ElementId>();
            return message;
        }

        private static string KeyOf(Document doc) {
            return string.IsNullOrEmpty(doc.PathName) ? "unsaved:" + doc.Title : doc.PathName;
        }
    }
}
