using System;
using System.IO;
using Microsoft.VisualStudio.TestTools.UnitTesting;

using pyRevitLabs.Common;

// https://docs.microsoft.com/en-us/visualstudio/test/getting-started-with-unit-testing
namespace pyRevitLabs.UnitTests {
    [TestClass]
    public class TemplateUnitTest {
        private TestContext _testContextInstance;

        public virtual string TempPath { get; }

        [AssemblyInitialize()]
        public static void AssemblyInit(TestContext context) { }

        //https://docs.microsoft.com/en-us/dotnet/api/microsoft.visualstudio.testtools.unittesting.classinitializeattribute
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

        // https://docs.microsoft.com/en-us/dotnet/api/microsoft.visualstudio.testtools.unittesting.classcleanupattribute
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
