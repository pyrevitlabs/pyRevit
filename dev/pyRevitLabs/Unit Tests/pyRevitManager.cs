using System;
using System.Diagnostics;
using System.IO;
using Microsoft.VisualStudio.TestTools.UnitTesting;

using pyRevitLabs.Common;
using pyRevitLabs.TargetApps.Revit;

namespace pyRevitLabs.Tests {
    [TestClass()]
    public class PyRevitCLI: TemplateUnitTest {

        private const string cliBinaryName = "pyrevit.exe";
        private const string testCloneName = "TestClone";
        private string TestClonePath => Path.Combine(TempPath, testCloneName);

        public override string TempPath =>
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "PyRevitCLI-Tests");

        // helper function to run cli commands ang log results
        private void RunCommand(string arguments) {
            // setup cli process
            ProcessStartInfo updaterProcessInfo = new ProcessStartInfo(cliBinaryName);
            updaterProcessInfo.Arguments = arguments + " --debug";
            //updaterProcessInfo.WorkingDirectory = 
            updaterProcessInfo.UseShellExecute = false;
            updaterProcessInfo.RedirectStandardOutput = true;
            updaterProcessInfo.CreateNoWindow = true;

            // run and collect output
            var process = Process.Start(updaterProcessInfo);
            string output = process.StandardOutput.ReadToEnd();
            process.WaitForExit();

            // write results to test context
            TestContext.WriteLine(output);
        }

        [TestMethod()]
        public void DeployFromImage_Full_Test() {
            var testCloneBranch = "master";

            RunCommand(string.Format("clone \"{0}\" core --dest=\"{1}\"", testCloneName, TempPath));

            var clone = PyRevitClones.GetRegisteredClone(testCloneName);
            PyRevitClones.UnregisterClone(clone);
            Assert.AreEqual(testCloneBranch, clone.Branch, string.Format("{0} != {1}", testCloneBranch, clone.Branch));
        }
    }
}
