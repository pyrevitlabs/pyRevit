using Build.Helpers;
using Build.Modules;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Build.Tests;

[TestClass]
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
    public void ExtractIssueNumbers_returns_empty_for_text_without_references()
    {
        CollectionAssert.AreEqual(
            Array.Empty<string>(),
            IssueReferenceHelper.ExtractIssueNumbers("no ticket here").ToList());
    }
}
