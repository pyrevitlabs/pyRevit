using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Runtime.Remoting;
using System.Reflection;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;

using pyRevitLabs.PyRevit;

namespace PyRevitLabs.PyRevit.Runtime {
    public static class ExecutionResultCodes {
        public static int Succeeded = 0;
        public static int SysExited = 1;
        public static int ExecutionException = 2;
        public static int CompileException = 3;
        public static int EngineNotImplementedException = 4;
        public static int ExternalInterfaceNotImplementedException = 5;
        public static int FailedLoadingContent = 6;
        public static int BadCommandArguments = 7;
        public static int NotSupportedFeatureException = 8;
        public static int UnknownException = 9;
    }

    /// Executes a script
    public class ScriptExecutor {
        /// Run the script and print the output to a new output window.
        public static int ExecuteScript(ref ScriptRuntime runtime) {
            switch (runtime.EngineType) {
                case EngineType.IronPython:
                    return ExecuteManagedScript<IronPythonEngine>(ref runtime);

                case EngineType.CPython:
                    return ExecuteManagedScript<CPythonEngine>(ref runtime);

                case EngineType.CSharp:
                    return ExecuteManagedScript<CLREngine>(ref runtime);

                case EngineType.Invoke:
                    return ExecuteManagedScript<InvokableDLLEngine>(ref runtime);

                case EngineType.VisualBasic:
                    return ExecuteManagedScript<CLREngine>(ref runtime);

                case EngineType.IronRuby:
                    return ExecuteManagedScript<RubyEngine>(ref runtime);

                case EngineType.Dynamo:
                    return ExecuteDynamoDefinition(ref runtime);

                case EngineType.Grasshopper:
                    return ExecuteGrasshopperDocument(ref runtime);

                case EngineType.Content:
                    return ExecuteContentLoader(ref runtime);
                default:
                    // should not get here
                    throw new Exception("Unknown engine type.");
            }
        }

        private static int ExecuteManagedScript<T>(ref ScriptRuntime runtime) where T: ExecutionEngine, new() {
            // 1: ----------------------------------------------------------------------------------------------------
            // get new engine manager (EngineManager manages document-specific engines)
            // and ask for an engine (EngineManager return either new engine or an already active one)
            T engine = EngineManager.GetEngine<T>(ref runtime);

            // init the engine
            engine.Start(ref runtime);
            // execute
            var result = engine.Execute(ref runtime);
            // stop and cleanup the engine
            engine.Stop(ref runtime);

            return result;
        }

        /// Run the script using DynamoBIM
        private static int ExecuteDynamoDefinition(ref ScriptRuntime runtime) {
            var journalData = new Dictionary<string, string>() {
                // Specifies the path to the Dynamo workspace to execute.
                { "dynPath", runtime.ScriptSourceFile },

                // Specifies whether the Dynamo UI should be visible (set to false - Dynamo will run headless).
                { "dynShowUI", runtime.ScriptRuntimeConfigs.DebugMode.ToString() },

                // If the journal file specifies automation mode
                // Dynamo will run on the main thread without the idle loop.
                { "dynAutomation",  "True" },

                // The journal file can specify if the Dynamo workspace opened
                //{ "dynForceManualRun",  "True" }

                // The journal file can specify if the Dynamo workspace opened from DynPathKey will be executed or not. 
                // If we are in automation mode the workspace will be executed regardless of this key.
                { "dynPathExecute",  "True" },

                // The journal file can specify if the existing UIless RevitDynamoModel
                // needs to be shutdown before performing any action.
                // per comments on https://github.com/eirannejad/pyRevit/issues/570
                // Setting this to True slows down Dynamo by a factor of 3
                { "dynModelShutDown",  "True" },

                // The journal file can specify the values of Dynamo nodes.
                //{ "dynModelNodesInfo",  "" }
                };

            //return new DynamoRevit().ExecuteCommand(new DynamoRevitCommandData() {
            //    JournalData = journalData,
            //    Application = commandData.Application
            //});

            try {
                // find the DynamoRevitApp from DynamoRevitDS.dll
                // this should be already loaded since Dynamo loads before pyRevit
                ObjectHandle dynRevitAppObjHandle =
                    Activator.CreateInstance("DynamoRevitDS", "Dynamo.Applications.DynamoRevitApp");
                object dynRevitApp = dynRevitAppObjHandle.Unwrap();
                MethodInfo execDynamo = dynRevitApp.GetType().GetMethod("ExecuteDynamoCommand");

                // run the script
                execDynamo.Invoke(dynRevitApp, new object[] { journalData, runtime.UIApp });
                return ExecutionResultCodes.Succeeded;
            }
            catch (FileNotFoundException) {
                // if failed in finding DynamoRevitDS.dll, assume no dynamo
                TaskDialog.Show(PyRevitConsts.ProductName,
                    "Can not find dynamo installation or determine which Dynamo version to Run.\n\n" +
                    "Run Dynamo once to select the active version.");
                return ExecutionResultCodes.ExecutionException;
            }
        }

        /// Run the script using Grasshopper
        private static int ExecuteGrasshopperDocument(ref ScriptRuntime runtime) {
            // TODO: ExecuteGrasshopperDocument
            TaskDialog.Show(PyRevitConsts.ProductName, "Grasshopper Execution Engine Not Yet Implemented.");
            return ExecutionResultCodes.EngineNotImplementedException;
        }

        /// Run the content bundle and place in active document
        private static int ExecuteContentLoader(ref ScriptRuntime runtime) {
#if (REVIT2013 || REVIT2014)
            TaskDialog.Show(PyRevitConsts.ProductName, NotSupportedFeatureException.NotSupportedMessage);
            return ExecutionResultCodes.NotSupportedFeatureException;
#else
            if (runtime.UIApp != null && runtime.UIApp.ActiveUIDocument != null) {
                string familySourceFile = runtime.ScriptSourceFile;
                UIDocument uidoc = runtime.UIApp.ActiveUIDocument;
                Document doc = uidoc.Document;

                // find or load family first
                Family contentFamily = null;

                // attempt to find previously loaded family
                Element existingFamily = null;
                string familyName = Path.GetFileNameWithoutExtension(familySourceFile);
                var currentFamilies = 
                    new FilteredElementCollector(doc).OfClass(typeof(Family)).Where(q => q.Name == familyName);
                if (currentFamilies.Count() > 0)
                    existingFamily = currentFamilies.First();

                if (existingFamily != null)
                    contentFamily = (Family)existingFamily;

                // if not found, attemt to load
                if (contentFamily == null) {
                    try {
                        var txn = new Transaction(doc, "Load pyRevit Content");
                        txn.Start();
                        doc.LoadFamily(
                            familySourceFile,
                            new ContentLoaderOptions(),
                            out contentFamily
                            );
                        txn.Commit();
                    }
                    catch (Exception loadEx) {
                        TaskDialog.Show(PyRevitConsts.ProductName,
                            string.Format("Failed loading content.\n{0}\n{1}", loadEx.Message, loadEx.StackTrace));
                        return ExecutionResultCodes.FailedLoadingContent;
                    }
                }

                if (contentFamily == null) {
                    TaskDialog.Show(PyRevitConsts.ProductName,
                        string.Format("Failed finding or loading bundle content at:\n{0}", familySourceFile));
                    return ExecutionResultCodes.FailedLoadingContent;
                }

                // now ask ui to place an instance
                ElementId firstSymbolId = contentFamily.GetFamilySymbolIds().First();
                if (firstSymbolId != null && firstSymbolId != ElementId.InvalidElementId) {
                    FamilySymbol firstSymbol = (FamilySymbol)doc.GetElement(firstSymbolId);
                    if (firstSymbol != null)
                        try {
                            var placeOps = new PromptForFamilyInstancePlacementOptions();
                            uidoc.PromptForFamilyInstancePlacement(firstSymbol, placeOps);
                            return ExecutionResultCodes.Succeeded;
                        }
                        catch (Autodesk.Revit.Exceptions.OperationCanceledException) {
                            // user cancelled placement
                            return ExecutionResultCodes.Succeeded;
                        }
                        catch (Exception promptEx) {
                            TaskDialog.Show(PyRevitConsts.ProductName,
                                string.Format("Failed placing content.\n{0}\n{1}",
                                              promptEx.Message, promptEx.StackTrace));
                            return ExecutionResultCodes.FailedLoadingContent;
                        }
                }
            }

            TaskDialog.Show(PyRevitConsts.ProductName, "Failed accessing Appication.");
            return ExecutionResultCodes.FailedLoadingContent;
#endif
        }
    }
}
