using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Xml;

namespace pyRevitLabs.PyRevit.Runtime.Shared {
    /// <summary>
    /// Journal data keys read by <c>Dynamo.Applications.DynamoRevit.ExecuteCommand</c> in Dynamo
    /// for Revit. Unrecognized keys are ignored without warning, so these must match Dynamo's
    /// own <c>JournalKeys</c> exactly, including casing and without trailing whitespace.
    /// </summary>
    public static class DynamoJournalKeys {
        public const string ShowUI = "dynShowUI";
        public const string Automation = "dynAutomation";
        public const string GraphPath = "dynPath";
        public const string ExecuteGraph = "dynPathExecute";
        public const string ShutdownModel = "dynModelShutDown";
        public const string NodesInfo = "dynModelNodesInfo";

        /// <summary>Run the graph even when its own "Run" setting is on manual.</summary>
        public const string ForceManualRun = "dynForceManualRun";

        /// <summary>Reuse the currently open workspace when it is already the requested graph.</summary>
        public const string ReuseOpenGraph = "dynPathCheckExisting";
    }

    /// <summary>
    /// Execution settings for a Dynamo graph run, mapped one-to-one onto Dynamo's journal data.
    /// </summary>
    public class DynamoExecutionOptions {
        /// <summary>Full path to the <c>.dyn</c> graph to open. Ignored when empty.</summary>
        public string GraphPath { get; set; }

        /// <summary>JSON payload with node values to push after the graph is opened.</summary>
        public string NodesInfo { get; set; }

        /// <summary>Bring up the Dynamo UI. Forces a single Dynamo call, see the interop remarks.</summary>
        public bool ShowUI { get; set; }

        /// <summary>Run on the main thread without the idle loop.</summary>
        public bool Automate { get; set; }

        public bool ExecuteGraph { get; set; }

        public bool ShutdownModel { get; set; }

        public bool ReuseOpenGraph { get; set; }

        public bool ForceManualRun { get; set; }

        public DynamoExecutionOptions WithShutdownModel(bool shutdownModel) {
            return new DynamoExecutionOptions {
                GraphPath = GraphPath,
                NodesInfo = NodesInfo,
                ShowUI = ShowUI,
                Automate = Automate,
                ExecuteGraph = ExecuteGraph,
                ShutdownModel = shutdownModel,
                ReuseOpenGraph = ReuseOpenGraph,
                ForceManualRun = ForceManualRun
            };
        }
    }

    public enum DynamoCommandStatus {
        Succeeded,
        DynamoUnavailable,
        IncompatibleDynamo,
        Rejected,
        Failed
    }

    /// <summary>Outcome of a Dynamo command run, with a user facing message and full diagnostics.</summary>
    public class DynamoCommandResult {
        public DynamoCommandStatus Status { get; }

        public string Message { get; }

        public string Details { get; }

        public bool Succeeded => Status == DynamoCommandStatus.Succeeded;

        public DynamoCommandResult(DynamoCommandStatus status, string message, string details) {
            Status = status;
            Message = message;
            Details = details;
        }
    }

    /// <summary>
    /// Resolves and drives <c>Dynamo.Applications.DynamoRevitApp.ExecuteDynamoCommand</c>, the
    /// entry point Dynamo for Revit exposes to add-ins that run a graph outside the Dynamo UI.
    ///
    /// Important: Dynamo only reads the graph path (<c>dynPath</c>) when it already has a UIless
    /// model up and is not being asked to replace that model in the same call. On a cold session
    /// <c>DynamoRevit.ExecuteCommand</c> only initializes the model and returns without touching
    /// the path, and a call that requests <c>dynModelShutDown</c> tears the model down and starts
    /// over. Both cases report <c>Result.Succeeded</c> while running nothing, which is why a
    /// UIless run is issued as a prepare call without the path followed by a call that carries
    /// the path and keeps the model. Showing the UI is left to a single call because Dynamo opens
    /// the graph itself on that path.
    ///
    /// Invariant: this type must stay free of Revit API types so it can be exercised outside of a
    /// Revit host. The active <c>UIApplication</c> is passed in as a plain object.
    /// </summary>
    public static class DynamoRevitInterop {
        /// <summary>Assembly the Dynamo for Revit add-in ships in.</summary>
        public const string AppAssemblyName = "DynamoRevitDS";

        /// <summary>Full name of the Dynamo for Revit external application type.</summary>
        public const string AppTypeName = "Dynamo.Applications.DynamoRevitApp";

        /// <summary>Method on the app type that runs a graph from the journal data.</summary>
        public const string ExecuteCommandMethodName = "ExecuteDynamoCommand";

        private const string DynamoNotAvailableMessage =
            "Can not find Dynamo installation or determine which Dynamo version to Run.\n\n"
            + "Make sure Dynamo for Revit is installed for this Revit version, and run Dynamo "
            + "once to select the active version.";

        /// <summary>
        /// Hands <paramref name="options"/> to Dynamo, resolving the add-in assembly, the app type
        /// and the command method from whatever Dynamo version is present.
        /// </summary>
        /// <param name="options">Graph run settings.</param>
        /// <param name="uiApplication">Active <c>UIApplication</c> of the host session.</param>
        /// <param name="addinsFolders">
        /// Folders holding Revit add-in manifests, searched only when Dynamo is not loaded yet.
        /// </param>
        public static DynamoCommandResult Run(DynamoExecutionOptions options,
                                              object uiApplication,
                                              IEnumerable<string> addinsFolders) {
            if (options == null)
                throw new ArgumentNullException(nameof(options));
            if (uiApplication == null)
                throw new ArgumentNullException(nameof(uiApplication));

            var journalData = BuildJournalDataPhases(options);
            var diagnostics = new StringBuilder();

            Type appType;
            try {
                appType = ResolveDynamoRevitAppType(addinsFolders, out var resolvedFrom);
                diagnostics.AppendLine("Resolved Dynamo from: " + (resolvedFrom ?? "<not found>"));
            }
            catch (Exception resolveEx) {
                return Failed(DynamoCommandStatus.DynamoUnavailable, DynamoNotAvailableMessage, resolveEx, diagnostics);
            }

            if (appType == null)
                return Failed(DynamoCommandStatus.DynamoUnavailable, DynamoNotAvailableMessage, null, diagnostics);

            var executeCommand = ResolveExecuteDynamoCommandMethod(appType, journalData[0], uiApplication);
            if (executeCommand == null)
                return Failed(
                    DynamoCommandStatus.IncompatibleDynamo,
                    "Can not find \"" + ExecuteCommandMethodName + "\" on the installed Dynamo version.\n\n"
                        + "This tool needs a Dynamo version that can run graphs from an add-in.",
                    null,
                    diagnostics
                    );

            object app;
            try {
                app = Activator.CreateInstance(appType, nonPublic: true);
            }
            catch (Exception createEx) {
                return Failed(DynamoCommandStatus.IncompatibleDynamo, "Error initializing Dynamo.", createEx, diagnostics);
            }

            foreach (var data in journalData) {
                diagnostics.AppendLine("Dynamo call: " + DescribeJournalData(data));
                object invokeResult;
                try {
                    invokeResult = executeCommand.Invoke(app, new object[] { data, uiApplication });
                }
                catch (Exception invokeEx) {
                    return Failed(DynamoCommandStatus.Failed, "Error executing Dynamo script.", invokeEx, diagnostics);
                }

                if (IsRejectedResult(invokeResult)) {
                    diagnostics.AppendLine("Dynamo result: " + invokeResult);
                    return Failed(
                        DynamoCommandStatus.Rejected,
                        "Dynamo did not run the graph.\n\nDynamo returned: " + invokeResult,
                        null,
                        diagnostics
                        );
                }
            }

            return new DynamoCommandResult(
                DynamoCommandStatus.Succeeded,
                "Dynamo reported that it ran the graph. A headless run cannot be confirmed from "
                    + "Dynamo's answer alone - check the model for the graph's effect.",
                diagnostics.ToString());
        }

        /// <summary>
        /// Locates the Dynamo add-in type, preferring an already loaded assembly over one loaded
        /// from the add-in manifest of the host Revit version.
        /// </summary>
        /// <remarks>
        /// The host can load the add-in into a context of its own, where the assembly is not named
        /// after the add-in, so the type is also looked for across every loaded assembly.
        /// </remarks>
        /// <param name="addinsFolders">Revit add-in manifest folders to fall back to.</param>
        /// <param name="resolvedFrom">Assembly name or path the type was resolved from.</param>
        /// <returns>The app type, or null when no Dynamo installation can be found.</returns>
        public static Type ResolveDynamoRevitAppType(IEnumerable<string> addinsFolders, out string resolvedFrom) {
            var loadedAssemblies = AppDomain.CurrentDomain.GetAssemblies();

            foreach (var assembly in loadedAssemblies) {
                if (string.Equals(assembly.GetName().Name, AppAssemblyName, StringComparison.OrdinalIgnoreCase)) {
                    var appType = assembly.GetType(AppTypeName, throwOnError: false);
                    if (appType != null) {
                        resolvedFrom = assembly.GetName().Name;
                        return appType;
                    }
                }
            }

            foreach (var assembly in loadedAssemblies) {
                var appType = assembly.GetType(AppTypeName, throwOnError: false);
                if (appType != null) {
                    resolvedFrom = assembly.FullName;
                    return appType;
                }
            }

            var assemblyPath = FindDynamoRevitAssemblyFile(addinsFolders);
            if (assemblyPath == null) {
                resolvedFrom = null;
                return null;
            }

            var dynamoAssembly = Assembly.LoadFrom(assemblyPath);
            resolvedFrom = assemblyPath;
            return dynamoAssembly.GetType(AppTypeName, throwOnError: false);
        }

        /// <summary>
        /// Reads the Dynamo add-in manifests in <paramref name="addinsFolders"/> and returns the
        /// <c>DynamoRevitDS</c> assembly sitting next to the add-in they point at.
        /// </summary>
        public static string FindDynamoRevitAssemblyFile(IEnumerable<string> addinsFolders) {
            if (addinsFolders == null)
                return null;

            foreach (var addinsFolder in addinsFolders) {
                if (string.IsNullOrEmpty(addinsFolder) || !Directory.Exists(addinsFolder))
                    continue;

                foreach (var manifestFile in Directory.GetFiles(addinsFolder, "*.addin")) {
                    var addinAssembly = ReadManifestAssemblyPath(manifestFile);
                    if (string.IsNullOrEmpty(addinAssembly))
                        continue;

                    var installDir = Path.GetDirectoryName(addinAssembly);
                    if (string.IsNullOrEmpty(installDir))
                        continue;

                    var dynamoAssembly = Path.Combine(installDir, AppAssemblyName + ".dll");
                    if (File.Exists(dynamoAssembly))
                        return dynamoAssembly;
                }
            }

            return null;
        }

        /// <summary>
        /// Picks the <c>ExecuteDynamoCommand</c> overload that can take the journal data and the
        /// host application, so parameter type changes between Dynamo versions do not break the call.
        /// </summary>
        public static MethodInfo ResolveExecuteDynamoCommandMethod(Type appType,
                                                                    IDictionary<string, string> journalData,
                                                                    object uiApplication) {
            return appType.GetMethods(BindingFlags.Public | BindingFlags.Instance)
                          .Where(method => method.Name == ExecuteCommandMethodName)
                          .Where(method => {
                              var parameters = method.GetParameters();
                              return parameters.Length == 2
                                     && Accepts(parameters[0].ParameterType, journalData)
                                     && Accepts(parameters[1].ParameterType, uiApplication);
                          })
                          .FirstOrDefault();
        }

        /// <summary>
        /// Reads Dynamo's command result, which is Revit's <c>Result</c> for every Dynamo version
        /// that exposes the command. Any other return value is treated as no result to judge.
        /// </summary>
        public static bool IsRejectedResult(object invokeResult) {
            if (invokeResult is bool succeeded)
                return !succeeded;

            if (invokeResult is Enum) {
                var resultName = invokeResult.ToString();
                return resultName != "Succeeded" && resultName != "Success";
            }

            return false;
        }

        /// <summary>
        /// Builds the journal data for one Dynamo call. <paramref name="includeGraph"/> leaves out
        /// everything the graph path is needed for, which is how a prepare call tells Dynamo to only
        /// bring up or replace its model.
        /// </summary>
        /// <remarks>
        /// <c>dynShowUI</c> is always present: Dynamo falls back to showing its splash screen when
        /// the key is missing, which would block the caller with a modal window.
        /// </remarks>
        public static IDictionary<string, string> BuildJournalData(DynamoExecutionOptions options, bool includeGraph) {
            var journalData = new Dictionary<string, string>() {
                { DynamoJournalKeys.ShowUI, options.ShowUI.ToString() },
                { DynamoJournalKeys.Automation, options.Automate.ToString() },
                { DynamoJournalKeys.ShutdownModel, options.ShutdownModel.ToString() },
                { DynamoJournalKeys.ReuseOpenGraph, options.ReuseOpenGraph.ToString() },
                { DynamoJournalKeys.ForceManualRun, options.ForceManualRun.ToString() }
            };

            if (includeGraph) {
                journalData[DynamoJournalKeys.ExecuteGraph] = options.ExecuteGraph.ToString();
                if (!string.IsNullOrEmpty(options.GraphPath))
                    journalData[DynamoJournalKeys.GraphPath] = options.GraphPath;
                if (!string.IsNullOrEmpty(options.NodesInfo))
                    journalData[DynamoJournalKeys.NodesInfo] = options.NodesInfo;
            }

            return journalData;
        }

        /// <summary>
        /// The ordered journal data sets a run is issued with. Showing the UI needs a single call,
        /// a headless run needs a prepare call before the one that carries the graph.
        /// </summary>
        private static IList<IDictionary<string, string>> BuildJournalDataPhases(DynamoExecutionOptions options) {
            if (options.ShowUI)
                return new List<IDictionary<string, string>> { BuildJournalData(options, includeGraph: true) };

            return new List<IDictionary<string, string>> {
                BuildJournalData(options, includeGraph: false),
                BuildJournalData(options.WithShutdownModel(false), includeGraph: true)
            };
        }

        private static bool Accepts(Type parameterType, object argument) {
            return argument != null && parameterType.IsInstanceOfType(argument);
        }

        private static string ReadManifestAssemblyPath(string manifestFile) {
            try {
                var document = new XmlDocument();
                document.Load(manifestFile);
                var assemblyNode = document.DocumentElement?.SelectSingleNode("AddIn/Assembly");
                return assemblyNode?.InnerText.Trim();
            }
            catch (Exception) {
                return null;
            }
        }

        /// <summary>
        /// The journal data as a readable line, with node values left out.
        /// </summary>
        /// <remarks>
        /// <c>dynModelNodesInfo</c> carries the caller's own values, and diagnostics end up in the
        /// debug log and in the failure dialog, so only its presence is reported.
        /// </remarks>
        private static string DescribeJournalData(IDictionary<string, string> journalData) {
            return string.Join(
                " ",
                journalData.Select(
                    entry => entry.Key == DynamoJournalKeys.NodesInfo
                        ? entry.Key + "=<" + entry.Value.Length + " chars>"
                        : entry.Key + "=" + entry.Value));
        }

        private static DynamoCommandResult Failed(DynamoCommandStatus status,
                                                  string message,
                                                  Exception exception,
                                                  StringBuilder diagnostics) {
            if (exception != null) {
                var failure = exception is TargetInvocationException && exception.InnerException != null
                    ? exception.InnerException
                    : exception;
                diagnostics.AppendLine(failure.ToString());
            }

            return new DynamoCommandResult(status, message, diagnostics.ToString());
        }
    }
}
