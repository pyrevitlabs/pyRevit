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
        public string State { get; set; } = "StartedUI";
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
        public void HeadlessRun_StartsTheModelBeforeHandingOverTheGraph() {
            Dynamo.Applications.DynamoRevit.RevitDynamoModel = null;
            var application = new Dynamo.Applications.FakeRevitUIApplication();
            var options = new DynamoExecutionOptions {
                GraphPath = GraphPath,
                ShowUI = false,
                Automate = false,
                ExecuteGraph = true,
                ShutdownModel = false,
                ReuseOpenGraph = false,
                ForceManualRun = true
            };

            var result = DynamoRevitInterop.Run(options, application, new string[0]);

            Assert.AreEqual(
                DynamoCommandStatus.Succeeded,
                result.Status,
                "a UIless run starts the Dynamo model and then hands the graph over, so it runs "
                    + "even on a cold session"
                );

            Assert.AreEqual(
                2,
                Dynamo.Applications.DynamoRevitApp.ReceivedJournalData.Count,
                "a UIless run is a warm-up call followed by the call carrying the graph"
                );

            var warmUpCall = Dynamo.Applications.DynamoRevitApp.ReceivedJournalData[0];
            Assert.IsFalse(
                warmUpCall.ContainsKey(DynamoJournalKeys.GraphPath),
                "the warm-up call only starts the model and must not hand over a graph"
                );
            Assert.AreEqual("False", warmUpCall[DynamoJournalKeys.ShutdownModel]);
            Assert.AreEqual("False", warmUpCall[DynamoJournalKeys.ShowUI]);

            var runCall = Dynamo.Applications.DynamoRevitApp.ReceivedJournalData[1];
            Assert.AreEqual(GraphPath, runCall[DynamoJournalKeys.GraphPath]);
            Assert.AreEqual("True", runCall[DynamoJournalKeys.ExecuteGraph]);
            Assert.AreEqual("False", runCall[DynamoJournalKeys.ShutdownModel]);
            Assert.AreEqual("True", runCall[DynamoJournalKeys.ForceManualRun]);
            Assert.AreEqual("False", runCall[DynamoJournalKeys.ShowUI]);

            Assert.AreEqual(2, Dynamo.Applications.DynamoRevitApp.ReceivedApplications.Count);
            Assert.AreSame(application, Dynamo.Applications.DynamoRevitApp.ReceivedApplications[0]);
            Assert.AreSame(application, Dynamo.Applications.DynamoRevitApp.ReceivedApplications[1]);
        }

        [TestMethod]
        public void HeadlessRun_DropsTheModelShutdownSoDynamoCanRunTheGraph() {
            Dynamo.Applications.DynamoRevit.RevitDynamoModel = new Dynamo.Applications.FakeRevitDynamoModel();

            DynamoRevitInterop.Run(
                new DynamoExecutionOptions {
                    GraphPath = GraphPath,
                    ShowUI = false,
                    ShutdownModel = true,
                    ExecuteGraph = true
                },
                new Dynamo.Applications.FakeRevitUIApplication(),
                new string[0]
                );

            foreach (var call in Dynamo.Applications.DynamoRevitApp.ReceivedJournalData) {
                Assert.AreEqual(
                    "False",
                    call[DynamoJournalKeys.ShutdownModel],
                    "Dynamo shuts the model down instead of running the graph when a call asks for "
                        + "both, so a UIless run must not ask for the shutdown"
                    );
            }
        }

        [TestMethod]
        public void HeadlessRun_OnceDynamoModelIsUp_ReportsSucceeded() {
            Dynamo.Applications.DynamoRevit.RevitDynamoModel = new Dynamo.Applications.FakeRevitDynamoModel();

            var result = DynamoRevitInterop.Run(
                new DynamoExecutionOptions { GraphPath = GraphPath, ShowUI = false, ExecuteGraph = true },
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
        public void ModelUpDetection_TreatsAStoppedModelAsDown() {
            Dynamo.Applications.DynamoRevit.RevitDynamoModel = new Dynamo.Applications.FakeRevitDynamoModel {
                State = "NotStarted"
            };

            var detected = DynamoRevitInterop.TryGetModelUp(
                typeof(Dynamo.Applications.DynamoRevitApp),
                out var modelUp
                );

            Assert.IsTrue(detected);
            Assert.IsFalse(
                modelUp,
                "Dynamo keeps the model reference after a shutdown, so a model that is not in a "
                    + "started state must not be read as up"
                );
        }

        [TestMethod]
        public void RunAskingForShutdown_StillDecidesByModelState() {
            Dynamo.Applications.DynamoRevit.RevitDynamoModel = new Dynamo.Applications.FakeRevitDynamoModel();

            var result = DynamoRevitInterop.Run(
                new DynamoExecutionOptions {
                    GraphPath = GraphPath,
                    ShowUI = false,
                    ShutdownModel = true,
                    ExecuteGraph = true
                },
                new Dynamo.Applications.FakeRevitUIApplication(),
                new string[0]
                );

            Assert.AreEqual(
                DynamoCommandStatus.Succeeded,
                result.Status,
                "Dynamo can execute the graph before it handles the shutdown flag, so a shutdown "
                    + "request must not by itself be reported as a run that did not happen"
                );
        }

        [TestMethod]
        public void RunRequestingNeitherAutomationNorExecution_ReportsNotRun() {
            Dynamo.Applications.DynamoRevit.RevitDynamoModel = new Dynamo.Applications.FakeRevitDynamoModel();

            var result = DynamoRevitInterop.Run(
                new DynamoExecutionOptions {
                    GraphPath = GraphPath,
                    ShowUI = false,
                    Automate = false,
                    ExecuteGraph = false
                },
                new Dynamo.Applications.FakeRevitUIApplication(),
                new string[0]
                );

            Assert.AreEqual(
                DynamoCommandStatus.NotRun,
                result.Status,
                "the tool asked Dynamo for neither automation nor graph execution, so it must not "
                    + "report a run even when a model is up"
                );
        }

        [TestMethod]
        public void RunRequestingAutomationOnly_StillReportsByModelState() {
            Dynamo.Applications.DynamoRevit.RevitDynamoModel = new Dynamo.Applications.FakeRevitDynamoModel();

            var result = DynamoRevitInterop.Run(
                new DynamoExecutionOptions {
                    GraphPath = GraphPath,
                    ShowUI = false,
                    Automate = true,
                    ExecuteGraph = false
                },
                new Dynamo.Applications.FakeRevitUIApplication(),
                new string[0]
                );

            Assert.AreEqual(
                DynamoCommandStatus.Succeeded,
                result.Status,
                "automation on its own still asks Dynamo to run, so the result follows the model "
                    + "state rather than the ExecuteGraph flag alone"
                );
        }

        [TestMethod]
        public void RunShowingUI_IssuesSingleCallCarryingGraph() {
            var options = new DynamoExecutionOptions {
                GraphPath = GraphPath,
                ShowUI = true,
                ShutdownModel = false,
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
            Assert.AreEqual("False", Dynamo.Applications.DynamoRevitApp.ReceivedJournalData[0][DynamoJournalKeys.ShutdownModel]);
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
