using System;
using System.IO;
using System.Linq;

using Microsoft.VisualStudio.TestTools.UnitTesting;

using pyRevitLabs.PyRevit;

namespace pyRevitLabs.UnitTests {
    [TestClass]
    [TestCategory("HostFree")]
    [TestCategory("Unit")]
    public class PyRevitRunnerCommandTests {
        private string _extensionDir;

        [TestInitialize]
        public void Setup() {
            _extensionDir = Path.Combine(Path.GetTempPath(), "pyRevitRunnerCommands_" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(Path.Combine(_extensionDir, PyRevitConsts.ExtensionUICommandsDirName));
        }

        [TestCleanup]
        public void Cleanup() {
            if (Directory.Exists(_extensionDir))
                Directory.Delete(_extensionDir, recursive: true);
        }

        private string AddCommandFile(string fileName) {
            string path = Path.Combine(_extensionDir, PyRevitConsts.ExtensionUICommandsDirName, fileName);
            File.WriteAllText(path, string.Empty);
            return path;
        }

        [TestMethod]
        [DataRow("hello_command.py", "hello")]
        [DataRow("Foo_Command.PY", "Foo")]
        [DataRow("Foo_COMMAND.py", "Foo")]
        [DataRow("my_command.py_command.py", "my_command.py")]
        [DataRow("a_command.py_command.PY", "a_command.py")]
        public void Name_DropsOnlyTheTrailingPostfixIgnoringCase(string fileName, string expectedName) {
            var command = new PyRevitRunnerCommand(Path.Combine("commands", fileName));

            Assert.AreEqual(expectedName, command.Name);
        }

        [TestMethod]
        public void GetCommands_ListsOnlyCommandPostfixFilesUnderTheirCleanName() {
            AddCommandFile("hello_command.py");
            AddCommandFile("Foo_Command.PY");
            AddCommandFile("helpers.py");

            var names = PyRevitExtension.GetCommands(_extensionDir).Select(c => c.Name).OrderBy(n => n).ToArray();

            CollectionAssert.AreEqual(new[] { "Foo", "hello" }, names);
        }

        [TestMethod]
        public void GetCommand_ResolvesMixedCasePostfixByCleanName() {
            string path = AddCommandFile("Foo_Command.PY");

            var command = PyRevitExtension.GetCommand(_extensionDir, "foo");

            Assert.AreEqual(path, command.Path);
        }
    }
}
