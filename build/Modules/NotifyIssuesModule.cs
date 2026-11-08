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

[DependsOn<RejectTestSignedBinariesModule>(Optional = true)]
[SkipIfNoGitHubToken]
public sealed class NotifyIssuesModule(
    IOptions<BuildOptions> buildOptions,
    IOptions<PublishOptions> publishOptions) : Module
{
    private static readonly TimeSpan CommentDelay = TimeSpan.FromSeconds(2);

    internal const string WipCommentPrefix = ":package: New work-in-progress (wip) builds are available";
    internal const string WipFallbackRange = "HEAD~1";
    internal const string NotifierLogin = "github-actions[bot]";

    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var versionInfo = VersionHelper.CreateVersionInfo(VersionHelper.ReadBuildVersion());
        var notifyUrl = buildOptions.Value.NotifyUrl;
        if (string.IsNullOrWhiteSpace(notifyUrl))
        {
            notifyUrl = ReadPublishedReleaseUrl();
        }

        if (string.IsNullOrWhiteSpace(notifyUrl))
        {
            context.Summary.Warning("NotifyUrl is not set; skipping issue notifications.");
            return;
        }

        var channel = buildOptions.Value.Channel;
        var isRelease = channel.Equals("release", StringComparison.OrdinalIgnoreCase);
        var previousTag = isRelease
            ? await FindPreviousTagAsync(context, cancellationToken)
            : ResolveWipBaseRevision(buildOptions.Value.NotifyFromSha);

        var comment = isRelease
            ? $":package: New public release is available for [{versionInfo.BuildVersion}]({notifyUrl})"
            : $"{WipCommentPrefix} for [{versionInfo.BuildVersion}]({notifyUrl})";

        var changes = await CollectChangesAsync(context, previousTag);
        var repositoryInfo = context.GitHub().RepositoryInfo;
        var (owner, repositoryName) = GitHubRepositoryHelper.Resolve(
            buildOptions,
            publishOptions,
            repositoryInfo.Owner,
            repositoryInfo.RepositoryName);
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
        var updated = 0;
        var failed = 0;
        var stoppedEarly = false;
        var issues = context.GitHub().Client.Issue.Comment;

        foreach (var ticket in tickets)
        {
            try
            {
                var number = int.Parse(ticket!, System.Globalization.CultureInfo.InvariantCulture);

                if (!isRelease)
                {
                    var existing = await FindPreviousWipCommentAsync(issues, owner, repositoryName, number);
                    if (existing is not null)
                    {
                        if (!string.Equals(existing.Body, comment, StringComparison.Ordinal))
                        {
                            await issues.Update(owner, repositoryName, existing.Id, comment);
                        }

                        updated++;
                        await Task.Delay(CommentDelay, cancellationToken);
                        continue;
                    }
                }

                await issues.Create(owner, repositoryName, number, comment);
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
                failed++;
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
                    "{0} new, {1} updated, of {2}",
                    posted,
                    updated,
                    tickets.Count));
        }

        EnsureAllNotified(stoppedEarly, failed, tickets.Count);
    }

    /// <summary>
    /// Fails the module when any ticket was not notified, so the CI run is not successful and the
    /// next WIP run, which starts from the last successful run, covers these commits again.
    /// </summary>
    internal static void EnsureAllNotified(bool stoppedEarly, int failed, int total)
    {
        if (stoppedEarly || failed > 0)
        {
            throw new InvalidOperationException(string.Format(
                System.Globalization.CultureInfo.InvariantCulture,
                "Issue notifications incomplete ({0} failed of {1}{2}).",
                failed,
                total,
                stoppedEarly ? ", stopped early" : string.Empty));
        }
    }

    /// <summary>
    /// Base revision for WIP notifications: the last commit already notified, as resolved by CI
    /// (head of the last successful develop push run, or github.event.before).
    /// Falls back to the last commit only when it is missing (workflow_dispatch) or is the
    /// all-zero SHA GitHub sends for a newly created branch. Never falls back to the last tag,
    /// which re-notified every issue linked since the release on each push.
    /// </summary>
    internal static string ResolveWipBaseRevision(string? pushBeforeSha)
    {
        var sha = pushBeforeSha?.Trim();
        if (string.IsNullOrEmpty(sha) || sha.Length < 7 || !sha.All(Uri.IsHexDigit) || sha.All(c => c == '0'))
        {
            return WipFallbackRange;
        }

        return sha;
    }

    /// <summary>
    /// Returns the bot's previous WIP announcement on the issue, if any. Callers update it in place
    /// rather than posting a new comment: edits do not notify subscribers.
    /// </summary>
    private static async Task<IssueComment?> FindPreviousWipCommentAsync(
        IIssueCommentsClient issues,
        string owner,
        string repositoryName,
        int number)
    {
        var comments = await issues.GetAllForIssue(
            owner,
            repositoryName,
            number,
            new ApiOptions { PageSize = 100 });
        return comments.LastOrDefault(comment => IsBotWipComment(comment.Body, comment.User?.Login));
    }

    internal static bool IsBotWipComment(string? body, string? authorLogin) =>
        body is not null
        && body.StartsWith(WipCommentPrefix, StringComparison.Ordinal)
        && string.Equals(authorLogin, NotifierLogin, StringComparison.OrdinalIgnoreCase);

    internal static string? ReadPublishedReleaseUrl()
    {
        if (!File.Exists(PyRevitPaths.GitHubReleaseUrlFile))
        {
            return null;
        }

        var url = File.ReadAllText(PyRevitPaths.GitHubReleaseUrlFile).Trim();
        return string.IsNullOrWhiteSpace(url) ? null : url;
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

    private static async Task<IReadOnlyList<ChangeTicket>> CollectChangesAsync(IModuleContext context, string from)
    {
        var result = await context.Git().Commands.Log(
            new GitLogOptions
            {
                Pretty = "format:%h %s%n%b%n/",
                Arguments = [$"{from}..HEAD"],
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
