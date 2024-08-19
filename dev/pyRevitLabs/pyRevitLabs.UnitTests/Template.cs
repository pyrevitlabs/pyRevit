using System.IO;
using Microsoft.VisualStudio.TestTools.UnitTesting;

using pyRevitLabs.Common;

namespace pyRevitLabs.UnitTests
{
    [TestClass]
    public class TemplateUnitTest {
        private TestContext _testContextInstance;

        public virtual string TempPath { get; }

        [AssemblyInitialize()]
        public static void AssemblyInit(TestContext context) { }

        [ClassInitialize()]
        public static void ClassInit(TestContext context) { }

        [TestInitialize()]
        public void Initialize() {
            if (!Directory.Exists(TempPath))
                Directory.CreateDirectory(TempPath);
            else
                Cleanup();
        }

        [TestCleanup()]
        public void Cleanup() {
            try {
                CommonUtils.DeleteDirectory(TempPath);
            }
            catch {

            }
        }

        [ClassCleanup()]
        public static void ClassCleanup() { }

        [AssemblyCleanup()]
        public static void AssemblyCleanup() { }


        public TestContext TestContext {
            get { return _testContextInstance; }
            set { _testContextInstance = value; }
        }
    }
}
