using Build.Helpers;
using Build.Models;
using Build.Options;
using Microsoft.Extensions.Options;
using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.Git.Extensions;
using ModularPipelines.Git.Options;
using ModularPipelines.GitHub.Attributes;
using ModularPipelines.GitHub.Extensions;
using ModularPipelines.Modules;
using ModularPipelines.Options;
using Octokit;
using System.Net;

namespace Build.Modules;

[SkipIfNoGitHubToken]
public sealed class NotifyIssuesModule(IOptions<BuildOptions> buildOptions) : Module
{
    private static readonly TimeSpan CommentDelay = TimeSpan.FromSeconds(2);

    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var versionInfo = VersionHelper.CreateVersionInfo(VersionHelper.ReadBuildVersion());
        var notifyUrl = buildOptions.Value.NotifyUrl;
        if (string.IsNullOrWhiteSpace(notifyUrl))
        {
            context.Summary.Warning("NotifyUrl is not set; skipping issue notifications.");
            return;
        }

        var channel = buildOptions.Value.Channel;
        var previousTag = channel.Equals("release", StringComparison.OrdinalIgnoreCase)
            ? await FindPreviousTagAsync(context, cancellationToken)
            : await FindLatestTagAsync(context, cancellationToken);

        var comment = channel.Equals("release", StringComparison.OrdinalIgnoreCase)
            ? $":package: New public release is available for [{versionInfo.BuildVersion}]({notifyUrl})"
            : $":package: New work-in-progress (wip) builds are available for [{versionInfo.BuildVersion}]({notifyUrl})";

        var changes = await CollectChangesAsync(context, previousTag, cancellationToken);
        var repositoryInfo = context.GitHub().RepositoryInfo;
        var tickets = changes
            .Select(change => change.Ticket)
            .Where(ticket => ticket is not null)
            .Distinct()
            .ToList();

        if (tickets.Count == 0)
        {
            context.Summary.KeyValue("Notify", "Issues", "0 (none linked since " + previousTag + ")");
            return;
        }

        context.Summary.KeyValue("Notify", "Issues", tickets.Count.ToString(System.Globalization.CultureInfo.InvariantCulture));

        var posted = 0;
        var stoppedEarly = false;

        foreach (var ticket in tickets)
        {
            try
            {
                await context.GitHub().Client.Issue.Comment.Create(
                    repositoryInfo.Owner,
                    repositoryInfo.RepositoryName,
                    int.Parse(ticket!, System.Globalization.CultureInfo.InvariantCulture),
                    comment);
                posted++;
                if (posted < tickets.Count)
                {
                    await Task.Delay(CommentDelay, cancellationToken);
                }
            }
            catch (SecondaryRateLimitExceededException ex)
            {
                context.Summary.Warning(string.Format(
                    System.Globalization.CultureInfo.InvariantCulture,
                    "GitHub secondary rate limit hit after {0} of {1} notifications; stopping. {2}",
                    posted,
                    tickets.Count,
                    ex.Message));
                stoppedEarly = true;
                break;
            }
            catch (ApiException ex) when (ex.StatusCode == HttpStatusCode.Forbidden)
            {
                context.Summary.Warning(string.Format(
                    System.Globalization.CultureInfo.InvariantCulture,
                    "GitHub rejected issue comment (403) after {0} of {1} notifications; stopping. {2}",
                    posted,
                    tickets.Count,
                    ex.Message));
                stoppedEarly = true;
                break;
            }
            catch (ApiException ex)
            {
                context.Summary.Warning(string.Format(
                    System.Globalization.CultureInfo.InvariantCulture,
                    "Failed to notify issue #{0}: {1}",
                    ticket,
                    ex.Message));
            }
        }

        if (!stoppedEarly)
        {
            context.Summary.KeyValue(
                "Notify",
                "Posted",
                string.Format(
                    System.Globalization.CultureInfo.InvariantCulture,
                    "{0} of {1}",
                    posted,
                    tickets.Count));
        }
    }

    private static async Task<string> FindLatestTagAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var result = await context.Git().Commands.ForEachRef(
            new GitForEachRefOptions
            {
                Sort = "-creatordate",
                Format = "%(refname)",
                Count = "1",
                Arguments = ["refs/tags/v*"],
            },
            new CommandExecutionOptions { LogSettings = CommandLoggingOptions.Silent },
            cancellationToken);

        return result.StandardOutput
            .Split('\n', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .Select(tag => tag.Replace("refs/tags/", string.Empty, StringComparison.Ordinal))
            .FirstOrDefault() ?? "HEAD~1";
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

    private static async Task<IReadOnlyList<ChangeTicket>> CollectChangesAsync(
        IModuleContext context,
        string previousTag,
        CancellationToken cancellationToken)
    {
        var result = await context.Git().Commands.Log(
            new GitLogOptions
            {
                Pretty = "format:%h %s%n%b%n/",
                Arguments = [$"{previousTag}..HEAD"],
            });

        return ParseTickets(result.StandardOutput);
    }

    internal static IReadOnlyList<ChangeTicket> ParseTickets(string gitLog)
    {
        var tickets = new List<ChangeTicket>();
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
            if (parts.Length == 2)
            {
                foreach (var ticket in IssueReferenceHelper.ExtractIssueNumbers(parts[1]))
                {
                    tickets.Add(new ChangeTicket(ticket));
                }
            }

            index++;
            while (index < lines.Length && !lines[index].StartsWith("/", StringComparison.Ordinal))
            {
                index++;
            }

            if (index < lines.Length)
            {
                index++;
            }
        }

        return tickets;
    }

    internal sealed record ChangeTicket(string Ticket);
}
