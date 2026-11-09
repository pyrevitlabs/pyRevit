using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Revit-free matching of a <c>document</c> value that isn't a key against the open documents'
    /// titles and paths, so the refusal can tell the caller which key it meant.
    /// </summary>
    /// <remarks>
    /// Invariant: requests name documents only by key. A title or path never selects a document;
    /// it only fills the hint in <c>unknown_document</c>, because titles aren't unique and an
    /// unsaved document has no path.
    /// A value with a directory separator is a path and is compared, normalised, with a document's
    /// path only; anything else is a title and is compared with its title only. Both ignore case.
    /// </remarks>
    internal static class AgentDocumentBinding {
        public static bool Matches(string requested, string title, string path) {
            if (string.IsNullOrWhiteSpace(requested))
                return false;
            if (!LooksLikePath(requested))
                return string.Equals(requested, title, StringComparison.OrdinalIgnoreCase);
            if (string.IsNullOrEmpty(path))
                return false;
            return string.Equals(Normalize(requested), Normalize(path), StringComparison.OrdinalIgnoreCase);
        }

        /// <returns>
        /// The one open document whose title or path <paramref name="requested"/> is, or null
        /// when none or several are.
        /// </returns>
        public static (string Key, string Title, string Path)? Named(
            string requested, IEnumerable<(string Key, string Title, string Path)> open) {
            var matches = open.Where(document => Matches(requested, document.Title, document.Path)).Take(2).ToList();
            return matches.Count == 1 ? matches[0] : ((string, string, string)?)null;
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
