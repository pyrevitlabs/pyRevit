using System.Text.RegularExpressions;
using Build.Helpers;
using ModularPipelines.Context;
using ModularPipelines.Modules;

namespace Build.Modules;

/// <summary>
/// Checks the agent skills shipped in <c>pyrevitlib/pyrevit/agent/skills</c> against the rules
/// in "Writing a skill" of <c>docs/agent-runtime.md</c>, so a broken skill fails the build
/// instead of misleading agents.
/// </summary>
/// <remarks>
/// Errors: a missing <c>SKILL.md</c>, a <c>name</c> that isn't kebab-case or differs from its
/// folder, a description outside 20-1,024 characters, a body over 500 lines, a markdown link
/// leaving the skill folder or pointing to a missing file, and an <c>INSTRUCTIONS.md</c>
/// without its <c>{skills}</c> placeholder. A skill over about 5,000 tokens is reported in the
/// summary but doesn't fail the build.
/// </remarks>
public sealed partial class ValidateAgentSkillsModule : Module
{
    private const string SkillFileName = "SKILL.md";
    private const string InstructionsFileName = "INSTRUCTIONS.md";
    private const string SkillsPlaceholder = "{skills}";
    private const int MinDescriptionLength = 20;
    private const int MaxDescriptionLength = 1024;
    private const int MaxBodyLines = 500;
    private const int WarnTokenCount = 5000;

    protected override Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var root = PyRevitPaths.AgentSkillsPath;
        var errors = new List<string>();
        var oversized = new List<string>();

        CheckInstructions(root, errors);
        var skillDirectories = Directory.GetDirectories(root).OrderBy(path => path, StringComparer.Ordinal).ToList();
        foreach (var skillDirectory in skillDirectories)
        {
            CheckSkill(skillDirectory, errors, oversized);
        }

        if (errors.Count > 0)
        {
            throw new InvalidOperationException(
                "Agent skills failed validation:" + Environment.NewLine + string.Join(Environment.NewLine, errors));
        }

        context.Summary.KeyValue("Agent skills", "Checked", skillDirectories.Count.ToString());
        if (oversized.Count > 0)
        {
            context.Summary.KeyValue("Agent skills", "Over the token budget", string.Join(", ", oversized));
        }

        return Task.CompletedTask;
    }

    private static void CheckInstructions(string root, List<string> errors)
    {
        var instructions = Path.Combine(root, InstructionsFileName);
        if (!File.Exists(instructions))
        {
            errors.Add($"{InstructionsFileName}: missing");
        }
        else if (!File.ReadAllText(instructions).Contains(SkillsPlaceholder, StringComparison.Ordinal))
        {
            errors.Add($"{InstructionsFileName}: has no {SkillsPlaceholder} placeholder for the skill list");
        }
    }

    private static void CheckSkill(string skillDirectory, List<string> errors, List<string> oversized)
    {
        var folder = Path.GetFileName(skillDirectory);
        var skillFile = Path.Combine(skillDirectory, SkillFileName);
        if (!File.Exists(skillFile))
        {
            errors.Add($"{folder}: has no {SkillFileName}");
            return;
        }

        var text = File.ReadAllText(skillFile);
        var lines = text.Replace("\r\n", "\n").Split('\n');
        var location = $"{folder}/{SkillFileName}";
        var closing = lines.Length > 0 && lines[0].Trim() == "---"
            ? Array.FindIndex(lines, 1, line => line.Trim() == "---")
            : -1;
        if (closing < 0)
        {
            errors.Add($"{location}: doesn't start with --- front matter");
            return;
        }

        var frontMatter = lines.Skip(1).Take(closing - 1).ToList();
        var name = ReadField(frontMatter, "name");
        if (name is null || !KebabCaseRegex().IsMatch(name) || name != folder)
        {
            errors.Add($"{location}: name '{name}' must be lowercase kebab-case and equal the folder name");
        }

        var description = ReadField(frontMatter, "description");
        if (description is null || description.Length < MinDescriptionLength || description.Length > MaxDescriptionLength)
        {
            errors.Add(
                $"{location}: description is {description?.Length ?? 0} characters; it must be {MinDescriptionLength}-{MaxDescriptionLength}");
        }

        var bodyLines = lines.Length - closing - 1;
        if (bodyLines > MaxBodyLines)
        {
            errors.Add($"{location}: body is {bodyLines} lines; the limit is {MaxBodyLines}");
        }

        if (text.Length / 4 > WarnTokenCount)
        {
            oversized.Add($"{folder} (~{text.Length / 4} tokens)");
        }

        foreach (var markdownFile in Directory.GetFiles(skillDirectory, "*.md", SearchOption.AllDirectories))
        {
            CheckLinks(skillDirectory, markdownFile, errors);
        }
    }

    private static void CheckLinks(string skillDirectory, string markdownFile, List<string> errors)
    {
        var skillRoot = Path.GetFullPath(skillDirectory) + Path.DirectorySeparatorChar;
        var location = Path.GetRelativePath(Path.GetDirectoryName(skillDirectory)!, markdownFile).Replace('\\', '/');
        var prose = InlineCodeRegex().Replace(FencedCodeRegex().Replace(File.ReadAllText(markdownFile), string.Empty), string.Empty);
        foreach (Match match in LinkRegex().Matches(prose))
        {
            var target = match.Groups[1].Value;
            if (target.StartsWith('#') || target.Contains("://", StringComparison.Ordinal) || target.StartsWith("mailto:", StringComparison.Ordinal))
            {
                continue;
            }

            var path = target.Split('#')[0];
            var resolved = Path.GetFullPath(Path.Combine(Path.GetDirectoryName(markdownFile)!, path));
            if (Path.IsPathRooted(path) || !resolved.StartsWith(skillRoot, StringComparison.OrdinalIgnoreCase))
            {
                errors.Add($"{location}: link '{target}' leaves the skill folder");
            }
            else if (!File.Exists(resolved))
            {
                errors.Add($"{location}: link '{target}' points to a missing file");
            }
        }
    }

    private static string? ReadField(IEnumerable<string> frontMatter, string field)
    {
        var prefix = field + ":";
        var line = frontMatter.FirstOrDefault(candidate => candidate.StartsWith(prefix, StringComparison.Ordinal));
        return line?[prefix.Length..].Trim();
    }

    [GeneratedRegex("^[a-z0-9]+(-[a-z0-9]+)*$")]
    private static partial Regex KebabCaseRegex();

    [GeneratedRegex(@"\]\(([^)\s]+)\)")]
    private static partial Regex LinkRegex();

    [GeneratedRegex(@"^\s*```.*?^\s*```", RegexOptions.Singleline | RegexOptions.Multiline)]
    private static partial Regex FencedCodeRegex();

    [GeneratedRegex("`[^`\n]*`")]
    private static partial Regex InlineCodeRegex();
}
