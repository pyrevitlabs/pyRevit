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

        /// <summary>Bring up the Dynamo UI.</summary>
        public bool ShowUI { get; set; }

        /// <summary>Run on the main thread without the idle loop.</summary>
        public bool Automate { get; set; }

        public bool ExecuteGraph { get; set; }

        public bool ShutdownModel { get; set; }

        public bool ReuseOpenGraph { get; set; }

        public bool ForceManualRun { get; set; }
    }

    public enum DynamoCommandStatus {
        Succeeded,
        DynamoUnavailable,
        IncompatibleDynamo,
        Rejected,

        /// <summary>Dynamo accepted the command but never executed the graph.</summary>
        NotRun,
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
    /// Important: the journal data must always carry the graph path. A call that omits
    /// <c>dynPath</c> makes <c>DynamoRevit.ExecuteCommand</c> throw
    /// <see cref="NullReferenceException"/>, and Dynamo answers that with its own modal error
    /// dialog, which blocks the calling API thread. A run is therefore always issued as a single
    /// call.
    ///
    /// Important: measured against Dynamo for Revit 2027, a call with <c>dynShowUI</c> off only
    /// executes the graph once a Dynamo model already exists, and reports
    /// <c>Result.Succeeded</c> whether or not it ran anything. A call with <c>dynShowUI</c> on
    /// brings the model up and runs the graph. A UIless run is therefore reported as
    /// <see cref="DynamoCommandStatus.NotRun"/> when the model is not up yet, instead of being
    /// reported as a run.
    ///
    /// Important: <c>DynamoRevit.ExecuteCommand</c> throws <see cref="NullReferenceException"/>
    /// when it is called with no Revit document open, and Dynamo answers that with its own modal
    /// error dialog, which blocks the calling API thread.
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

        /// <summary>Type holding Dynamo's per-Revit state, used to tell whether its model is up.</summary>
        public const string DynamoRevitTypeName = "Dynamo.Applications.DynamoRevit";

        /// <summary>Property on that type that is set once a Dynamo model is loaded.</summary>
        public const string DynamoModelPropertyName = "RevitDynamoModel";

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

            var journalData = BuildJournalData(options, includeGraph: true);
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

            var executeCommand = ResolveExecuteDynamoCommandMethod(appType, journalData, uiApplication);
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

            var modelStateKnown = TryGetModelUp(appType, out var modelUpBefore);
            diagnostics.AppendLine("Dynamo model up before the call: " + (modelStateKnown ? modelUpBefore.ToString() : "unknown"));

            diagnostics.AppendLine("Dynamo call: " + DescribeJournalData(journalData));
            object invokeResult;
            try {
                invokeResult = executeCommand.Invoke(app, new object[] { journalData, uiApplication });
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

            if (options.ShowUI) {
                return new DynamoCommandResult(
                    DynamoCommandStatus.Succeeded,
                    "Dynamo opened the graph in the Dynamo UI. It was executed if the graph's own "
                        + "Run setting is on Automatic - check the model for the graph's effect.",
                    diagnostics.ToString());
            }

            if (modelStateKnown) {
                if (modelUpBefore) {
                    return new DynamoCommandResult(
                        DynamoCommandStatus.Succeeded,
                        "Dynamo reported that it ran the graph. A headless run cannot be confirmed "
                            + "from Dynamo's answer alone - check the model for the graph's effect.",
                        diagnostics.ToString()
                        );
                }

                return new DynamoCommandResult(
                    DynamoCommandStatus.NotRun,
                    "Dynamo did not run the graph.\n\nDynamo for Revit only executes a graph once "
                        + "its model is up, and this run was issued before that, so nothing was "
                        + "executed even though Dynamo reported success. Run the tool in debug "
                        + "mode to open Dynamo and run the graph.",
                    diagnostics.ToString()
                    );
            }

            return new DynamoCommandResult(
                DynamoCommandStatus.Succeeded,
                "Dynamo reported that it accepted the graph, but this Dynamo version does not "
                    + "expose whether its model was already up, so whether the graph executed "
                    + "cannot be confirmed - check the model for the graph's effect.",
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
        /// Whether Dynamo's model is already up, which is what decides if a UIless call runs the
        /// graph. Read from <c>DynamoRevit.RevitDynamoModel</c> on the add-in assembly.
        /// </summary>
        /// <remarks>
        /// This is a Dynamo implementation detail, so it is read on a best-effort basis: when the
        /// type or the property is not there, or reading it fails, <paramref name="modelUp"/> is
        /// false and the caller reports the run as unconfirmed rather than as a failure.
        /// </remarks>
        /// <param name="addinType">The resolved <c>DynamoRevitApp</c> type.</param>
        /// <param name="modelUp">Whether a Dynamo model is loaded.</param>
        /// <returns>True when the state could be read.</returns>
        public static bool TryGetModelUp(Type addinType, out bool modelUp) {
            modelUp = false;
            try {
                var modelProperty = addinType.Assembly
                                          .GetType(DynamoRevitTypeName, throwOnError: false)?
                                          .GetProperty(
                                              DynamoModelPropertyName,
                                              BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic
                                              );
                if (modelProperty == null)
                    return false;

                modelUp = modelProperty.GetValue(null, null) != null;
                return true;
            }
            catch (Exception) {
                return false;
            }
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
