using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;

using pyRevitLabs.Json.Linq;

namespace pyRevitCLI {
    /// <summary>
    /// A public function, class, method or module of pyrevitlib or rpw, read from source.
    /// </summary>
    internal sealed class LibrarySymbol {
        public string Module { get; set; }
        public string Name { get; set; }
        public string Owner { get; set; }
        public string Kind { get; set; }
        public string Signature { get; set; }
        public string Doc { get; set; }
        public AutomationMetadata Automation { get; set; }

        public string FullName => Owner == null ? $"{Module}.{Name}" : $"{Module}.{Owner}.{Name}";
        public string Summary => (Doc ?? string.Empty).Split('\n').Select(line => line.Trim()).FirstOrDefault(line => line.Length > 0) ?? string.Empty;
    }

    /// <summary>
    /// Stable metadata attached to a Python library symbol for agent discovery.
    /// </summary>
    internal sealed class AutomationMetadata {
        public string Id { get; set; }
        public string PlainEnglish { get; set; }
        public string Mode { get; set; }
        public List<string> Effects { get; set; }
        public string Context { get; set; }
        public string Transaction { get; set; }
    }

    /// <summary>
    /// Serves <c>lookup_pyrevit_api</c>: the public API of pyrevitlib and rpw, indexed from the
    /// source files of the clone, so agents use the shared libraries instead of re-deriving
    /// Revit API recipes.
    /// </summary>
    /// <remarks>
    /// Reads Python source with a line scanner instead of importing it, so it needs neither
    /// Revit nor a Python install, and it reflects the clone as it is on disk. The index is
    /// rebuilt when a source file changes. Private names (leading underscore) are left out.
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

        private static readonly Regex ClassLine = new Regex(@"^class\s+(?<name>\w+)\s*(\((?<bases>[^)]*)\))?\s*:", RegexOptions.Compiled);
        private static readonly Regex DefStart = new Regex(@"^(?<indent>\s*)def\s+(?<name>\w+)\s*\(", RegexOptions.Compiled);
        private static readonly Regex Decorator = new Regex(@"^\s*@(?<name>[\w.]+)", RegexOptions.Compiled);
        private static readonly Regex AutomationOperation = new Regex(@"^\s*@automation\.operation\s*\(", RegexOptions.Compiled);
        private static readonly Regex AutomationType = new Regex(@"^\s*@automation\.type\s*\(", RegexOptions.Compiled);
        private static readonly Regex AutomationId = new Regex(@"^\s*(?:""(?<double>(?:\\.|[^""])*)""|'(?<single>(?:\\.|[^'])*)')", RegexOptions.Compiled | RegexOptions.Singleline);
        private static readonly Regex AutomationValue = new Regex(@"(?:^|,)\s*(?<name>PlainEnglish|mode|context|transaction)\s*=\s*(?:""(?<double>(?:\\.|[^""])*)""|'(?<single>(?:\\.|[^'])*)')", RegexOptions.Compiled | RegexOptions.Singleline);
        private static readonly Regex AutomationEffects = new Regex(@"(?:^|,)\s*effects\s*=\s*\((?<values>.*?)\)", RegexOptions.Compiled | RegexOptions.Singleline);
        private static readonly Regex QuotedValue = new Regex(@"(?:""(?<double>(?:\\.|[^""])*)""|'(?<single>(?:\\.|[^'])*)')", RegexOptions.Compiled | RegexOptions.Singleline);

        private static readonly object cacheLock = new object();
        private static List<LibrarySymbol> cached;
        private static DateTime cachedStamp;
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
            var ranked = symbols
                .Select(symbol => new { Symbol = symbol, Score = Score(symbol, tokens) })
                .Where(entry => entry.Score > 0)
                .OrderByDescending(entry => entry.Score)
                .ThenBy(entry => entry.Symbol.FullName.Length)
                .Take(MaxResults)
                .Select(entry => Brief(entry.Symbol))
                .ToList();
            return new JObject {
                ["found"] = ranked.Count > 0,
                ["query"] = query,
                ["matches"] = new JArray(ranked),
                ["note"] = ranked.Count > 0
                    ? "Ranked by name and docstring. Look one up by its full name for the whole docstring."
                    : "Nothing in pyrevitlib or rpw matches. Use the Revit API directly (lookup_revit_api).",
            };
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
            var stamp = files.Count == 0 ? DateTime.MinValue : files.Max(File.GetLastWriteTimeUtc);
            lock (cacheLock) {
                if (cached != null && cachedRoot == root && cachedStamp >= stamp)
                    return cached;

                var symbols = new List<LibrarySymbol>();
                foreach (var file in files)
                    symbols.AddRange(ParseFile(root, file));
                cached = symbols;
                cachedStamp = stamp;
                cachedRoot = root;
                return symbols;
            }
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

        private static string ModuleName(string root, string file) {
            var relative = file.Substring(root.Length).TrimStart(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            relative = relative.Substring(0, relative.Length - ".py".Length).Replace(Path.DirectorySeparatorChar, '.').Replace('/', '.');
            return relative.EndsWith(".__init__") ? relative.Substring(0, relative.Length - ".__init__".Length) : relative;
        }

        internal static List<LibrarySymbol> ParseFile(string root, string file) {
            var module = ModuleName(root, file);
            var lines = File.ReadAllLines(file);
            var symbols = new List<LibrarySymbol>();

            var moduleDocLine = 0;
            while (moduleDocLine < lines.Length && (lines[moduleDocLine].Trim().Length == 0 || lines[moduleDocLine].TrimStart().StartsWith("#")))
                moduleDocLine++;
            symbols.Add(new LibrarySymbol {
                Module = module,
                Name = module.Split('.').Last(),
                Kind = "module",
                Doc = ReadDocstring(lines, moduleDocLine),
            });

            string currentClass = null;
            LibrarySymbol currentClassSymbol = null;
            var decorators = new List<string>();
            AutomationMetadata automation = null;
            for (var index = 0; index < lines.Length; index++) {
                var line = lines[index];
                if (AutomationOperation.IsMatch(line) || AutomationType.IsMatch(line)) {
                    var markerLine = index;
                    try {
                        automation = ReadAutomation(lines, ref index, AutomationType.IsMatch(line));
                    }
                    catch (Exception ex) when (ex is AgentClientException || ex is ArgumentException) {
                        automation = null;
                        index = markerLine;
                    }
                    continue;
                }
                var decorator = Decorator.Match(line);
                if (decorator.Success) {
                    decorators.Add(decorator.Groups["name"].Value);
                    continue;
                }

                var classMatch = ClassLine.Match(line);
                if (classMatch.Success) {
                    var classAutomation = automation;
                    currentClass = classMatch.Groups["name"].Value;
                    currentClassSymbol = null;
                    decorators.Clear();
                    automation = null;
                    if (currentClass.StartsWith("_"))
                        continue;
                    var bases = classMatch.Groups["bases"].Value.Trim();
                    var classDoc = ReadDocstring(lines, index + 1);
                    currentClassSymbol = new LibrarySymbol {
                        Module = module,
                        Name = currentClass,
                        Kind = "class",
                        Signature = "()",
                        Doc = bases.Length > 0 ? ((classDoc ?? string.Empty) + "\n\nBases: " + bases + ".").Trim() : classDoc,
                        Automation = classAutomation,
                    };
                    symbols.Add(currentClassSymbol);
                    continue;
                }

                var def = DefStart.Match(line);
                if (!def.Success) {
                    if (line.Length > 0 && !char.IsWhiteSpace(line[0]) && !line.StartsWith("#"))
                        currentClass = null;
                    decorators.Clear();
                    automation = null;
                    continue;
                }

                var indent = def.Groups["indent"].Value.Length;
                var name = def.Groups["name"].Value;
                var signature = ReadSignature(lines, ref index, def.Index + def.Length - 1);
                var isMethod = indent > 0 && currentClass != null;
                if (indent == 0)
                    currentClass = null;
                var skip = (indent > 0 && !isMethod) || (isMethod && indent > 4) || (currentClass != null && currentClass.StartsWith("_"))
                           || (name.StartsWith("_") && name != "__init__");
                if (!skip && isMethod && name == "__init__") {
                    if (currentClassSymbol != null)
                        currentClassSymbol.Signature = DropSelf(signature);
                }
                else if (!skip) {
                    symbols.Add(new LibrarySymbol {
                        Module = module,
                        Owner = isMethod ? currentClass : null,
                        Name = name,
                        Kind = isMethod ? (decorators.Contains("property") ? "property" : "method") : "function",
                        Signature = isMethod ? DropSelf(signature) : signature,
                        Doc = ReadDocstring(lines, index + 1),
                        Automation = automation,
                    });
                }
                decorators.Clear();
                automation = null;
            }
            return symbols;
        }

        private static AutomationMetadata ReadAutomation(string[] lines, ref int index, bool isType) {
            var decorator = ReadDecorator(lines, ref index);
            var arguments = decorator.Substring(decorator.IndexOf('(') + 1);
            arguments = arguments.Substring(0, arguments.Length - 1);
            var id = ReadString(AutomationId.Match(arguments));
            var values = AutomationValue.Matches(arguments)
                .Cast<Match>()
                .ToDictionary(match => match.Groups["name"].Value, ReadString);
            var effects = AutomationEffects.Match(arguments);
            var effectValues = effects.Success
                ? QuotedValue.Matches(effects.Groups["values"].Value).Cast<Match>().Select(ReadString).ToList()
                : new List<string>();
            if (string.IsNullOrEmpty(id) || !values.ContainsKey("PlainEnglish"))
                throw new AgentClientException("invalid_automation_marker", "A Python automation marker needs a stable id and PlainEnglish value.");
            return new AutomationMetadata {
                Id = id,
                PlainEnglish = values["PlainEnglish"],
                Mode = values.ContainsKey("mode") ? values["mode"] : isType ? "infrastructure" : "query",
                Effects = effectValues,
                Context = values.ContainsKey("context") ? values["context"] : isType ? "none" : "document",
                Transaction = values.ContainsKey("transaction") ? values["transaction"] : "none",
            };
        }

        private static string ReadDecorator(string[] lines, ref int index) {
            var builder = new StringBuilder();
            var depth = 0;
            var quote = '\0';
            for (; index < lines.Length; index++) {
                var line = StripComment(lines[index]);
                builder.Append(line.Trim());
                for (var position = 0; position < line.Length; position++) {
                    var character = line[position];
                    if (quote != '\0') {
                        if (character == '\\')
                            position++;
                        else if (character == quote)
                            quote = '\0';
                    }
                    else if (character == '\"' || character == '\'')
                        quote = character;
                    else if (character == '(')
                        depth++;
                    else if (character == ')') {
                        depth--;
                        if (depth == 0)
                            return builder.ToString();
                    }
                }
            }
            throw new AgentClientException("invalid_automation_marker", "A Python automation marker has an unclosed argument list.");
        }

        private static string ReadString(Match match) {
            if (!match.Success)
                return null;
            var value = match.Groups["double"].Success
                ? match.Groups["double"].Value
                : match.Groups["single"].Value;
            return Regex.Unescape(value);
        }

        private static string ReadSignature(string[] lines, ref int index, int openParen) {
            var builder = new StringBuilder();
            var depth = 0;
            var line = StripComment(lines[index]);
            var position = openParen;
            while (true) {
                for (; position < line.Length; position++) {
                    var character = line[position];
                    if (character == '(') depth++;
                    if (character == ')') depth--;
                    builder.Append(character);
                    if (depth == 0)
                        return Regex.Replace(builder.ToString(), @"\s+", " ").Replace("( ", "(").Replace(", )", ")").Replace(",)", ")").Replace(" )", ")");
                }
                if (index + 1 >= lines.Length)
                    return builder.ToString();
                index++;
                line = StripComment(lines[index]);
                position = 0;
                builder.Append(' ');
            }
        }

        private static string StripComment(string line) {
            var quote = '\0';
            for (var position = 0; position < line.Length; position++) {
                var character = line[position];
                if (quote != '\0') {
                    if (character == quote)
                        quote = '\0';
                }
                else if (character == '"' || character == '\'') {
                    quote = character;
                }
                else if (character == '#') {
                    return line.Substring(0, position);
                }
            }
            return line;
        }

        private static string DropSelf(string signature) {
            return Regex.Replace(signature, @"^\((self|cls)\s*,?\s*", "(");
        }

        private static string ReadDocstring(string[] lines, int start) {
            var index = start;
            while (index < lines.Length && lines[index].Trim().Length == 0)
                index++;
            if (index >= lines.Length)
                return null;

            var first = lines[index].TrimStart();
            if (first.StartsWith("r"))
                first = first.Substring(1);
            string quote;
            if (first.StartsWith("\"\"\""))
                quote = "\"\"\"";
            else if (first.StartsWith("'''"))
                quote = "'''";
            else
                return null;

            var body = first.Substring(3);
            var closing = body.IndexOf(quote, StringComparison.Ordinal);
            if (closing >= 0)
                return body.Substring(0, closing).Trim();

            var collected = new List<string> { body };
            for (index++; index < lines.Length; index++) {
                closing = lines[index].IndexOf(quote, StringComparison.Ordinal);
                if (closing >= 0) {
                    collected.Add(lines[index].Substring(0, closing));
                    break;
                }
                collected.Add(lines[index]);
            }
            return Dedent(collected).Trim();
        }

        private static string Dedent(List<string> lines) {
            var indents = lines.Skip(1)
                .Where(line => line.Trim().Length > 0)
                .Select(line => line.Length - line.TrimStart().Length)
                .ToList();
            var common = indents.Count > 0 ? indents.Min() : 0;
            return string.Join("\n", lines.Select((line, i) => i > 0 && line.Length >= common ? line.Substring(common) : line.Trim()));
        }
    }
}
