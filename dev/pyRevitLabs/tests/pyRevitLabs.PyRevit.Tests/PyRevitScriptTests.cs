using pyRevitLabs.PyRevit;

namespace pyRevitLabs.PyRevit.Tests {
    /// <summary>Script-file classification remains independent of interpreter installation.</summary>
    [TestFixture]
    [Category("HostFree")]
    [Category("Unit")]
    public class PyRevitScriptTests {
        /// <summary>Recognizes supported file types without executing the script.</summary>
        [TestCase("SCRIPT.PY", PyRevitScriptTypes.Python, true)]
        [TestCase("tool.cs", PyRevitScriptTypes.CSharp, true)]
        [TestCase("tool.txt", PyRevitScriptTypes.Python, false)]
        public void IsType_RecognizesScriptExtension(string path, PyRevitScriptTypes type, bool expected) {
            Assert.That(PyRevitScript.IsType(path, type), Is.EqualTo(expected));
        }
    }
}
