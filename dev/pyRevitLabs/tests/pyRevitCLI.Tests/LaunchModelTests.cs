using pyRevitLabs.Common;
using pyRevitLabs.PyRevit;

namespace pyRevitCLI.Tests;

/// <summary>
///     Verifies the model that <c>pyrevit launch</c> opens when Revit starts (#3949).
/// </summary>
[Trait("Environment", "HostFree")]
[Trait("Level", "Integration")]
public class LaunchModelTests : IDisposable {
    private readonly string temp = Path.Combine(Path.GetTempPath(), "pyRevit-model-tests-" + Guid.NewGuid());
    private readonly string model;

    /// <summary>
    ///     Initializes a new instance of the <see cref="LaunchModelTests"/> class with a model file in a temporary folder.
    /// </summary>
    public LaunchModelTests() {
        Directory.CreateDirectory(temp);
        model = Path.Combine(temp, "Tower {A}.rvt");
        File.WriteAllText(model, string.Empty);
    }

    /// <inheritdoc />
    public void Dispose() {
        Directory.Delete(temp, true);
    }

    /// <summary>
    ///     Verifies that an existing model is returned as a full path and a blank one means no model.
    /// </summary>
    [Fact]
    public void AnExistingModelIsAFullPath() {
        var relative = Path.GetRelativePath(Environment.CurrentDirectory, model);

        Assert.Equal(model, PyRevitLauncher.ParseModel(" " + relative + " "));
        Assert.Null(PyRevitLauncher.ParseModel(null));
        Assert.Null(PyRevitLauncher.ParseModel("  "));
    }

    /// <summary>
    ///     Verifies that a model that does not exist is refused before anything is prepared.
    /// </summary>
    [Fact]
    public void AMissingModelIsRefused() {
        var missing = Path.Combine(temp, "Missing.rvt");

        var error = Assert.Throws<PyRevitException>(() => PyRevitLauncher.ParseModel(missing));

        Assert.Equal($"Can not find model \"{missing}\".", error.Message);
    }

    /// <summary>
    ///     Verifies that the launch journal opens the model the way Revit records a model passed on its command line.
    /// </summary>
    [Fact]
    public void TheJournalOpensTheModel() {
        var journal = PyRevitLauncher.BuildJournal(model);

        Assert.EndsWith(
            "Set Jrn = CrsJournalScript\n"
            + "Jrn.Command \"Internal\" , \"Open an existing project , ID_REVIT_FILE_OPEN\"\n"
            + "Jrn.Data \"File Name\" , \"IDOK\" , \"" + model + "\"\n",
            journal.Replace("\r\n", "\n"));
    }

    /// <summary>
    ///     Verifies that a launch without a model keeps the journal that only starts Revit.
    /// </summary>
    [Fact]
    public void WithoutAModelTheJournalOnlyStartsRevit() {
        Assert.EndsWith("Set Jrn = CrsJournalScript\n", PyRevitLauncher.BuildJournal(null).Replace("\r\n", "\n"));
    }
}
