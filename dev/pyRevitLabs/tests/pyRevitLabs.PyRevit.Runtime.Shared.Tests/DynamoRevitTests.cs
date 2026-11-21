using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

using NUnit.Framework;

using pyRevitLabs.PyRevit.Runtime.Shared;

namespace Dynamo.Applications {
    public enum FakeDynamoResult {
        Succeeded,
        Cancelled,
        Failed
    }

    /// <summary>Stand-in for the Revit UI application handed to the fake Dynamo add-in.</summary>
    [Category("HostFree")]
    [Category("Unit")]
    public class FakeRevitUIApplication {
    }

    /// <summary>Stand-in Dynamo model whose state string the interop reads to decide whether the model is up.</summary>
    [Category("HostFree")]
    [Category("Unit")]
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
    [Category("HostFree")]
    [Category("Unit")]
    public class DynamoRevitApp {
        public static readonly List<IDictionary<string, string>> ReceivedJournalData =
            new List<IDictionary<string, string>>();

        public static readonly List<object> ReceivedApplications = new List<object>();

        public static FakeDynamoResult ResultToReturn = FakeDynamoResult.Succeeded;

        /// <summary>Clears the recorded calls and restores a succeeding result between tests.</summary>
        public static void Reset() {
            ReceivedJournalData.Clear();
            ReceivedApplications.Clear();
            ResultToReturn = FakeDynamoResult.Succeeded;
        }

        /// <summary>Records the journal data and application it receives and returns the configured result.</summary>
        public FakeDynamoResult ExecuteDynamoCommand(IDictionary<string, string> journalData,
                                                     FakeRevitUIApplication application) {
            ReceivedJournalData.Add(
                new Dictionary<string, string>(journalData, StringComparer.OrdinalIgnoreCase)
                );
            ReceivedApplications.Add(application);
            return ResultToReturn;
        }

        /// <summary>Decoy overload with extra parameters that the interop must never pick.</summary>
        public string ExecuteDynamoCommand(Dictionary<string, string> journalData,
                                           FakeRevitUIApplication application,
                                           bool forceManualRun) {
            throw new InvalidOperationException("Overload with extra parameters must not be called.");
        }
    }
}

namespace pyRevitLabs.PyRevit.Runtime.Shared.Tests {
    /// <summary>Covers headless Dynamo runs through reflection-only interop: the model is started before the graph runs, the run reports by model state, and manual graphs are not run under automation.</summary>
    [TestFixture]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [NonParallelizable]
    [Category("HostFree")]
    [Category("Unit")]
    public class DynamoRevitInteropTests {
        private const string GraphPath = @"C:\scripts\report.dyn";

        private string _tempRoot;

        /// <summary>Creates a scratch folder and clears the fake Dynamo state.</summary>
        [SetUp]
        public void Setup() {
            _tempRoot = Path.Combine(Path.GetTempPath(), "pyrevit-dynamo-tests-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(_tempRoot);
            Dynamo.Applications.DynamoRevitApp.Reset();
            Dynamo.Applications.DynamoRevit.RevitDynamoModel = null;
        }

        /// <summary>Clears the fake Dynamo state and deletes the scratch folder.</summary>
        [TearDown]
        public void Cleanup() {
            Dynamo.Applications.DynamoRevitApp.Reset();
            Dynamo.Applications.DynamoRevit.RevitDynamoModel = null;
            if (Directory.Exists(_tempRoot))
                Directory.Delete(_tempRoot, recursive: true);
        }

        /// <summary>A UIless run on a cold session sends a graph-free warm-up call that starts the model, then a second call carrying the graph to the same application.</summary>
        [Test]
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

            Assert.That(result.Status, Is.EqualTo(DynamoCommandStatus.Succeeded), "a UIless run starts the Dynamo model and then hands the graph over, so it runs "
                    + "even on a cold session");

            Assert.That(Dynamo.Applications.DynamoRevitApp.ReceivedJournalData.Count, Is.EqualTo(2), "a UIless run is a warm-up call followed by the call carrying the graph");

            var warmUpCall = Dynamo.Applications.DynamoRevitApp.ReceivedJournalData[0];
            Assert.That(warmUpCall.ContainsKey(DynamoJournalKeys.GraphPath), Is.False, "the warm-up call only starts the model and must not hand over a graph");
            Assert.That(warmUpCall[DynamoJournalKeys.ShutdownModel], Is.EqualTo("False"));
            Assert.That(warmUpCall[DynamoJournalKeys.ShowUI], Is.EqualTo("False"));

            var runCall = Dynamo.Applications.DynamoRevitApp.ReceivedJournalData[1];
            Assert.That(runCall[DynamoJournalKeys.GraphPath], Is.EqualTo(GraphPath));
            Assert.That(runCall[DynamoJournalKeys.ExecuteGraph], Is.EqualTo("True"));
            Assert.That(runCall[DynamoJournalKeys.ShutdownModel], Is.EqualTo("False"));
            Assert.That(runCall[DynamoJournalKeys.ForceManualRun], Is.EqualTo("True"));
            Assert.That(runCall[DynamoJournalKeys.ShowUI], Is.EqualTo("False"));

            Assert.That(Dynamo.Applications.DynamoRevitApp.ReceivedApplications.Count, Is.EqualTo(2));
            Assert.That(Dynamo.Applications.DynamoRevitApp.ReceivedApplications[0], Is.SameAs(application));
            Assert.That(Dynamo.Applications.DynamoRevitApp.ReceivedApplications[1], Is.SameAs(application));
        }

        /// <summary>No call of a UIless run asks Dynamo to shut the model down, even when the options request it.</summary>
        [Test]
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
                Assert.That(call[DynamoJournalKeys.ShutdownModel], Is.EqualTo("False"), "Dynamo shuts the model down instead of running the graph when a call asks for "
                        + "both, so a UIless run must not ask for the shutdown");
            }
        }

        /// <summary>A UIless run reports <c>Succeeded</c> when the Dynamo model is up.</summary>
        [Test]
        public void HeadlessRun_OnceDynamoModelIsUp_ReportsSucceeded() {
            Dynamo.Applications.DynamoRevit.RevitDynamoModel = new Dynamo.Applications.FakeRevitDynamoModel();

            var result = DynamoRevitInterop.Run(
                new DynamoExecutionOptions { GraphPath = GraphPath, ShowUI = false, ExecuteGraph = true },
                new Dynamo.Applications.FakeRevitUIApplication(),
                new string[0]
                );

            Assert.That(result.Status, Is.EqualTo(DynamoCommandStatus.Succeeded), "a UIless call does run the graph once the Dynamo model is up, so reporting "
                    + "NotRun here would be a false failure for a run that changed the model");
        }

        /// <summary>Model state cannot be read from a type outside the Dynamo add-in assembly, and the model is reported down.</summary>
        [Test]
        public void ModelUpDetection_ReportsUnavailableForAnUnrelatedAddin() {
            var detected = DynamoRevitInterop.TryGetModelUp(typeof(string), out var modelUp);

            Assert.That(detected, Is.False, "a type outside the add-in assembly has no Dynamo state to read");
            Assert.That(modelUp, Is.False);
        }

        /// <summary>A model whose state is not a started state is read as down.</summary>
        [Test]
        public void ModelUpDetection_TreatsAStoppedModelAsDown() {
            Dynamo.Applications.DynamoRevit.RevitDynamoModel = new Dynamo.Applications.FakeRevitDynamoModel {
                State = "NotStarted"
            };

            var detected = DynamoRevitInterop.TryGetModelUp(
                typeof(Dynamo.Applications.DynamoRevitApp),
                out var modelUp
                );

            Assert.That(detected, Is.True);
            Assert.That(modelUp, Is.False, "Dynamo keeps the model reference after a shutdown, so a model that is not in a "
                    + "started state must not be read as up");
        }

        /// <summary>A UIless run that also requests model shutdown reports <c>Succeeded</c> when the model is up.</summary>
        [Test]
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

            Assert.That(result.Status, Is.EqualTo(DynamoCommandStatus.Succeeded), "Dynamo can execute the graph before it handles the shutdown flag, so a shutdown "
                    + "request must not by itself be reported as a run that did not happen");
        }

        /// <summary>A run asking for neither automation nor graph execution reports <c>NotRun</c> even with the model up.</summary>
        [Test]
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

            Assert.That(result.Status, Is.EqualTo(DynamoCommandStatus.NotRun), "the tool asked Dynamo for neither automation nor graph execution, so it must not "
                    + "report a run even when a model is up");
        }

        /// <summary>An automation run without graph execution reports <c>Succeeded</c> when the model is up.</summary>
        [Test]
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

            Assert.That(result.Status, Is.EqualTo(DynamoCommandStatus.Succeeded), "automation on its own still asks Dynamo to run, so the result follows the model "
                    + "state rather than the ExecuteGraph flag alone");
        }

        /// <summary>A headless automation run of a graph saved on Manual reports <c>NotRun</c> naming the graph and run type, and never calls Dynamo.</summary>
        [Test]
        public void HeadlessAutomationRun_OfManualGraph_ReportsNotRunWithoutCallingDynamo() {
            Dynamo.Applications.DynamoRevit.RevitDynamoModel = new Dynamo.Applications.FakeRevitDynamoModel();
            var graphPath = WriteGraph("manual.dyn", runType: "Manual", hasRunWithoutCrash: true);

            var result = DynamoRevitInterop.Run(
                new DynamoExecutionOptions {
                    GraphPath = graphPath,
                    ShowUI = false,
                    Automate = true,
                    ExecuteGraph = true
                },
                new Dynamo.Applications.FakeRevitUIApplication(),
                new string[0]
                );

            Assert.That(result.Status, Is.EqualTo(DynamoCommandStatus.NotRun), "in automation mode Dynamo ignores dynPathExecute and only opens the graph, so a "
                    + "graph saved on Manual is never executed and must not be reported as a run");
            Assert.That(result.Message, Does.Contain("Manual"));
            Assert.That(result.Message, Does.Contain(graphPath));
            Assert.That(Dynamo.Applications.DynamoRevitApp.ReceivedJournalData.Count, Is.EqualTo(0), "a run known not to execute must not open the graph in Dynamo");
        }

        /// <summary>A headless automation run of a graph saved on Automatic warms up the model and hands the graph over.</summary>
        [Test]
        public void HeadlessAutomationRun_OfAutomaticGraph_RunsIt() {
            Dynamo.Applications.DynamoRevit.RevitDynamoModel = new Dynamo.Applications.FakeRevitDynamoModel();
            var graphPath = WriteGraph("automatic.dyn", runType: "Automatic", hasRunWithoutCrash: true);

            var result = DynamoRevitInterop.Run(
                new DynamoExecutionOptions {
                    GraphPath = graphPath,
                    ShowUI = false,
                    Automate = true,
                    ExecuteGraph = true
                },
                new Dynamo.Applications.FakeRevitUIApplication(),
                new string[0]
                );

            Assert.That(result.Status, Is.EqualTo(DynamoCommandStatus.Succeeded), result.Details);
            Assert.That(Dynamo.Applications.DynamoRevitApp.ReceivedJournalData.Count, Is.EqualTo(2));
            Assert.That(Dynamo.Applications.DynamoRevitApp.ReceivedJournalData[1][DynamoJournalKeys.GraphPath], Is.EqualTo(graphPath));
        }
        /// <summary>Without automation, a headless run executes the graph whether it is saved on Manual or Automatic.</summary>
        [TestCase("Manual")]
        [TestCase("Automatic")]
        public void HeadlessRunWithoutAutomation_RunsTheGraphWhateverItsRunSetting(string runType) {
            Dynamo.Applications.DynamoRevit.RevitDynamoModel = new Dynamo.Applications.FakeRevitDynamoModel();
            var graphPath = WriteGraph(runType.ToLowerInvariant() + ".dyn", runType, hasRunWithoutCrash: true);

            var result = DynamoRevitInterop.Run(
                new DynamoExecutionOptions {
                    GraphPath = graphPath,
                    ShowUI = false,
                    Automate = false,
                    ExecuteGraph = true
                },
                new Dynamo.Applications.FakeRevitUIApplication(),
                new string[0]
                );

            Assert.That(result.Status, Is.EqualTo(DynamoCommandStatus.Succeeded), "without automation Dynamo honours dynPathExecute and runs the graph whatever its own "
                    + "Run setting, so the run-setting check must not block it");
            Assert.That(Dynamo.Applications.DynamoRevitApp.ReceivedJournalData.Count, Is.EqualTo(2));
            var runCall = Dynamo.Applications.DynamoRevitApp.ReceivedJournalData[1];
            Assert.That(runCall[DynamoJournalKeys.GraphPath], Is.EqualTo(graphPath));
            Assert.That(runCall[DynamoJournalKeys.ExecuteGraph], Is.EqualTo("True"));
            Assert.That(runCall[DynamoJournalKeys.Automation], Is.EqualTo("False"));
        }

        /// <summary>Forcing a manual run under headless automation reports <c>NotRun</c> naming the option, and never calls Dynamo.</summary>
        [Test]
        public void HeadlessAutomationRun_WithForcedManualRun_ReportsNotRunWithoutCallingDynamo() {
            Dynamo.Applications.DynamoRevit.RevitDynamoModel = new Dynamo.Applications.FakeRevitDynamoModel();
            var graphPath = WriteGraph("automatic.dyn", runType: "Automatic", hasRunWithoutCrash: true);

            var result = DynamoRevitInterop.Run(
                new DynamoExecutionOptions {
                    GraphPath = graphPath,
                    ShowUI = false,
                    Automate = true,
                    ExecuteGraph = true,
                    ForceManualRun = true
                },
                new Dynamo.Applications.FakeRevitUIApplication(),
                new string[0]
                );

            Assert.That(result.Status, Is.EqualTo(DynamoCommandStatus.NotRun), "dynForceManualRun opens even an Automatic graph on Manual, which automation mode "
                    + "never executes");
            Assert.That(result.Message, Does.Contain("dynamo_force_manual_run"));
            Assert.That(Dynamo.Applications.DynamoRevitApp.ReceivedJournalData.Count, Is.EqualTo(0));
        }

        /// <summary>With the Dynamo UI shown, an automation run of a Manual graph still opens it in a single call.</summary>
        [Test]
        public void AutomationRunShowingUI_OfManualGraph_StillOpensItInDynamo() {
            var graphPath = WriteGraph("manual.dyn", runType: "Manual", hasRunWithoutCrash: true);

            var result = DynamoRevitInterop.Run(
                new DynamoExecutionOptions {
                    GraphPath = graphPath,
                    ShowUI = true,
                    Automate = true,
                    ExecuteGraph = true
                },
                new Dynamo.Applications.FakeRevitUIApplication(),
                new string[0]
                );

            Assert.That(result.Status, Is.EqualTo(DynamoCommandStatus.Succeeded), "with the Dynamo UI shown the user can press Run, so a Manual graph must still be "
                    + "opened rather than reported as not run");
            Assert.That(Dynamo.Applications.DynamoRevitApp.ReceivedJournalData.Count, Is.EqualTo(1));
            Assert.That(Dynamo.Applications.DynamoRevitApp.ReceivedJournalData[0][DynamoJournalKeys.GraphPath], Is.EqualTo(graphPath));
        }

        /// <summary>The graph run mode is read from JSON and legacy XML graphs, a graph that has not run without a crash reads as Manual, and a missing file reads as Unknown.</summary>
        [Test]
        public void GraphRunMode_FollowsDynamoLoadRules() {
            Assert.That(DynamoRevitInterop.ReadGraphRunMode(WriteGraph("auto.dyn", "Automatic", true)), Is.EqualTo(DynamoGraphRunMode.Automatic));
            Assert.That(DynamoRevitInterop.ReadGraphRunMode(WriteGraph("crashed.dyn", "Automatic", false)), Is.EqualTo(DynamoGraphRunMode.Manual), "Dynamo reopens a graph that has not run without a crash on Manual");
            Assert.That(DynamoRevitInterop.ReadGraphRunMode(WriteXmlGraph("legacy.dyn", "Manual")), Is.EqualTo(DynamoGraphRunMode.Manual));
            Assert.That(DynamoRevitInterop.ReadGraphRunMode(Path.Combine(_tempRoot, "missing.dyn")), Is.EqualTo(DynamoGraphRunMode.Unknown));
        }

        /// <summary>A run showing the UI makes one call that carries the graph, shows the UI and does not shut the model down.</summary>
        [Test]
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

            Assert.That(result.Succeeded, Is.True, result.Details);
            Assert.That(Dynamo.Applications.DynamoRevitApp.ReceivedJournalData.Count, Is.EqualTo(1));
            Assert.That(Dynamo.Applications.DynamoRevitApp.ReceivedJournalData[0][DynamoJournalKeys.GraphPath], Is.EqualTo(GraphPath));
            Assert.That(Dynamo.Applications.DynamoRevitApp.ReceivedJournalData[0][DynamoJournalKeys.ShowUI], Is.EqualTo("True"));
            Assert.That(Dynamo.Applications.DynamoRevitApp.ReceivedJournalData[0][DynamoJournalKeys.ShutdownModel], Is.EqualTo("False"));
        }

        /// <summary>A failed result from Dynamo is reported as <c>Rejected</c> with the result in the message.</summary>
        [Test]
        public void RunRejectedByDynamo_ReportsRejection() {
            Dynamo.Applications.DynamoRevitApp.ResultToReturn = Dynamo.Applications.FakeDynamoResult.Failed;

            var result = DynamoRevitInterop.Run(
                new DynamoExecutionOptions { GraphPath = GraphPath },
                new Dynamo.Applications.FakeRevitUIApplication(),
                new string[0]
                );

            Assert.That(result.Status, Is.EqualTo(DynamoCommandStatus.Rejected));
            Assert.That(result.Message, Does.Contain("Failed"));
        }

        /// <summary>Journal data uses unpadded Dynamo key names, always includes every option flag, and omits an empty graph path.</summary>
        [Test]
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

            Assert.That(journalData.Keys.ToArray(), Is.EquivalentTo(new[] {
                    DynamoJournalKeys.ShowUI,
                    DynamoJournalKeys.Automation,
                    DynamoJournalKeys.ShutdownModel,
                    DynamoJournalKeys.ReuseOpenGraph,
                    DynamoJournalKeys.ForceManualRun,
                    DynamoJournalKeys.ExecuteGraph
                }));

            Assert.That(journalData.All(entry => entry.Key.Trim() == entry.Key), Is.True, "journal keys must not be padded");
            Assert.That(journalData[DynamoJournalKeys.ReuseOpenGraph], Is.EqualTo("True"));
            Assert.That(journalData[DynamoJournalKeys.ForceManualRun], Is.EqualTo("True"));
            Assert.That(journalData[DynamoJournalKeys.Automation], Is.EqualTo("True"));
        }

        /// <summary>Journal data built without the graph drops the graph path, execution and nodes keys but keeps the model options.</summary>
        [Test]
        public void JournalDataWithoutGraph_OmitsGraphKeysButKeepsModelOptions() {
            var journalData = DynamoRevitInterop.BuildJournalData(
                new DynamoExecutionOptions { GraphPath = GraphPath, NodesInfo = "[]", ShutdownModel = true },
                includeGraph: false
                );

            Assert.That(journalData.ContainsKey(DynamoJournalKeys.GraphPath), Is.False);
            Assert.That(journalData.ContainsKey(DynamoJournalKeys.ExecuteGraph), Is.False);
            Assert.That(journalData.ContainsKey(DynamoJournalKeys.NodesInfo), Is.False);
            Assert.That(journalData.ContainsKey(DynamoJournalKeys.ShowUI), Is.True);
            Assert.That(journalData[DynamoJournalKeys.ShutdownModel], Is.EqualTo("True"));
        }

        /// <summary>Journal data carries the nodes info payload verbatim.</summary>
        [Test]
        public void JournalDataWithNodesInfo_CarriesPayload() {
            var journalData = DynamoRevitInterop.BuildJournalData(
                new DynamoExecutionOptions { GraphPath = GraphPath, NodesInfo = "[{\"Id\":\"1\"}]" },
                includeGraph: true
                );

            Assert.That(journalData[DynamoJournalKeys.NodesInfo], Is.EqualTo("[{\"Id\":\"1\"}]"));
        }

        /// <summary>Command resolution picks the overload taking only journal data and the application.</summary>
        [Test]
        public void ExecuteCommandMethod_ResolvesOverloadTakingJournalDataAndApplication() {
            var method = DynamoRevitInterop.ResolveExecuteDynamoCommandMethod(
                typeof(Dynamo.Applications.DynamoRevitApp),
                new Dictionary<string, string>(),
                new Dynamo.Applications.FakeRevitUIApplication()
                );

            Assert.That(method, Is.Not.Null);
            Assert.That(method.GetParameters().Length, Is.EqualTo(2));
        }

        /// <summary>Command resolution returns null for a type without a compatible command method.</summary>
        [Test]
        public void ExecuteCommandMethod_NotFoundForIncompatibleDynamo() {
            var method = DynamoRevitInterop.ResolveExecuteDynamoCommandMethod(
                typeof(string),
                new Dictionary<string, string>(),
                new Dynamo.Applications.FakeRevitUIApplication()
                );

            Assert.That(method, Is.Null);
        }

        /// <summary>Failed, cancelled and false results count as rejected; succeeded, true and null do not.</summary>
        [Test]
        public void RejectedResult_InterpretsDynamoResultAndBool() {
            Assert.That(DynamoRevitInterop.IsRejectedResult(Dynamo.Applications.FakeDynamoResult.Succeeded), Is.False);
            Assert.That(DynamoRevitInterop.IsRejectedResult(Dynamo.Applications.FakeDynamoResult.Failed), Is.True);
            Assert.That(DynamoRevitInterop.IsRejectedResult(Dynamo.Applications.FakeDynamoResult.Cancelled), Is.True);
            Assert.That(DynamoRevitInterop.IsRejectedResult(true), Is.False);
            Assert.That(DynamoRevitInterop.IsRejectedResult(false), Is.True);
            Assert.That(DynamoRevitInterop.IsRejectedResult(null), Is.False);
        }

        /// <summary>The Dynamo add-in type resolves with no add-in folders given and reports where it was resolved from.</summary>
        [Test]
        public void AppType_ResolvesLoadedAddinAssembly() {
            var appType = DynamoRevitInterop.ResolveDynamoRevitAppType(new string[0], out var resolvedFrom);

            Assert.That(appType, Is.Not.Null);
            Assert.That(appType.FullName, Is.EqualTo("Dynamo.Applications.DynamoRevitApp"));
            Assert.That(string.IsNullOrEmpty(resolvedFrom), Is.False);
        }

        /// <summary>The Dynamo assembly is found beside the assembly named by the Dynamo add-in manifest, ignoring other manifests.</summary>
        [Test]
        public void DynamoAssemblyFile_FoundNextToManifestAssembly() {
            var installDir = CreateFakeDynamoInstall();
            var addinsFolder = Path.Combine(_tempRoot, "addins");
            WriteManifest(addinsFolder, "SomeOther.addin", Path.Combine(installDir, "Other.dll"));
            WriteManifest(addinsFolder, "DynamoForRevit.addin", Path.Combine(installDir, "DynamoForRevit.dll"));

            var assemblyFile = DynamoRevitInterop.FindDynamoRevitAssemblyFile(new[] { addinsFolder });

            Assert.That(assemblyFile, Is.EqualTo(Path.Combine(installDir, "DynamoRevitDS.dll")));
        }

        /// <summary>No Dynamo assembly is found when manifests point at another install, the folder is missing, or folder entries are null or empty.</summary>
        [Test]
        public void DynamoAssemblyFile_NotFoundWithoutDynamoInstall() {
            var installDir = Path.Combine(_tempRoot, "otherinstall");
            Directory.CreateDirectory(installDir);
            File.WriteAllText(Path.Combine(installDir, "Other.dll"), "not an assembly");
            var addinsFolder = Path.Combine(_tempRoot, "addins");
            WriteManifest(addinsFolder, "SomeOther.addin", Path.Combine(installDir, "Other.dll"));

            Assert.That(DynamoRevitInterop.FindDynamoRevitAssemblyFile(new[] { addinsFolder }), Is.Null);
            Assert.That(DynamoRevitInterop.FindDynamoRevitAssemblyFile(new[] { Path.Combine(_tempRoot, "missing") }), Is.Null);
            Assert.That(DynamoRevitInterop.FindDynamoRevitAssemblyFile(new[] { addinsFolder, null, string.Empty }), Is.Null);
        }

        private string WriteGraph(string fileName, string runType, bool hasRunWithoutCrash) {
            var graphPath = Path.Combine(_tempRoot, fileName);
            File.WriteAllText(
                graphPath,
                "{\r\n"
                    + "  \"Uuid\": \"3c9d0464-8643-5ffe-96e5-ab1769818209\",\r\n"
                    + "  \"Nodes\": [ { \"Code\": \"x = \\\"RunType\\\": \\\"Automatic\\\"\" } ],\r\n"
                    + "  \"View\": {\r\n"
                    + "    \"Dynamo\": {\r\n"
                    + "      \"RunType\": \"" + runType + "\",\r\n"
                    + "      \"HasRunWithoutCrash\": " + (hasRunWithoutCrash ? "true" : "false") + "\r\n"
                    + "    }\r\n"
                    + "  }\r\n"
                    + "}\r\n"
                );
            return graphPath;
        }

        private string WriteXmlGraph(string fileName, string runType) {
            var graphPath = Path.Combine(_tempRoot, fileName);
            File.WriteAllText(
                graphPath,
                "<Workspace Version=\"1.3.0.0\" RunType=\"" + runType + "\" HasRunWithoutCrash=\"True\" />\r\n"
                );
            return graphPath;
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
