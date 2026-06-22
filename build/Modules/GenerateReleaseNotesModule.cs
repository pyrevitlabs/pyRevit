using System.Text;
using Build.Helpers;
using Build.Models;
using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.Git.Extensions;
using ModularPipelines.Git.Options;
using ModularPipelines.GitHub.Attributes;
using ModularPipelines.GitHub.Extensions;
using ModularPipelines.Modules;
using ModularPipelines.Options;
using Octokit;

namespace Build.Modules;

[SkipIfNoGitHubToken]
public sealed class GenerateReleaseNotesModule : Module<string>
{
    protected override async Task<string?> ExecuteAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var versionInfo = GetVersionInfo();
        var previousTag = await FindPreviousTagAsync(context, cancellationToken);
        var repositoryInfo = context.GitHub().RepositoryInfo;
        var owner = repositoryInfo.Owner ?? "pyrevitlabs";
        var repo = repositoryInfo.RepositoryName ?? "pyRevit";
        var changes = await CollectChangesAsync(
            context,
            previousTag,
            context.GitHub().Client,
            owner,
            repo,
            warning => context.Summary.Warning(warning),
            cancellationToken);

        var builder = new StringBuilder();
        AppendDownloads(builder, versionInfo);
        AppendHighlights(builder, changes);
        AppendChanges(builder, changes);

        return builder.ToString();
    }

    private static void AppendDownloads(StringBuilder builder, VersionInfo versionInfo)
    {
        var baseUrl = VersionHelper.GetReleaseDownloadBaseUrl(versionInfo.BuildVersionUrlSafe);
        builder.AppendLine("# Downloads");
        builder.AppendLine(":small_blue_diamond: See **Assets** section below for all download options");
        builder.AppendLine("### pyRevit");

        AppendDownloadLink(builder, "pyRevit", versionInfo.InstallVersion, baseUrl, PyRevitPaths.PyRevitInstallerName);
        AppendDownloadLink(
            builder,
            "pyRevit",
            versionInfo.InstallVersion,
            baseUrl,
            PyRevitPaths.PyRevitAdminInstallerName,
            " - Admin / All Users / %PROGRAMDATA%");

        builder.AppendLine("### pyRevit CLI (Command line utility)");
        AppendDownloadLink(
            builder,
            "pyRevit CLI",
            versionInfo.InstallVersion,
            baseUrl,
            PyRevitPaths.PyRevitCliAdminInstallerName,
            " - Admin / System %PATH%");
    }

    private static void AppendDownloadLink(
        StringBuilder builder,
        string label,
        string version,
        string baseUrl,
        string nameFormat,
        string suffix = "")
    {
        var fileName = string.Format(nameFormat, version) + ".exe";
        builder.AppendLine($"- :package: [{label} {version} Installer]({baseUrl}{fileName}){suffix}");
    }

    private static void AppendHighlights(StringBuilder builder, IReadOnlyList<ChangeEntry> changes)
    {
        builder.AppendLine();
        builder.AppendLine("# Highlights");
        foreach (var change in changes.Where(change => change.IsHighlighted || change.IsNewFeature))
        {
            builder.AppendLine(change.Format());
        }
    }

    private static void AppendChanges(StringBuilder builder, IReadOnlyList<ChangeEntry> changes)
    {
        builder.AppendLine();
        builder.AppendLine("# Changes");

        var grouped = changes
            .Where(change => change.Ticket is not null && change.Subsystems.Count > 0)
            .SelectMany(change => change.Subsystems.Select(subsystem => (subsystem, change)))
            .GroupBy(entry => entry.subsystem, StringComparer.OrdinalIgnoreCase);

        foreach (var group in grouped.OrderBy(group => group.Key, StringComparer.Ordinal))
        {
            builder.AppendLine($"### {group.Key}");
            foreach (var (_, change) in group)
            {
                builder.AppendLine(change.Format());
            }
        }
    }

    private static async Task<string> FindPreviousTagAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var result = await context.Git().Commands.ForEachRef(
            new GitForEachRefOptions
            {
                Sort = "-creatordate",
                Format = "%(refname)",
                Count = "2",
                Arguments = ["refs/tags/v*"],
            },
            new CommandExecutionOptions { LogSettings = CommandLoggingOptions.Silent },
            cancellationToken);

        var tags = result.StandardOutput
            .Split('\n', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .Select(tag => tag.Replace("refs/tags/", string.Empty, StringComparison.Ordinal))
            .ToArray();

        return tags.Length >= 2 ? tags[1] : tags.FirstOrDefault() ?? "HEAD~1";
    }

    private static async Task<IReadOnlyList<ChangeEntry>> CollectChangesAsync(
        IModuleContext context,
        string previousTag,
        IGitHubClient gitHubClient,
        string owner,
        string repo,
        Action<string> logWarning,
        CancellationToken cancellationToken)
    {
        var result = await context.Git().Commands.Log(
            new GitLogOptions
            {
                Pretty = "format:%h %s%n%b%n/",
                Arguments = [$"{previousTag}..HEAD"],
            });

        return await ParseChangesAsync(result.StandardOutput, gitHubClient, owner, repo, logWarning);
    }

    internal static async Task<IReadOnlyList<ChangeEntry>> ParseChangesAsync(
        string gitLog,
        IGitHubClient? gitHubClient,
        string owner,
        string repo,
        Action<string>? logWarning = null)
    {
        var changes = new List<ChangeEntry>();
        var lines = gitLog.Split('\n');
        var index = 0;
        while (index < lines.Length)
        {
            var line = lines[index];
            if (string.IsNullOrWhiteSpace(line))
            {
                index++;
                continue;
            }

            var parts = line.Split(' ', 2);
            if (parts.Length != 2)
            {
                index++;
                continue;
            }

            var hash = parts[0];
            var message = parts[1];
            index++;

            var comments = new StringBuilder();
            while (index < lines.Length && !lines[index].StartsWith("/", StringComparison.Ordinal))
            {
                comments.AppendLine(lines[index]);
                index++;
            }

            if (index < lines.Length)
            {
                index++;
            }

            changes.Add(await ChangeEntry.CreateAsync(hash, message, comments.ToString(), gitHubClient, owner, repo, logWarning));
        }

        return changes;
    }

    private static VersionInfo GetVersionInfo()
    {
        return VersionHelper.ReadVersionInfo();
    }

    internal sealed class ChangeEntry
    {
        private ChangeEntry(
            string hash,
            string? ticket,
            string title,
            string url,
            IReadOnlyList<string> subsystems,
            bool isHighlighted,
            bool isNewFeature)
        {
            Hash = hash;
            Ticket = ticket;
            Title = title;
            Url = url;
            Subsystems = subsystems;
            IsHighlighted = isHighlighted;
            IsNewFeature = isNewFeature;
        }

        public string Hash { get; }

        public string? Ticket { get; }

        public string Title { get; }

        public string Url { get; }

        public IReadOnlyList<string> Subsystems { get; }

        public bool IsHighlighted { get; }

        public bool IsNewFeature { get; }

        public static async Task<ChangeEntry> CreateAsync(
            string hash,
            string message,
            string comments,
            IGitHubClient? gitHubClient,
            string owner,
            string repo,
            Action<string>? logWarning = null)
        {
            var ticket = IssueReferenceHelper.ExtractIssueNumbers(message).FirstOrDefault();
            var title = message;
            var url = string.Empty;
            var subsystems = new List<string>();
            var isHighlighted = false;
            var isNewFeature = false;

            if (ticket is not null && gitHubClient is not null)
            {
                try
                {
                    var issue = await gitHubClient.Issue.Get(owner, repo, int.Parse(ticket, System.Globalization.CultureInfo.InvariantCulture));
                    title = issue.Title;
                    url = issue.HtmlUrl;
                    foreach (var label in issue.Labels)
                    {
                        if (label.Description?.Contains("[subsystem", StringComparison.OrdinalIgnoreCase) == true)
                        {
                            subsystems.Add(label.Name);
                        }

                        if (string.Equals(label.Name, "Highlight", StringComparison.OrdinalIgnoreCase))
                        {
                            isHighlighted = true;
                        }

                        if (string.Equals(label.Name, "New Feature", StringComparison.OrdinalIgnoreCase))
                        {
                            isNewFeature = true;
                        }
                    }
                }
                catch (NotFoundException)
                {
                    // Issue metadata is optional when the ticket no longer exists.
                }
                catch (Exception ex)
                {
                    logWarning?.Invoke($"Could not fetch metadata for #{ticket}: {ex.Message}");
                }
            }

            return new ChangeEntry(hash, ticket, title, url, subsystems, isHighlighted, isNewFeature);
        }

        public string Format()
        {
            if (Ticket is null)
            {
                return $"- {Title}";
            }

            return $"- Resolved #{Ticket}: {Title}";
        }
    }
}
