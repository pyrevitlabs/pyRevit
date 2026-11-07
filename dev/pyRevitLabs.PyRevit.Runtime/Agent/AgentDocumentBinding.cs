using System;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Revit-free rule that decides whether a run's requested document is the active one.
    /// </summary>
    /// <remarks>
    /// The requested value is a title or path as returned by <c>get_context</c>. A document that
    /// has no path yet is matched by title only.
    /// </remarks>
    internal static class AgentDocumentBinding {
        public static bool Matches(string requested, string activeTitle, string activePath) {
            if (string.IsNullOrWhiteSpace(requested))
                return true;
            if (!string.IsNullOrEmpty(activePath)
                && string.Equals(requested, activePath, StringComparison.OrdinalIgnoreCase))
                return true;
            return !string.IsNullOrEmpty(activeTitle)
                && string.Equals(requested, activeTitle, StringComparison.OrdinalIgnoreCase);
        }
    }
}
