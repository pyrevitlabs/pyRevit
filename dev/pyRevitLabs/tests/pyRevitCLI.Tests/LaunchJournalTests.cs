using pyRevitLabs.PyRevit;

namespace pyRevitCLI.Tests;

/// <summary>
///     Verifies that <c>pyrevit launch</c> keeps the journals Revit wrote into its launch directory (#3949).
/// </summary>
[Trait("Environment", "HostFree")]
[Trait("Level", "Integration")]
public class LaunchJournalTests : IDisposable {
    private readonly string temp = Path.Combine(Path.GetTempPath(), "pyRevit-journal-tests-" + Guid.NewGuid());
    private readonly string launchDirectory;
    private readonly string journalsDirectory;

    /// <summary>
    ///     Initializes a new instance of the <see cref="LaunchJournalTests"/> class with a launch directory as Revit leaves it.
    /// </summary>
    public LaunchJournalTests() {
        launchDirectory = Path.Combine(temp, "launch", "0123abcd");
        journalsDirectory = Path.Combine(temp, "Journals");
        Directory.CreateDirectory(launchDirectory);
        File.WriteAllText(Path.Combine(launchDirectory, "journal.0001.txt"), "session");
        File.WriteAllText(Path.Combine(launchDirectory, "journal.0001.worker1.log"), "worker");
        File.WriteAllText(Path.Combine(launchDirectory, "PyRevitLaunch.txt"), "played");
        File.WriteAllText(Path.Combine(launchDirectory, "pyRevit.addin"), "manifest");
    }

    /// <inheritdoc />
    public void Dispose() {
        Directory.Delete(temp, true);
    }

    /// <summary>
    ///     Verifies that the session journal and its worker logs are copied under names that carry the launch, and nothing else is.
    /// </summary>
    [Fact]
    public void TheSessionJournalsAreCopiedIntoTheJournalsFolder() {
        var saved = PyRevitLauncher.SaveJournals(launchDirectory, journalsDirectory);

        Assert.Equal(
            new[] { "journal.launch-0123abcd.0001.txt", "journal.launch-0123abcd.0001.worker1.log" },
            Directory.GetFiles(journalsDirectory).Select(Path.GetFileName).OrderBy(name => name, StringComparer.Ordinal));
        Assert.Equal("session", File.ReadAllText(Path.Combine(journalsDirectory, "journal.launch-0123abcd.0001.txt")));
        Assert.Equal(Path.Combine(journalsDirectory, "journal.launch-0123abcd.0001.txt"), Assert.Single(saved, path => path.EndsWith(".txt")));
    }

    /// <summary>
    ///     Verifies that a journal that can't be read is skipped and the others are still copied.
    /// </summary>
    [Fact]
    public void AJournalThatCanNotBeReadIsSkipped() {
        using (File.Open(Path.Combine(launchDirectory, "journal.0001.worker1.log"), FileMode.Open, FileAccess.Read, FileShare.None)) {
            PyRevitLauncher.SaveJournals(launchDirectory, journalsDirectory);
        }

        Assert.Equal(new[] { "journal.launch-0123abcd.0001.txt" }, Directory.GetFiles(journalsDirectory).Select(Path.GetFileName));
    }

    /// <summary>
    ///     Verifies that a launch whose Revit never wrote a journal leaves the Journals folder alone.
    /// </summary>
    [Fact]
    public void ALaunchWithoutJournalsCopiesNothing() {
        foreach (var journal in Directory.GetFiles(launchDirectory, "journal.*"))
            File.Delete(journal);

        Assert.Empty(PyRevitLauncher.SaveJournals(launchDirectory, journalsDirectory));
        Assert.False(Directory.Exists(journalsDirectory));
    }
}
