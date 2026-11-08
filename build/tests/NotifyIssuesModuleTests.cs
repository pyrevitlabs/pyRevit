using Build.Helpers;
using Build.Modules;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Build.Tests;

[TestClass]
[TestCategory("HostFree")]
[TestCategory("Unit")]
public sealed class NotifyIssuesModuleTests
{
    [TestMethod]
    public void ParseTickets_extracts_single_issue_from_commit_subject()
    {
        var tickets = NotifyIssuesModule.ParseTickets("abc1234 fix loader crash #42\n/\n");

        Assert.AreEqual(1, tickets.Count);
        Assert.AreEqual("42", tickets[0].Ticket);
    }

    [TestMethod]
    public void ParseTickets_extracts_all_issues_from_commit_subject()
    {
        var tickets = NotifyIssuesModule.ParseTickets("abc1234 fix #123, closes #456\n/\n");

        CollectionAssert.AreEquivalent(
            new[] { "123", "456" },
            tickets.Select(ticket => ticket.Ticket).ToList());
    }

    [TestMethod]
    [DataRow(null)]
    [DataRow("")]
    [DataRow("0000000000000000000000000000000000000000")]
    [DataRow("not-a-sha")]
    public void ResolveWipBaseRevision_falls_back_to_last_commit_never_to_a_tag(string? before)
    {
        Assert.AreEqual(NotifyIssuesModule.WipFallbackRange, NotifyIssuesModule.ResolveWipBaseRevision(before));
    }

    [TestMethod]
    public void ResolveWipBaseRevision_uses_push_before_sha()
    {
        const string before = "03ab51a66f1c2d3e4b5a69788796a5b4c3d2e1f0";

        Assert.AreEqual(before, NotifyIssuesModule.ResolveWipBaseRevision(" " + before + " "));
    }

    [TestMethod]
    public void IsBotWipComment_matches_only_bot_wip_announcements()
    {
        var body = NotifyIssuesModule.WipCommentPrefix + " for [7.0.1.26300+1200](https://example.test)";

        Assert.IsTrue(NotifyIssuesModule.IsBotWipComment(body, "github-actions[bot]"));
        Assert.IsFalse(NotifyIssuesModule.IsBotWipComment(body, "some-user"));
        Assert.IsFalse(NotifyIssuesModule.IsBotWipComment(":package: New public release is available for [7.0.1]", "github-actions[bot]"));
        Assert.IsFalse(NotifyIssuesModule.IsBotWipComment(null, "github-actions[bot]"));
    }

    [TestMethod]
    public void ExtractIssueNumbers_returns_empty_for_text_without_references()
    {
        CollectionAssert.AreEqual(
            Array.Empty<string>(),
            IssueReferenceHelper.ExtractIssueNumbers("no ticket here").ToList());
    }

    [TestMethod]
    public void ReadPublishedReleaseUrl_returns_null_when_file_missing()
    {
        var path = PyRevitPaths.GitHubReleaseUrlFile;
        var existed = File.Exists(path);
        var previous = existed ? File.ReadAllText(path) : null;
        try
        {
            if (existed)
            {
                File.Delete(path);
            }

            Assert.IsNull(NotifyIssuesModule.ReadPublishedReleaseUrl());
        }
        finally
        {
            if (existed && previous is not null)
            {
                Directory.CreateDirectory(PyRevitPaths.DistPath);
                File.WriteAllText(path, previous);
            }
        }
    }

    [TestMethod]
    public void ReadPublishedReleaseUrl_reads_trimmed_url_from_dist_file()
    {
        Directory.CreateDirectory(PyRevitPaths.DistPath);
        var path = PyRevitPaths.GitHubReleaseUrlFile;
        var existed = File.Exists(path);
        var previous = existed ? File.ReadAllText(path) : null;
        const string expected = "https://github.com/pyrevitlabs/pyRevit/releases/tag/v6.5.0.26173%2B1406";
        try
        {
            File.WriteAllText(path, expected + "\r\n");

            Assert.AreEqual(expected, NotifyIssuesModule.ReadPublishedReleaseUrl());
        }
        finally
        {
            if (existed && previous is not null)
            {
                File.WriteAllText(path, previous);
            }
            else if (File.Exists(path))
            {
                File.Delete(path);
            }
        }
    }
}
