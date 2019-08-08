using System;
using System.Collections.Generic;
using System.Net;
using System.Web.Script.Serialization;
using System.IO;
using System.Threading.Tasks;

using Autodesk.Revit.ApplicationServices;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Events;
using Autodesk.Revit.UI;
using Autodesk.Revit.UI.Events;

using pyRevitLabs.Common;

namespace PyRevitBaseClasses {
    public enum EventType {
        // Autodesk.Revit.ApplicationServices.Application Events
        Application_ApplicationInitialized,
        Application_DocumentChanged,
        Application_DocumentClosed,
        Application_DocumentClosing,
        Application_DocumentCreated,
        Application_DocumentCreating,
        Application_DocumentOpened,
        Application_DocumentOpening,
        Application_DocumentPrinted,
        Application_DocumentPrinting,
        Application_DocumentSaved,
        Application_DocumentSaving,
        Application_DocumentSavedAs,
        Application_DocumentSavingAs,
        Application_DocumentSynchronizedWithCentral,
        Application_DocumentSynchronizingWithCentral,
        Application_DocumentWorksharingEnabled,
        Application_ElementTypeDuplicated,
        Application_ElementTypeDuplicating,
        Application_FailuresProcessing,
        Application_FamilyLoadedIntoDocument,
        Application_FamilyLoadingIntoDocument,
        Application_FileExported,
        Application_FileExporting,
        Application_FileImported,
        Application_FileImporting,
        Application_LinkedResourceOpened,
        Application_LinkedResourceOpening,
        Application_ProgressChanged,
        Application_ViewExported,
        Application_ViewExporting,
        Application_ViewPrinted,
        Application_ViewPrinting,
        Application_WorksharedOperationProgressChanged,

        // Autodesk.Revit.UI.UIApplication Events
        UIApplication_ApplicationClosing,
        UIApplication_DialogBoxShowing,
        UIApplication_DisplayingOptionsDialog,
        UIApplication_DockableFrameFocusChanged,
        UIApplication_DockableFrameVisibilityChanged,
        UIApplication_FabricationPartBrowserChanged,
        UIApplication_FormulaEditing,
        UIApplication_Idling,
        UIApplication_TransferredProjectStandards,
        UIApplication_TransferringProjectStandards,
        UIApplication_ViewActivated,
        UIApplication_ViewActivating,

        // Autodesk.Revit.ApplicationServices.ControlledApplication Events
        //ControlledApplication_ApplicationInitialized,
        //ControlledApplication_DocumentChanged,
        //ControlledApplication_DocumentClosed,
        //ControlledApplication_DocumentClosing,
        //ControlledApplication_DocumentCreated,
        //ControlledApplication_DocumentCreating,
        //ControlledApplication_DocumentOpened,
        //ControlledApplication_DocumentOpening,
        //ControlledApplication_DocumentPrinted,
        //ControlledApplication_DocumentPrinting,
        //ControlledApplication_DocumentSaved,
        //ControlledApplication_DocumentSaving,
        //ControlledApplication_DocumentSavedAs,
        //ControlledApplication_DocumentSavingAs,
        //ControlledApplication_DocumentSynchronizedWithCentral,
        //ControlledApplication_DocumentSynchronizingWithCentral,
        //ControlledApplication_DocumentWorksharingEnabled,
        //ControlledApplication_ElementTypeDuplicated,
        //ControlledApplication_ElementTypeDuplicating,
        //ControlledApplication_FailuresProcessing,
        //ControlledApplication_FamilyLoadedIntoDocument,
        //ControlledApplication_FamilyLoadingIntoDocument,
        //ControlledApplication_FileExported,
        //ControlledApplication_FileExporting,
        //ControlledApplication_FileImported,
        //ControlledApplication_FileImporting,
        //ControlledApplication_LinkedResourceOpened,
        //ControlledApplication_LinkedResourceOpening,
        //ControlledApplication_ProgressChanged,
        //ControlledApplication_ViewExported,
        //ControlledApplication_ViewExporting,
        //ControlledApplication_ViewPrinted,
        //ControlledApplication_ViewPrinting,
        //ControlledApplication_WorksharedOperationProgressChanged,

        // Autodesk.Revit.UI.UIControlledApplication Events
        //UIControlledApplication_ApplicationClosing,
        //UIControlledApplication_DialogBoxShowing,
        //UIControlledApplication_DisplayingOptionsDialog,
        //UIControlledApplication_DockableFrameFocusChanged,
        //UIControlledApplication_DockableFrameVisibilityChanged,
        //UIControlledApplication_FabricationPartBrowserChanged,
        //UIControlledApplication_FormulaEditing,
        //UIControlledApplication_Idling,
        //UIControlledApplication_TransferredProjectStandards,
        //UIControlledApplication_TransferringProjectStandards,
        //UIControlledApplication_ViewActivated,
        //UIControlledApplication_ViewActivating,

        // Autodesk.Revit.UI.Macros.ApplicationEntryPoint Events
        //ApplicationEntryPoint_ApplicationClosing,
        //ApplicationEntryPoint_DialogBoxShowing,
        //ApplicationEntryPoint_DisplayingOptionsDialog,
        //ApplicationEntryPoint_DockableFrameFocusChanged,
        //ApplicationEntryPoint_DockableFrameVisibilityChanged,
        //ApplicationEntryPoint_FabricationPartBrowserChanged,
        //ApplicationEntryPoint_FormulaEditing,
        //ApplicationEntryPoint_Idling,
        //ApplicationEntryPoint_TransferredProjectStandards,
        //ApplicationEntryPoint_TransferringProjectStandards,
        //ApplicationEntryPoint_ViewActivated,
        //ApplicationEntryPoint_ViewActivating,
    }

    public class UIEventUtils {
        private bool _txnCompleted = false;
        private Document _doc = null;
        private string _txnName = null;
        private BuiltInParameter _paramToUpdate;
        private string _paramToUpdateStringValue = null;

        public UIApplication App { get; private set; }
        public List<ElementId> NewElements { get; private set; }

        public UIEventUtils(UIApplication app) {
            if (app != null) {
                App = app;
                NewElements = new List<ElementId>();
            }
            else
                throw new Exception("Application can not be null.");
        }

        private void OnDocumentChanged(object sender, DocumentChangedEventArgs e) {
            NewElements.AddRange(e.GetAddedElementIds());
        }

        private void CancelAllDialogs(object sender, DialogBoxShowingEventArgs e) {
            if (e.Cancellable) {
#if (REVIT2013 || REVIT2014)
                e.Cancel = true;
#else
                e.Cancel();
#endif
            }
            else
                e.OverrideResult(1);
        }

        private void NewElementPropertyValueUpdater(object sender, IdlingEventArgs e) {
            // cancel if txn is completed
            if (_txnCompleted) {
                App.Idling -= new EventHandler<IdlingEventArgs>(NewElementPropertyValueUpdater);
                EndCancellingAllDialogs();
                EndTrackingElements();
            }

            // now update element parameters
            try {
                var TXN = new Transaction(_doc, _txnName);
                TXN.Start();
                foreach (var newElId in NewElements) {
                    var element = _doc.GetElement(newElId);
                    if (element != null) {
                        var parameter = element.get_Parameter(_paramToUpdate);
                        if (parameter != null && !parameter.IsReadOnly)
                            parameter.Set(_paramToUpdateStringValue);
                    }
                }
                TXN.Commit();
            }
            catch {
            }

            _txnCompleted = true;
        }

        public void StartTrackingElements() {
            App.Application.DocumentChanged += new EventHandler<DocumentChangedEventArgs>(OnDocumentChanged);
        }

        public void EndTrackingElements() {
            App.Application.DocumentChanged -= new EventHandler<DocumentChangedEventArgs>(OnDocumentChanged);
        }

        public void StartCancellingAllDialogs() {
            App.DialogBoxShowing += new EventHandler<DialogBoxShowingEventArgs>(CancelAllDialogs);
        }

        public void EndCancellingAllDialogs() {
            App.DialogBoxShowing -= new EventHandler<DialogBoxShowingEventArgs>(CancelAllDialogs);
        }

        public void PostElementPropertyUpdateRequest(Document doc,
                                                     string txnName,
                                                     BuiltInParameter bip,
                                                     string value) {
            _doc = doc;
            _txnName = txnName;
            _paramToUpdate = bip;
            _paramToUpdateStringValue = value;
            App.Idling += new EventHandler<IdlingEventArgs>(NewElementPropertyValueUpdater);
        }

        public void PostCommandAndUpdateNewElementProperties(Document doc,
                                                             PostableCommand postableCommand, string transactionName,
                                                             BuiltInParameter bip, string value) {
            StartTrackingElements();
            StartCancellingAllDialogs();
            var postableCommandId = RevitCommandId.LookupPostableCommandId(postableCommand);
            App.PostCommand(postableCommandId);
            PostElementPropertyUpdateRequest(doc, transactionName, bip, value);
        }
    }


    public class PlaceKeynoteExternalEventHandler : IExternalEventHandler {
        public string KeynoteKey = null;
        public PostableCommand KeynoteType = PostableCommand.UserKeynote;

        public PlaceKeynoteExternalEventHandler() { }

        public void Execute(UIApplication app) {
            var docutils = new UIEventUtils(app);
            docutils.PostCommandAndUpdateNewElementProperties(
                app.ActiveUIDocument.Document,
                KeynoteType,
                "Update",
                BuiltInParameter.KEY_VALUE,
                KeynoteKey
                );
        }

        public string GetName() {
            return "PlaceKeynoteExternalEvent";
        }
    }
}
