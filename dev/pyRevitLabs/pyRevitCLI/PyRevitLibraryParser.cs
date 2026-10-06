using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;

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
    /// Reads the public symbols and automation markers of one pyrevitlib or rpw source file.
    /// </summary>
    /// <remarks>
    /// A line scanner, not an importer: it needs neither Revit nor a Python install. Private
    /// names (leading underscore) are left out, and a malformed automation marker is dropped
    /// instead of failing the file.
    /// </remarks>
    internal static class PyRevitLibraryParser {
        private static readonly Regex ClassLine = new Regex(@"^class\s+(?<name>\w+)\s*(\((?<bases>[^)]*)\))?\s*:", RegexOptions.Compiled);
        private static readonly Regex DefStart = new Regex(@"^(?<indent>\s*)def\s+(?<name>\w+)\s*\(", RegexOptions.Compiled);
        private static readonly Regex Decorator = new Regex(@"^\s*@(?<name>[\w.]+)", RegexOptions.Compiled);
        private static readonly Regex AutomationOperation = new Regex(@"^\s*@automation\.operation\s*\(", RegexOptions.Compiled);
        private static readonly Regex AutomationType = new Regex(@"^\s*@automation\.type\s*\(", RegexOptions.Compiled);
        private static readonly Regex AutomationId = new Regex(@"^\s*(?:""(?<double>(?:\\.|[^""])*)""|'(?<single>(?:\\.|[^'])*)')", RegexOptions.Compiled | RegexOptions.Singleline);
        private static readonly Regex AutomationValue = new Regex(@"(?:^|,)\s*(?<name>PlainEnglish|mode|context|transaction)\s*=\s*(?:""(?<double>(?:\\.|[^""])*)""|'(?<single>(?:\\.|[^'])*)')", RegexOptions.Compiled | RegexOptions.Singleline);
        private static readonly Regex AutomationEffects = new Regex(@"(?:^|,)\s*effects\s*=\s*\((?<values>.*?)\)", RegexOptions.Compiled | RegexOptions.Singleline);
        private static readonly Regex QuotedValue = new Regex(@"(?:""(?<double>(?:\\.|[^""])*)""|'(?<single>(?:\\.|[^'])*)')", RegexOptions.Compiled | RegexOptions.Singleline);

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
        private static string ModuleName(string root, string file) {
            var relative = file.Substring(root.Length).TrimStart(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            relative = relative.Substring(0, relative.Length - ".py".Length).Replace(Path.DirectorySeparatorChar, '.').Replace('/', '.');
            return relative.EndsWith(".__init__") ? relative.Substring(0, relative.Length - ".__init__".Length) : relative;
        }
    }
}
