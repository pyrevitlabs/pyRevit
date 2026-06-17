using System.Text;
using System.Text.RegularExpressions;

namespace Build.Helpers;

/// <summary>
/// Minimal port of dev/_autocomplete.py for CI builds.
/// </summary>
public static partial class AutocompleteGenerator
{
    public static void Generate(string usagePatternsPath, string outputPath)
    {
        var lines = File.ReadAllLines(usagePatternsPath).Skip(1);
        var app = new GoCommand("pyrevit");
        app.Flags.Add("verbose");
        app.Flags.Add("debug");

        foreach (var line in lines)
        {
            ParseDocoptLine(line, app);
        }

        var builder = new StringBuilder();
        builder.AppendLine("package main");
        builder.AppendLine();
        builder.AppendLine("import \"github.com/posener/complete\"");
        builder.AppendLine();
        builder.AppendLine("func main() {");
        builder.Append(app.WriteGo(indent: 1));
        builder.AppendLine("\tcomplete.New(\"pyrevit\", pyrevit).Run()");
        builder.AppendLine("}");

        Directory.CreateDirectory(Path.GetDirectoryName(outputPath)!);
        File.WriteAllText(outputPath, builder.ToString());
    }

    private static void ParseDocoptLine(string line, GoCommand app)
    {
        line = line.Trim();
        foreach (var character in new[] { '[', ']', '|', '=' })
        {
            line = line.Replace(character.ToString(), string.Empty, StringComparison.Ordinal);
        }

        line = TagPattern().Replace(line, string.Empty).Trim();

        var flags = FlagPattern().Matches(line).Select(match => match.Groups[1].Value).ToList();
        foreach (var flag in flags)
        {
            line = line.Replace("--" + flag, string.Empty, StringComparison.Ordinal);
        }

        foreach (Match match in ShortFlagPattern().Matches(line))
        {
            line = line.Replace("-" + match.Groups[1].Value, string.Empty, StringComparison.Ordinal);
        }

        line = line.Trim();
        var commandPaths = new List<List<string>>();

        var optionalMatch = OptionalPattern().Match(line);
        if (optionalMatch.Success)
        {
            var optionsDef = optionalMatch.Value;
            foreach (Match option in WordPattern().Matches(optionalMatch.Groups[1].Value))
            {
                commandPaths.Add(ExtractBranch(line.Replace(optionsDef, option.Value, StringComparison.Ordinal)));
            }

            line = line.Replace(optionsDef, string.Empty, StringComparison.Ordinal).Trim();
        }

        commandPaths.Add(ExtractBranch(line));
        foreach (var commandPath in commandPaths)
        {
            app.UpdateFlags(commandPath, flags);
        }
    }

    private static List<string> ExtractBranch(string value)
    {
        var words = WordPattern().Matches(value).Select(match => match.Value).ToList();
        if (words.Count > 0 && string.Equals(words[0], "pyrevit", StringComparison.OrdinalIgnoreCase))
        {
            words.RemoveAt(0);
        }

        return words;
    }

    [GeneratedRegex(@"<[a-zA-Z_]+?>")]
    private static partial Regex TagPattern();

    [GeneratedRegex(@"\s--(\w+)\s?")]
    private static partial Regex FlagPattern();

    [GeneratedRegex(@"-(\w+)\s?")]
    private static partial Regex ShortFlagPattern();

    [GeneratedRegex(@"\((.+?)\)")]
    private static partial Regex OptionalPattern();

    [GeneratedRegex(@"\w+")]
    private static partial Regex WordPattern();

    private sealed class GoCommand(string token)
    {
        public string Token { get; } = token;

        public HashSet<string> Flags { get; } = [];

        public List<GoCommand> Nodes { get; } = [];

        public void UpdateFlags(IReadOnlyList<string> commandPaths, IEnumerable<string> flags)
        {
            if (commandPaths.Count == 0)
            {
                foreach (var flag in flags)
                {
                    Flags.Add(NormalizeFlag(flag));
                }

                return;
            }

            var rootToken = commandPaths[0];
            var command = Nodes.FirstOrDefault(node => node.Token == rootToken);
            if (command is null)
            {
                command = new GoCommand(rootToken);
                Nodes.Add(command);
            }

            command.UpdateFlags(commandPaths.Skip(1).ToList(), flags);
        }

        public string WriteGo(int indent)
        {
            var padding = new string('\t', indent);
            var builder = new StringBuilder();
            builder.AppendLine($"{padding}{Token} := complete.Command{{");
            WriteFields(builder, indent + 1);
            builder.AppendLine($"{padding}}}");
            return builder.ToString();
        }

        private string WriteSubCommand(int indent)
        {
            var padding = new string('\t', indent);
            var builder = new StringBuilder();
            builder.AppendLine($"{padding}\"{Token}\": complete.Command{{");
            WriteFields(builder, indent + 1);
            builder.AppendLine($"{padding}}},");
            return builder.ToString();
        }

        private void WriteFields(StringBuilder builder, int indent)
        {
            var padding = new string('\t', indent);
            if (Nodes.Count == 0)
            {
                builder.AppendLine($"{padding}Sub: complete.Commands{{}},");
            }
            else
            {
                builder.AppendLine($"{padding}Sub: complete.Commands{{");
                foreach (var node in Nodes)
                {
                    builder.Append(node.WriteSubCommand(indent + 1));
                }

                builder.AppendLine($"{padding}}},");
            }

            if (Flags.Count == 0)
            {
                builder.AppendLine($"{padding}Flags: complete.Flags{{}},");
            }
            else
            {
                builder.AppendLine($"{padding}Flags: complete.Flags{{");
                foreach (var flag in Flags.OrderBy(flag => flag, StringComparer.Ordinal))
                {
                    builder.AppendLine($"{padding}\t\"--{flag}\": complete.PredictNothing,");
                }

                builder.AppendLine($"{padding}}},");
            }
        }

        private static string NormalizeFlag(string flag)
        {
            return flag.TrimStart('-');
        }
    }
}
