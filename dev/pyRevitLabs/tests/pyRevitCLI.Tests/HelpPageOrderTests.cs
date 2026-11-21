using System.Text.RegularExpressions;
using pyRevitCLI;

namespace pyRevitCLI.Tests;

/// <summary>
///     Keeps the <c>--help</c> pages in the order of <c>UsagePatterns.txt</c>, which both describe the same commands.
/// </summary>
[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public class HelpPageOrderTests {
    private static readonly string[] UsageFileLines =
        File.ReadAllLines(Path.Combine(AppContext.BaseDirectory, "UsagePatterns.txt"));

    public static IEnumerable<object[]> SubcommandPages() =>
        Enum.GetValues<PyRevitCLICommandType>()
            .Where(type => type != PyRevitCLICommandType.Main && PyRevitCLIAppHelps.HelpText(type) != null)
            .Select(type => new object[] { type.ToString() });

    [Fact]
    public void MainPageListsTheCommandsInUsageOrder() {
        var usageOrder = UsageFileLines
            .Select(line => Regex.Match(line, @"^\s*pyrevit ([a-z]+)\b"))
            .Where(match => match.Success)
            .Select(match => match.Groups[1].Value)
            .Distinct()
            .ToList();

        var listed = ListedCommands(PyRevitCLIAppHelps.HelpText(PyRevitCLICommandType.Main), "Commands").ToList();

        Assert.Equal(usageOrder, listed);
    }

    [Theory]
    [MemberData(nameof(SubcommandPages))]
    public void SubcommandPageListsEachSectionInUsageOrder(string typeName) {
        var type = Enum.Parse<PyRevitCLICommandType>(typeName);
        var page = PyRevitCLIAppHelps.HelpText(type);
        var usageWords = page.Split('\n')
            .Select(line => line.Trim())
            .Where(line => line.StartsWith("pyrevit "))
            .Select(WordsOf)
            .ToList();

        foreach (var section in new[] { "Management Commands", "Commands" }) {
            var positions = ListedCommands(page, section)
                .Where(command => Regex.IsMatch(command, "^[a-z]"))
                .Select(command => (command, position: PositionIn(usageWords, command)))
                .ToList();

            Assert.DoesNotContain(positions, entry => entry.position.Line < 0);
            Assert.Equal(positions.OrderBy(entry => entry.position.Line).ThenBy(entry => entry.position.Word).Select(entry => entry.command),
                         positions.Select(entry => entry.command));
        }
    }

    private static (int Line, int Word) PositionIn(List<List<string>> usageWords, string command) {
        var line = usageWords.FindIndex(words => words.Contains(command));
        return (line, line < 0 ? -1 : usageWords[line].IndexOf(command));
    }

    private static List<string> WordsOf(string usageLine) =>
        Regex.Split(usageLine, @"[\s()\[\]|]+").Where(word => Regex.IsMatch(word, "^[a-z][a-z0-9-]*$")).ToList();

    private static IEnumerable<string> ListedCommands(string page, string section) =>
        page.Split('\n')
            .Select(line => line.TrimEnd('\r'))
            .SkipWhile(line => line != "    " + section + ":")
            .Skip(1)
            .TakeWhile(line => line.Length > 0)
            .Select(line => line.Trim().Split(' ')[0]);
}
