using System;
using System.IO;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Revit-free rules for binding a run to the document the caller inspected.
    /// </summary>
    /// <remarks>
    /// The requested value is a title or path as returned by <c>get_context</c>. A value with a
    /// directory separator is a path and is compared, normalised, with the active document's
    /// path only; anything else is a title and is compared with the active title only. Titles are
    /// not unique, so two open documents that share a title can only be told apart by path.
    /// </remarks>
    internal static class AgentDocumentBinding {
        public const string ChangedCode = "document_changed";

        /// <summary>
        /// Reads the optional <c>document</c> request parameter.
        /// </summary>
        /// <returns>The requested document, or <c>null</c> when the parameter is absent or null.</returns>
        /// <exception cref="AgentException"><c>invalid_params</c> when it is not a non-blank string.</exception>
        public static string Parse(JToken token) {
            if (token == null || token.Type == JTokenType.Null)
                return null;
            if (token.Type != JTokenType.String || string.IsNullOrWhiteSpace(token.Value<string>()))
                throw new AgentException("invalid_params", "'document' must be the non-empty title or path string returned by get_context.");
            return token.Value<string>();
        }

        public static bool Matches(string requested, string activeTitle, string activePath) {
            if (string.IsNullOrWhiteSpace(requested))
                return true;
            if (!LooksLikePath(requested))
                return string.Equals(requested, activeTitle, StringComparison.OrdinalIgnoreCase);
            if (string.IsNullOrEmpty(activePath))
                return false;
            return string.Equals(Normalize(requested), Normalize(activePath), StringComparison.OrdinalIgnoreCase);
        }

        /// <summary>
        /// The refusal for a run whose requested document is not the active one. Nothing has run,
        /// so <c>data.outcome</c> is <c>not_run</c>.
        /// </summary>
        public static AgentException Refusal(string requested, string activeTitle) {
            var exception = new AgentException(
                ChangedCode,
                activeTitle == null
                    ? $"The run was meant for '{requested}' but Revit has no active document. Nothing ran."
                    : $"The run was meant for '{requested}' but the active document is '{activeTitle}'. Nothing ran; activate the intended document or call get_context again.");
            exception.Details["outcome"] = "not_run";
            return exception;
        }

        private static bool LooksLikePath(string value) {
            return value.IndexOf('\\') >= 0 || value.IndexOf('/') >= 0;
        }

        private static string Normalize(string path) {
            try {
                return Path.GetFullPath(path).TrimEnd('\\', '/');
            }
            catch (Exception) {
                return path.TrimEnd('\\', '/');
            }
        }
    }
}
