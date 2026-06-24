using System.Text.RegularExpressions;

namespace Build.Helpers;

public static partial class IssueReferenceHelper
{
    [GeneratedRegex("#(\\d+)", RegexOptions.None)]
    private static partial Regex IssueNumberPattern();

    public static IEnumerable<string> ExtractIssueNumbers(string text)
    {
        foreach (Match match in IssueNumberPattern().Matches(text))
        {
            yield return match.Groups[1].Value;
        }
    }
}
