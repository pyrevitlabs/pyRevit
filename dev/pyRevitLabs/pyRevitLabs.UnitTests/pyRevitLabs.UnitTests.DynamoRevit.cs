using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

using Microsoft.VisualStudio.TestTools.UnitTesting;

using pyRevitLabs.PyRevit.Runtime.Shared;

namespace Dynamo.Applications {
    public enum FakeDynamoResult {
        Succeeded,
        Cancelled,
        Failed
    }

    public class FakeRevitUIApplication {
    }

    public class FakeRevitDynamoModel {
    }

    /// <summary>
    /// Stands in for Dynamo's per-Revit state holder. The interop reads
    /// <c>RevitDynamoModel</c> to tell whether a UIless call can run the graph.
    /// </summary>
    public static class DynamoRevit {
        public static FakeRevitDynamoModel RevitDynamoModel { get; set; }
    }

    /// <summary>
    /// Stands in for the Dynamo add-in type. It must keep this exact name so that the interop
    /// resolution finds it the same way it finds the real add-in.
    /// </summary>
    public class DynamoRevitApp {
        public static readonly List<IDictionary<string, string>> ReceivedJournalData =
            new List<IDictionary<string, string>>();

        public static readonly List<object> ReceivedApplications = new List<object>();

        public static FakeDynamoResult ResultToReturn = FakeDynamoResult.Succeeded;

        public static void Reset() {
            ReceivedJournalData.Clear();
            ReceivedApplications.Clear();
            ResultToReturn = FakeDynamoResult.Succeeded;
        }

        public FakeDynamoResult ExecuteDynamoCommand(IDictionary<string, string> journalData,
                                                     FakeRevitUIApplication application) {
            ReceivedJournalData.Add(
                new Dictionary<string, string>(journalData, StringComparer.OrdinalIgnoreCase)
                );
            ReceivedApplications.Add(application);
            return ResultToReturn;
        }

        public string ExecuteDynamoCommand(Dictionary<string, string> journalData,
                                           FakeRevitUIApplication application,
                                           bool forceManualRun) {
            throw new InvalidOperationException("Overload with extra parameters must not be called.");
        }
    }
}

namespace pyRevitLabs.UnitTests.DynamoRevit {
    [TestClass]
    public class DynamoRevitInteropTests {
        private const string GraphPath = @"C:\scripts\report.dyn";

        private string _tempRoot;

        [TestInitialize]
        public void Setup() {
            _tempRoot = Path.Combine(Path.GetTempPath(), "pyrevit-dynamo-tests-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(_tempRoot);
            Dynamo.Applications.DynamoRevitApp.Reset();
            Dynamo.Applications.DynamoRevit.RevitDynamoModel = null;
        }

        [TestCleanup]
        public void Cleanup() {
            if (Directory.Exists(_tempRoot))
                Directory.Delete(_tempRoot, recursive: true);
        }

        [TestMethod]
        public void HeadlessRun_BeforeDynamoModelIsUp_ReportsNotRun() {
            Dynamo.Applications.DynamoRevit.RevitDynamoModel = null;
            var application = new Dynamo.Applications.FakeRevitUIApplication();
            var options = new DynamoExecutionOptions {
                GraphPath = GraphPath,
                ShowUI = false,
                Automate = false,
                ExecuteGraph = true,
                ShutdownModel = true,
                ReuseOpenGraph = false,
                ForceManualRun = true
            };

            var result = DynamoRevitInterop.Run(options, application, new string[0]);

            Assert.AreEqual(
                DynamoCommandStatus.NotRun,
                result.Status,
                "Dynamo reports success for a UIless run issued before its model is up without "
                    + "executing anything, so the result must not claim the graph ran"
                );
            StringAssert.Contains(result.Message, "debug mode");

            Assert.AreEqual(
                1,
                Dynamo.Applications.DynamoRevitApp.ReceivedJournalData.Count,
                "a run must be a single Dynamo call: a call without the graph path makes Dynamo "
                    + "throw and raise a modal error dialog"
                );

            var call = Dynamo.Applications.DynamoRevitApp.ReceivedJournalData[0];
            Assert.AreEqual(GraphPath, call[DynamoJournalKeys.GraphPath]);
            Assert.AreEqual("True", call[DynamoJournalKeys.ExecuteGraph]);
            Assert.AreEqual("True", call[DynamoJournalKeys.ShutdownModel]);
            Assert.AreEqual("True", call[DynamoJournalKeys.ForceManualRun]);
            Assert.AreEqual("False", call[DynamoJournalKeys.ShowUI]);

            Assert.AreEqual(1, Dynamo.Applications.DynamoRevitApp.ReceivedApplications.Count);
            Assert.AreSame(application, Dynamo.Applications.DynamoRevitApp.ReceivedApplications[0]);
        }

        [TestMethod]
        public void HeadlessRun_OnceDynamoModelIsUp_ReportsSucceeded() {
            Dynamo.Applications.DynamoRevit.RevitDynamoModel = new Dynamo.Applications.FakeRevitDynamoModel();

            var result = DynamoRevitInterop.Run(
                new DynamoExecutionOptions { GraphPath = GraphPath, ShowUI = false },
                new Dynamo.Applications.FakeRevitUIApplication(),
                new string[0]
                );

            Assert.AreEqual(
                DynamoCommandStatus.Succeeded,
                result.Status,
                "a UIless call does run the graph once the Dynamo model is up, so reporting "
                    + "NotRun here would be a false failure for a run that changed the model"
                );
        }

        [TestMethod]
        public void ModelUpDetection_ReportsUnavailableForAnUnrelatedAddin() {
            var detected = DynamoRevitInterop.TryGetModelUp(typeof(string), out var modelUp);

            Assert.IsFalse(detected, "a type outside the add-in assembly has no Dynamo state to read");
            Assert.IsFalse(modelUp);
        }

        [TestMethod]
        public void RunShowingUI_IssuesSingleCallCarryingGraph() {
            var options = new DynamoExecutionOptions {
                GraphPath = GraphPath,
                ShowUI = true,
                ShutdownModel = true,
                ExecuteGraph = true
            };

            var result = DynamoRevitInterop.Run(
                options,
                new Dynamo.Applications.FakeRevitUIApplication(),
                new string[0]
                );

            Assert.IsTrue(result.Succeeded, result.Details);
            Assert.AreEqual(1, Dynamo.Applications.DynamoRevitApp.ReceivedJournalData.Count);
            Assert.AreEqual(GraphPath, Dynamo.Applications.DynamoRevitApp.ReceivedJournalData[0][DynamoJournalKeys.GraphPath]);
            Assert.AreEqual("True", Dynamo.Applications.DynamoRevitApp.ReceivedJournalData[0][DynamoJournalKeys.ShowUI]);
            Assert.AreEqual("True", Dynamo.Applications.DynamoRevitApp.ReceivedJournalData[0][DynamoJournalKeys.ShutdownModel]);
        }

        [TestMethod]
        public void RunRejectedByDynamo_ReportsRejection() {
            Dynamo.Applications.DynamoRevitApp.ResultToReturn = Dynamo.Applications.FakeDynamoResult.Failed;

            var result = DynamoRevitInterop.Run(
                new DynamoExecutionOptions { GraphPath = GraphPath },
                new Dynamo.Applications.FakeRevitUIApplication(),
                new string[0]
                );

            Assert.AreEqual(DynamoCommandStatus.Rejected, result.Status);
            StringAssert.Contains(result.Message, "Failed");
        }

        [TestMethod]
        public void JournalData_UsesDynamoKeyNamesAndAlwaysEmitsOptions() {
            var journalData = DynamoRevitInterop.BuildJournalData(
                new DynamoExecutionOptions {
                    GraphPath = string.Empty,
                    ShowUI = false,
                    Automate = true,
                    ExecuteGraph = true,
                    ShutdownModel = true,
                    ReuseOpenGraph = true,
                    ForceManualRun = true
                },
                includeGraph: true
                );

            CollectionAssert.AreEquivalent(
                new[] {
                    DynamoJournalKeys.ShowUI,
                    DynamoJournalKeys.Automation,
                    DynamoJournalKeys.ShutdownModel,
                    DynamoJournalKeys.ReuseOpenGraph,
                    DynamoJournalKeys.ForceManualRun,
                    DynamoJournalKeys.ExecuteGraph
                },
                journalData.Keys.ToArray()
                );

            Assert.IsTrue(journalData.All(entry => entry.Key.Trim() == entry.Key), "journal keys must not be padded");
            Assert.AreEqual("True", journalData[DynamoJournalKeys.ReuseOpenGraph]);
            Assert.AreEqual("True", journalData[DynamoJournalKeys.ForceManualRun]);
            Assert.AreEqual("True", journalData[DynamoJournalKeys.Automation]);
        }

        [TestMethod]
        public void JournalDataWithoutGraph_OmitsGraphKeysButKeepsModelOptions() {
            var journalData = DynamoRevitInterop.BuildJournalData(
                new DynamoExecutionOptions { GraphPath = GraphPath, NodesInfo = "[]", ShutdownModel = true },
                includeGraph: false
                );

            Assert.IsFalse(journalData.ContainsKey(DynamoJournalKeys.GraphPath));
            Assert.IsFalse(journalData.ContainsKey(DynamoJournalKeys.ExecuteGraph));
            Assert.IsFalse(journalData.ContainsKey(DynamoJournalKeys.NodesInfo));
            Assert.IsTrue(journalData.ContainsKey(DynamoJournalKeys.ShowUI));
            Assert.AreEqual("True", journalData[DynamoJournalKeys.ShutdownModel]);
        }

        [TestMethod]
        public void JournalDataWithNodesInfo_CarriesPayload() {
            var journalData = DynamoRevitInterop.BuildJournalData(
                new DynamoExecutionOptions { GraphPath = GraphPath, NodesInfo = "[{\"Id\":\"1\"}]" },
                includeGraph: true
                );

            Assert.AreEqual("[{\"Id\":\"1\"}]", journalData[DynamoJournalKeys.NodesInfo]);
        }

        [TestMethod]
        public void ExecuteCommandMethod_ResolvesOverloadTakingJournalDataAndApplication() {
            var method = DynamoRevitInterop.ResolveExecuteDynamoCommandMethod(
                typeof(Dynamo.Applications.DynamoRevitApp),
                new Dictionary<string, string>(),
                new Dynamo.Applications.FakeRevitUIApplication()
                );

            Assert.IsNotNull(method);
            Assert.AreEqual(2, method.GetParameters().Length);
        }

        [TestMethod]
        public void ExecuteCommandMethod_NotFoundForIncompatibleDynamo() {
            var method = DynamoRevitInterop.ResolveExecuteDynamoCommandMethod(
                typeof(string),
                new Dictionary<string, string>(),
                new Dynamo.Applications.FakeRevitUIApplication()
                );

            Assert.IsNull(method);
        }

        [TestMethod]
        public void RejectedResult_InterpretsDynamoResultAndBool() {
            Assert.IsFalse(DynamoRevitInterop.IsRejectedResult(Dynamo.Applications.FakeDynamoResult.Succeeded));
            Assert.IsTrue(DynamoRevitInterop.IsRejectedResult(Dynamo.Applications.FakeDynamoResult.Failed));
            Assert.IsTrue(DynamoRevitInterop.IsRejectedResult(Dynamo.Applications.FakeDynamoResult.Cancelled));
            Assert.IsFalse(DynamoRevitInterop.IsRejectedResult(true));
            Assert.IsTrue(DynamoRevitInterop.IsRejectedResult(false));
            Assert.IsFalse(DynamoRevitInterop.IsRejectedResult(null));
        }

        [TestMethod]
        public void AppType_ResolvesLoadedAddinAssembly() {
            var appType = DynamoRevitInterop.ResolveDynamoRevitAppType(new string[0], out var resolvedFrom);

            Assert.IsNotNull(appType);
            Assert.AreEqual("Dynamo.Applications.DynamoRevitApp", appType.FullName);
            Assert.IsFalse(string.IsNullOrEmpty(resolvedFrom));
        }

        [TestMethod]
        public void DynamoAssemblyFile_FoundNextToManifestAssembly() {
            var installDir = CreateFakeDynamoInstall();
            var addinsFolder = Path.Combine(_tempRoot, "addins");
            WriteManifest(addinsFolder, "SomeOther.addin", Path.Combine(installDir, "Other.dll"));
            WriteManifest(addinsFolder, "DynamoForRevit.addin", Path.Combine(installDir, "DynamoForRevit.dll"));

            var assemblyFile = DynamoRevitInterop.FindDynamoRevitAssemblyFile(new[] { addinsFolder });

            Assert.AreEqual(Path.Combine(installDir, "DynamoRevitDS.dll"), assemblyFile);
        }

        [TestMethod]
        public void DynamoAssemblyFile_NotFoundWithoutDynamoInstall() {
            var installDir = Path.Combine(_tempRoot, "otherinstall");
            Directory.CreateDirectory(installDir);
            File.WriteAllText(Path.Combine(installDir, "Other.dll"), "not an assembly");
            var addinsFolder = Path.Combine(_tempRoot, "addins");
            WriteManifest(addinsFolder, "SomeOther.addin", Path.Combine(installDir, "Other.dll"));

            Assert.IsNull(DynamoRevitInterop.FindDynamoRevitAssemblyFile(new[] { addinsFolder }));
            Assert.IsNull(DynamoRevitInterop.FindDynamoRevitAssemblyFile(new[] { Path.Combine(_tempRoot, "missing") }));
            Assert.IsNull(DynamoRevitInterop.FindDynamoRevitAssemblyFile(new[] { addinsFolder, null, string.Empty }));
        }

        private string CreateFakeDynamoInstall() {
            var installDir = Path.Combine(_tempRoot, "dynamoinstall");
            Directory.CreateDirectory(installDir);
            File.WriteAllText(Path.Combine(installDir, "DynamoRevitDS.dll"), "not an assembly");
            return installDir;
        }

        private static void WriteManifest(string addinsFolder, string manifestFile, string addinAssembly) {
            Directory.CreateDirectory(addinsFolder);
            File.WriteAllText(
                Path.Combine(addinsFolder, manifestFile),
                "<?xml version=\"1.0\" encoding=\"utf-8\" standalone=\"no\"?>\r\n"
                    + "<RevitAddIns>\r\n"
                    + "    <AddIn Type=\"Application\">\r\n"
                    + "        <Name>Test</Name>\r\n"
                    + "        <Assembly>" + addinAssembly + "</Assembly>\r\n"
                    + "        <AddInId>00000000-0000-0000-0000-000000000000</AddInId>\r\n"
                    + "        <FullClassName>Test.Addin</FullClassName>\r\n"
                    + "        <VendorId>PYRV</VendorId>\r\n"
                    + "    </AddIn>\r\n"
                    + "</RevitAddIns>\r\n"
                );
        }
    }
}
