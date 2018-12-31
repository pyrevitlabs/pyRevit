using System;
using System.Diagnostics;
using System.Windows;
using System.Windows.Forms;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Collections;
using System.Collections.Generic;

using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB.Events;
using Autodesk.Revit.UI.Events;
using System.IO;

namespace PyRevitBaseClasses
{
    public class UIDocUtils {
        private bool _txnCompleted = false;
        private Document _doc = null;
        private string _txnName = null;
        private BuiltInParameter _paramToUpdate;
        private string _paramToUpdateStringValue = null;

        public UIApplication App { get; private set; }
        public List<ElementId> NewElements { get; private set; }

        public UIDocUtils(UIApplication app) {
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
            if (e.Cancellable)
                e.Cancel = true;
            else
                e.OverrideResult(1);
        }

        private void NewElementPropertyValueUpdater(object sender, IdlingEventArgs e) {
            // cancel if txn is completed
            if(_txnCompleted) {
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
            } catch (Exception ex) {
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
}
