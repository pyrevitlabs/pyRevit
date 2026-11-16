using pyRevitLabs.PyRevit;

namespace pyRevitLabs.PyRevit.Tests;

/// <summary>
///     Verifies that <c>pyrevit launch</c> keeps the journals Revit wrote into its launch directory (#3949).
/// </summary>
[TestFixture]
[Category("HostFree")]
[Category("Integration")]
public class LaunchJournalTests {
    private string temp = string.Empty;
    private string launchDirectory = string.Empty;
    private string journalsDirectory = string.Empty;

    /// <summary>
    ///     Creates a launch directory as Revit leaves it.
    /// </summary>
    [SetUp]
    public void SetUp() {
        temp = Path.Combine(Path.GetTempPath(), "pyRevit-journal-tests-" + Guid.NewGuid());
        launchDirectory = Path.Combine(temp, "launch", "0123abcd");
        journalsDirectory = Path.Combine(temp, "Journals");
        Directory.CreateDirectory(launchDirectory);
        File.WriteAllText(Path.Combine(launchDirectory, "journal.0001.txt"), "session");
        File.WriteAllText(Path.Combine(launchDirectory, "journal.0001.worker1.log"), "worker");
        File.WriteAllText(Path.Combine(launchDirectory, "PyRevitLaunch.txt"), "played");
        File.WriteAllText(Path.Combine(launchDirectory, "pyRevit.addin"), "manifest");
    }

    /// <summary>
    ///     Deletes the test's folder.
    /// </summary>
    [TearDown]
    public void TearDown() {
        Directory.Delete(temp, true);
    }

    /// <summary>
    ///     Verifies that the session journal and its worker logs are copied under names that carry the launch, and nothing else is.
    /// </summary>
    [Test]
    public void TheSessionJournalsAreCopiedIntoTheJournalsFolder() {
        var saved = PyRevitLauncher.SaveJournals(launchDirectory, journalsDirectory);

        Assert.That(
            Directory.GetFiles(journalsDirectory).Select(Path.GetFileName).OrderBy(name => name, StringComparer.Ordinal),
            Is.EqualTo(new[] { "journal.launch-0123abcd.0001.txt", "journal.launch-0123abcd.0001.worker1.log" }));
        Assert.That(File.ReadAllText(Path.Combine(journalsDirectory, "journal.launch-0123abcd.0001.txt")), Is.EqualTo("session"));
        Assert.That(
            saved.Where(path => path.EndsWith(".txt")),
            Is.EqualTo(new[] { Path.Combine(journalsDirectory, "journal.launch-0123abcd.0001.txt") }));
    }

    /// <summary>
    ///     Verifies that a journal that can't be read is skipped and the others are still copied.
    /// </summary>
    [Test]
    public void AJournalThatCanNotBeReadIsSkipped() {
        using (File.Open(Path.Combine(launchDirectory, "journal.0001.worker1.log"), FileMode.Open, FileAccess.Read, FileShare.None)) {
            PyRevitLauncher.SaveJournals(launchDirectory, journalsDirectory);
        }

        Assert.That(
            Directory.GetFiles(journalsDirectory).Select(Path.GetFileName),
            Is.EqualTo(new[] { "journal.launch-0123abcd.0001.txt" }));
    }

    /// <summary>
    ///     Verifies that a launch whose Revit never wrote a journal leaves the Journals folder alone.
    /// </summary>
    [Test]
    public void ALaunchWithoutJournalsCopiesNothing() {
        foreach (var journal in Directory.GetFiles(launchDirectory, "journal.*"))
            File.Delete(journal);

        Assert.That(PyRevitLauncher.SaveJournals(launchDirectory, journalsDirectory), Is.Empty);
        Assert.That(Directory.Exists(journalsDirectory), Is.False);
    }
}
