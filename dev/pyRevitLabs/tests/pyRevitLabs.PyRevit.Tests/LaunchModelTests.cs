using pyRevitLabs.Common;
using pyRevitLabs.PyRevit;

namespace pyRevitLabs.PyRevit.Tests;

/// <summary>
///     Verifies the model that <c>pyrevit launch</c> opens when Revit starts (#3949).
/// </summary>
[TestFixture]
[NonParallelizable]
[Category("HostFree")]
[Category("Integration")]
public class LaunchModelTests {
    private string temp = string.Empty;
    private string model = string.Empty;

    /// <summary>
    ///     Creates a model file in a temporary folder.
    /// </summary>
    [SetUp]
    public void SetUp() {
        temp = Path.Combine(Path.GetTempPath(), "pyRevit-model-tests-" + Guid.NewGuid());
        Directory.CreateDirectory(temp);
        model = Path.Combine(temp, "Tower {A}.rvt");
        File.WriteAllText(model, string.Empty);
    }

    /// <summary>
    ///     Deletes the test's folder.
    /// </summary>
    [TearDown]
    public void TearDown() {
        Directory.Delete(temp, true);
    }

    /// <summary>
    ///     Verifies that an existing model is returned as a full path and a blank one means no model.
    /// </summary>
    [Test]
    public void AnExistingModelIsAFullPath() {
        var previousDirectory = Environment.CurrentDirectory;
        Environment.CurrentDirectory = temp;
        try {
            Assert.That(PyRevitLauncher.ParseModel(" " + Path.GetFileName(model) + " "), Is.EqualTo(model));
        }
        finally {
            Environment.CurrentDirectory = previousDirectory;
        }
        Assert.That(PyRevitLauncher.ParseModel(null), Is.Null);
        Assert.That(PyRevitLauncher.ParseModel("  "), Is.Null);
    }

    /// <summary>
    ///     Verifies that a model that does not exist is refused before anything is prepared.
    /// </summary>
    [Test]
    public void AMissingModelIsRefused() {
        var missing = Path.Combine(temp, "Missing.rvt");

        var error = Assert.Throws<PyRevitException>(() => PyRevitLauncher.ParseModel(missing));

        Assert.That(error!.Message, Is.EqualTo($"Can not find model \"{missing}\"."));
    }

    /// <summary>
    ///     Verifies that a model path with characters outside ASCII is refused, because Revit 2026 failed to open
    ///     such a path from the journal ("Failed to open document").
    /// </summary>
    [Test]
    public void AModelPathOutsideAsciiIsRefused() {
        var accented = Path.Combine(temp, "Torre Año.rvt");
        File.WriteAllText(accented, string.Empty);

        var error = Assert.Throws<PyRevitException>(() => PyRevitLauncher.ParseModel(accented));

        Assert.That(error!.Message, Does.Contain("only ASCII characters"));
    }

    /// <summary>
    ///     Verifies that the launch journal opens the model the way Revit records a model passed on its command line.
    /// </summary>
    [Test]
    public void TheJournalOpensTheModel() {
        var journal = PyRevitLauncher.BuildJournal(model);

        Assert.That(
            journal.Replace("\r\n", "\n"),
            Does.EndWith(
                "Set Jrn = CrsJournalScript\n"
                + "Jrn.Command \"Internal\" , \"Open an existing project , ID_REVIT_FILE_OPEN\"\n"
                + "Jrn.Data \"File Name\" , \"IDOK\" , \"" + model + "\"\n"));
    }

    /// <summary>
    ///     Verifies that a launch without a model keeps the journal that only starts Revit.
    /// </summary>
    [Test]
    public void WithoutAModelTheJournalOnlyStartsRevit() {
        Assert.That(PyRevitLauncher.BuildJournal(null).Replace("\r\n", "\n"), Does.EndWith("Set Jrn = CrsJournalScript\n"));
    }
}
