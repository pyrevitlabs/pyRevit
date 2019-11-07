using System;
using System.IO;
using System.Linq;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;

using pyRevitLabs.Common;

namespace PyRevitLabs.PyRevit.Runtime {
    public class ContentEngine : ScriptEngine {
        public override void Init(ref ScriptRuntime runtime) {
            base.Init(ref runtime);
            // this is not a cachable engine; always use new engines
            UseNewEngine = true;
        }

        public override int Execute(ref ScriptRuntime runtime) {
#if (REVIT2013 || REVIT2014)
            TaskDialog.Show(PyRevitLabsConsts.ProductName, NotSupportedFeatureException.NotSupportedMessage);
            return ScriptExecutorResultCodes.NotSupportedFeatureException;
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
                        var dialog = new TaskDialog(PyRevitLabsConsts.ProductName);
                        dialog.MainInstruction = "Failed loading content.";
                        dialog.ExpandedContent = string.Format("{0}\n{1}", loadEx.Message, loadEx.StackTrace);
                        dialog.Show();
                        return ScriptExecutorResultCodes.FailedLoadingContent;
                    }
                }

                if (contentFamily == null) {
                    TaskDialog.Show(PyRevitLabsConsts.ProductName,
                        string.Format("Failed finding or loading bundle content at:\n{0}", familySourceFile));
                    return ScriptExecutorResultCodes.FailedLoadingContent;
                }

                // now ask ui to place an instance
                ElementId firstSymbolId = contentFamily.GetFamilySymbolIds().First();
                if (firstSymbolId != null && firstSymbolId != ElementId.InvalidElementId) {
                    FamilySymbol firstSymbol = (FamilySymbol)doc.GetElement(firstSymbolId);
                    if (firstSymbol != null)
                        try {
                            var placeOps = new PromptForFamilyInstancePlacementOptions();
                            uidoc.PromptForFamilyInstancePlacement(firstSymbol, placeOps);
                            return ScriptExecutorResultCodes.Succeeded;
                        }
                        catch (Autodesk.Revit.Exceptions.OperationCanceledException) {
                            // user cancelled placement
                            return ScriptExecutorResultCodes.Succeeded;
                        }
                        catch (Exception promptEx) {
                            var dialog = new TaskDialog(PyRevitLabsConsts.ProductName);
                            dialog.MainInstruction = "Failed placing content.";
                            dialog.ExpandedContent = string.Format("{0}\n{1}", promptEx.Message, promptEx.StackTrace);
                            dialog.Show();
                            return ScriptExecutorResultCodes.FailedLoadingContent;
                        }
                }
            }

            TaskDialog.Show(PyRevitLabsConsts.ProductName, "Failed accessing Application.");
            return ScriptExecutorResultCodes.FailedLoadingContent;
#endif
        }
    }

    public class ContentLoaderOptions : IFamilyLoadOptions {
        public bool OnFamilyFound(bool familyInUse, out bool overwriteParameterValues) {
            overwriteParameterValues = true;
            return overwriteParameterValues;
        }

        public bool OnSharedFamilyFound(Family sharedFamily, bool familyInUse, out FamilySource source, out bool overwriteParameterValues) {
            throw new NotImplementedException();
        }
    }
}
