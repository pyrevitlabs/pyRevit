using pyRevitLabs.PyRevit;

namespace pyRevitLabs.PyRevit.Tests;

/// <summary>
///     Verifies how runner command files under an extension are named and resolved.
/// </summary>
[TestFixture]
[FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
[Category("HostFree")]
[Category("Unit")]
public class PyRevitRunnerCommandTests {
    private readonly string _extensionDir = Path.Combine(Path.GetTempPath(), "pyRevitRunnerCommands_" + Guid.NewGuid().ToString("N"));

    /// <summary>
    ///     Creates the extension's commands folder in a private temporary directory.
    /// </summary>
    [SetUp]
    public void Setup() {
        Directory.CreateDirectory(Path.Combine(_extensionDir, PyRevitConsts.ExtensionUICommandsDirName));
    }

    /// <summary>
    ///     Deletes the temporary extension folder.
    /// </summary>
    [TearDown]
    public void Cleanup() {
        if (Directory.Exists(_extensionDir))
            Directory.Delete(_extensionDir, recursive: true);
    }

    private string AddCommandFile(string fileName) {
        string path = Path.Combine(_extensionDir, PyRevitConsts.ExtensionUICommandsDirName, fileName);
        File.WriteAllText(path, string.Empty);
        return path;
    }

    [TestCase("hello_command.py", "hello")]
    [TestCase("Foo_Command.PY", "Foo")]
    [TestCase("Foo_COMMAND.py", "Foo")]
    [TestCase("my_command.py_command.py", "my_command.py")]
    [TestCase("a_command.py_command.PY", "a_command.py")]
    public void Name_DropsOnlyTheTrailingPostfixIgnoringCase(string fileName, string expectedName) {
        var command = new PyRevitRunnerCommand(Path.Combine("commands", fileName));

        Assert.That(command.Name, Is.EqualTo(expectedName));
    }

    [Test]
    public void GetCommands_ListsOnlyCommandPostfixFilesUnderTheirCleanName() {
        AddCommandFile("hello_command.py");
        AddCommandFile("Foo_Command.PY");
        AddCommandFile("helpers.py");

        var names = PyRevitExtension.GetCommands(_extensionDir).Select(c => c.Name).OrderBy(n => n).ToArray();

        Assert.That(names, Is.EqualTo(new[] { "Foo", "hello" }));
    }

    [Test]
    public void GetCommand_ResolvesMixedCasePostfixByCleanName() {
        string path = AddCommandFile("Foo_Command.PY");

        var command = PyRevitExtension.GetCommand(_extensionDir, "foo");

        Assert.That(command.Path, Is.EqualTo(path));
    }
}
