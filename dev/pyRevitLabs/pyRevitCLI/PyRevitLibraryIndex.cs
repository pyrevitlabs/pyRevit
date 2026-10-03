using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;

using pyRevitLabs.Json.Linq;

namespace pyRevitCLI {
    /// <summary>
    /// Serves <c>lookup_pyrevit_api</c>: the public API of pyrevitlib and rpw, indexed from the
    /// source files of the clone, so agents use the shared libraries instead of re-deriving
    /// Revit API recipes.
    /// </summary>
    /// <remarks>
    /// Symbols come from <see cref="PyRevitLibraryParser"/>, so the index needs neither Revit
    /// nor a Python install and reflects the clone as it is on disk. The index is rebuilt when
    /// a source file changes.
    /// </remarks>
    internal static class PyRevitLibraryIndex {
        private const int MaxResults = 15;
        private const int MaxModuleMembers = 200;
        private const int DefaultAutomationResults = 25;
        private const int MaxAutomationResults = 50;

        private static readonly string[] IndexedPaths = {
            "pyrevit/revit",
            "pyrevit/compat.py",
            "rpw/db",
            "rpw/ui/selection.py",
            "rpw/utils/coerce.py",
        };

        private static readonly object cacheLock = new object();
        private static List<LibrarySymbol> cached;
        private static string cachedFingerprint;
        private static string cachedRoot;

        public static string LibraryRoot {
            get {
                var skills = PyRevitAgentSkills.ShippedSkillsDir;
                return skills == null ? null : Path.GetFullPath(Path.Combine(skills, "..", "..", ".."));
            }
        }

        /// <param name="query">
        /// A module (<c>pyrevit.revit.db.create</c>), a symbol (<c>pyrevit.revit.db.query.find_type</c>,
        /// <c>find_type</c>), or words to search for (<c>section box</c>).
        /// </param>
        public static JObject Lookup(string query) {
            if (string.IsNullOrWhiteSpace(query))
                throw new AgentClientException("invalid_params", "'query' is required.");
            query = query.Trim();
            var symbols = Load();

            var modules = symbols.Where(symbol => symbol.Kind == "module").ToList();
            var module = modules.FirstOrDefault(candidate => candidate.Module == query);
            if (module != null) {
                var members = symbols.Where(symbol => symbol.Kind != "module" && symbol.Module == module.Module).ToList();
                return new JObject {
                    ["found"] = true,
                    ["module"] = module.Module,
                    ["summary"] = module.Summary,
                    ["import"] = ImportLine(module),
                    ["members"] = new JArray(members.Take(MaxModuleMembers).Select(Brief)),
                    ["members_truncated"] = members.Count > MaxModuleMembers,
                };
            }

            var exact = symbols
                .Where(symbol => symbol.Kind != "module"
                                 && (string.Equals(symbol.FullName, query, StringComparison.OrdinalIgnoreCase)
                                     || string.Equals(symbol.Automation?.Id, query, StringComparison.OrdinalIgnoreCase)
                                     || string.Equals(symbol.Name, query, StringComparison.OrdinalIgnoreCase)
                                     || (symbol.Owner != null && string.Equals(symbol.Owner + "." + symbol.Name, query, StringComparison.OrdinalIgnoreCase))
                                     || IsReExport(symbol, query)))
                .ToList();
            if (exact.Count == 0)
                module = modules.FirstOrDefault(candidate => string.Equals(candidate.Module, query, StringComparison.OrdinalIgnoreCase));
            if (exact.Count == 0 && module != null)
                return Lookup(module.Module);
            if (exact.Count > 0) {
                return new JObject {
                    ["found"] = true,
                    ["matches"] = new JArray(exact.Take(MaxResults).Select(exact.Count <= 3 ? (Func<LibrarySymbol, JObject>)Full : Brief)),
                };
            }

            var tokens = Tokens(query);
            var scored = symbols
                .Select(symbol => new { Symbol = symbol, Score = Score(symbol, tokens), Covers = CoversEveryToken(symbol, tokens) })
                .Where(entry => entry.Score > 0)
                .OrderByDescending(entry => entry.Score)
                .ThenBy(entry => entry.Symbol.FullName.Length)
                .ToList();
            var ranked = scored.Where(entry => entry.Covers).Take(MaxResults).Select(entry => Brief(entry.Symbol)).ToList();
            var result = new JObject {
                ["found"] = ranked.Count > 0,
                ["query"] = query,
                ["matches"] = new JArray(ranked),
                ["note"] = ranked.Count > 0
                    ? "Ranked by name and docstring. Look one up by its full name for the whole docstring."
                    : "Nothing in pyrevitlib or rpw matches every word. Use the Revit API directly (lookup_revit_api).",
            };
            if (ranked.Count == 0)
                result["near_matches"] = new JArray(scored.Take(MaxResults).Select(entry => Brief(entry.Symbol)));
            return result;
        }

        /// <summary>
        /// Lists explicitly marked automation symbols in stable identifier order.
        /// </summary>
        /// <remarks>
        /// A malformed marker, or an id used by more than one symbol, is left out instead of
        /// failing the listing; <c>dev/scripts/test_automation_marker.py</c> fails on both.
        /// </remarks>
        public static JObject ListAutomation(int offset = 0, int limit = DefaultAutomationResults) {
            if (offset < 0)
                throw new AgentClientException("invalid_params", "'offset' must not be negative.");
            if (limit < 1 || limit > MaxAutomationResults)
                throw new AgentClientException("invalid_params", $"'limit' must be between 1 and {MaxAutomationResults}.");

            var symbols = Load()
                .Where(symbol => symbol.Automation != null)
                .GroupBy(symbol => symbol.Automation.Id, StringComparer.OrdinalIgnoreCase)
                .Where(group => group.Count() == 1)
                .Select(group => group.Single())
                .OrderBy(symbol => symbol.Automation.Id, StringComparer.Ordinal)
                .ThenBy(symbol => symbol.FullName, StringComparer.Ordinal)
                .ToList();

            var page = symbols.Skip(offset).Take(limit).ToList();
            var nextOffset = offset + page.Count;
            return new JObject {
                ["total"] = symbols.Count,
                ["offset"] = offset,
                ["limit"] = limit,
                ["next_offset"] = nextOffset < symbols.Count ? new JValue(nextOffset) : JValue.CreateNull(),
                ["operations"] = new JArray(page.Select(Brief)),
            };
        }

        public static bool IsMarkedAutomation(string id) {
            try {
                return Load().Any(symbol => string.Equals(symbol.Automation?.Id, id, StringComparison.OrdinalIgnoreCase));
            }
            catch (AgentClientException) {
                return false;
            }
        }

        private static bool IsReExport(LibrarySymbol symbol, string query) {
            if (symbol.Owner != null || !query.EndsWith("." + symbol.Name, StringComparison.Ordinal))
                return false;
            var package = query.Substring(0, query.Length - symbol.Name.Length - 1);
            return symbol.Module.StartsWith(package + ".", StringComparison.Ordinal);
        }

        /// <summary>
        /// Public symbols named like <paramref name="member"/>, best first, for hints on a failed
        /// attribute access.
        /// </summary>
        public static List<string> Similar(string member, string module = null) {
            var tokens = Tokens(member);
            return Load()
                .Where(symbol => symbol.Kind != "module" && (module == null || symbol.Module == module))
                .Select(symbol => new { Symbol = symbol, Score = NameScore(symbol.Name, tokens) })
                .Where(entry => entry.Score > 0)
                .OrderByDescending(entry => entry.Score)
                .ThenBy(entry => entry.Symbol.Name.Length)
                .Take(6)
                .Select(entry => entry.Symbol.FullName + entry.Symbol.Signature)
                .ToList();
        }

        private static JObject Brief(LibrarySymbol symbol) {
            return new JObject {
                ["name"] = symbol.FullName,
                ["kind"] = symbol.Kind,
                ["signature"] = symbol.Signature,
                ["summary"] = symbol.Summary,
                ["automation"] = Automation(symbol),
            };
        }

        private static JObject Full(LibrarySymbol symbol) {
            var entry = Brief(symbol);
            entry["doc"] = symbol.Doc;
            entry["import"] = ImportLine(symbol);
            return entry;
        }

        private static JObject Automation(LibrarySymbol symbol) {
            if (symbol.Automation == null)
                return null;
            return new JObject {
                ["id"] = symbol.Automation.Id,
                ["plain_english"] = symbol.Automation.PlainEnglish,
                ["mode"] = symbol.Automation.Mode,
                ["effects"] = new JArray(symbol.Automation.Effects),
                ["context"] = symbol.Automation.Context,
                ["transaction"] = symbol.Automation.Transaction,
                ["invocable"] = PyRevitAutomationOperations.IsInvocable(symbol.Automation.Id),
            };
        }

        private static string ImportLine(LibrarySymbol symbol) {
            if (symbol.Kind == "module") {
                var lastDot = symbol.Module.LastIndexOf('.');
                return lastDot < 0 ? $"import {symbol.Module}" : $"from {symbol.Module.Substring(0, lastDot)} import {symbol.Module.Substring(lastDot + 1)}";
            }
            return $"from {symbol.Module} import {symbol.Owner ?? symbol.Name}";
        }

        private static int Score(LibrarySymbol symbol, List<string> tokens) {
            var doc = symbol.Doc ?? string.Empty;
            var automation = symbol.Automation == null
                ? string.Empty
                : symbol.Automation.Id + " " + symbol.Automation.PlainEnglish;
            return NameScore(symbol.FullName, tokens)
                + tokens.Count(token => doc.IndexOf(token, StringComparison.OrdinalIgnoreCase) >= 0)
                + tokens.Count(token => automation.IndexOf(token, StringComparison.OrdinalIgnoreCase) >= 0) * 4;
        }

        private static bool CoversEveryToken(LibrarySymbol symbol, List<string> tokens) {
            var text = symbol.FullName + " " + symbol.Doc + " " + symbol.Automation?.Id + " " + symbol.Automation?.PlainEnglish;
            return tokens
                .Where(token => !LookupStopWords.Contains(token))
                .All(token => text.IndexOf(token, StringComparison.OrdinalIgnoreCase) >= 0);
        }

        private static readonly HashSet<string> LookupStopWords = new HashSet<string> { "by", "in", "of", "to", "for", "an", "and", "or", "with", "is", "it", "on", "as", "not" };

        private static int NameScore(string name, List<string> tokens) {
            var nameTokens = Tokens(name);
            return tokens.Count(token => nameTokens.Contains(token)) * 10
                + tokens.Count(token => name.IndexOf(token, StringComparison.OrdinalIgnoreCase) >= 0) * 3;
        }

        private static List<string> Tokens(string text) {
            var spaced = Regex.Replace(text ?? string.Empty, "([a-z0-9])([A-Z])", "$1 $2");
            return Regex.Split(spaced, @"[^A-Za-z0-9]+")
                .Select(token => token.ToLowerInvariant())
                .Where(token => token.Length > 1 && token != "get" && token != "py" && token != "the")
                .Distinct()
                .ToList();
        }

        private static List<LibrarySymbol> Load() {
            var root = LibraryRoot;
            if (root == null || !Directory.Exists(root))
                throw new AgentClientException("library_not_found", "pyrevitlib was not found next to this CLI or in a registered clone.");

            var files = SourceFiles(root).ToList();
            var fingerprint = SourceFingerprint(files);
            lock (cacheLock) {
                if (cached != null && cachedRoot == root && cachedFingerprint == fingerprint)
                    return cached;

                var symbols = new List<LibrarySymbol>();
                foreach (var file in files) {
                    try {
                        symbols.AddRange(PyRevitLibraryParser.ParseFile(root, file));
                    }
                    catch (Exception ex) when (ex is FileNotFoundException || ex is DirectoryNotFoundException) {
                    }
                }
                cached = symbols;
                cachedFingerprint = fingerprint;
                cachedRoot = root;
                return symbols;
            }
        }

        internal static string SourceFingerprint(IEnumerable<string> files) {
            return string.Join("\n", files
                .OrderBy(path => path, StringComparer.OrdinalIgnoreCase)
                .Select(path => {
                    var info = new FileInfo(path);
                    return path + "\0" + info.LastWriteTimeUtc.Ticks + "\0" + (info.Exists ? info.Length : -1);
                }));
        }

        private static IEnumerable<string> SourceFiles(string root) {
            foreach (var relative in IndexedPaths) {
                var path = Path.Combine(root, relative.Replace('/', Path.DirectorySeparatorChar));
                if (File.Exists(path))
                    yield return path;
                else if (Directory.Exists(path))
                    foreach (var file in Directory.GetFiles(path, "*.py", SearchOption.AllDirectories))
                        yield return file;
            }
        }
    }
}
