using System;
using System.Numerics;
using System.Collections.Generic;
using System.Linq;
using System.Net;
using System.Web.Script.Serialization;
using System.IO;
using System.Threading.Tasks;
using Autodesk.Revit.ApplicationServices;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Events;
using Autodesk.Revit.UI;

using pyRevitLabs.Common;

namespace PyRevitBaseClasses {
    public class EngineInfo {
        public string type { get; set; }
        public string version { get; set; }
        public List<string> syspath { get; set; }
    }

    public class TraceInfo {
        public EngineInfo engine { get; set; }
        public string message { get; set; }
    }

    public class ScriptTelemetryRecord {
        // schema
        public Dictionary<string, string> meta { get; private set; }

        // when?
        public string timestamp { get; set; }
        // by who?
        public string username { get; set; }
        // on what?
        public string revit { get; set; }
        public string revitbuild { get; set; }
        public string sessionid { get; set; }
        public string pyrevit { get; set; }
        public string clone { get; set; }
        // on which document
        public string docname { get; set; }
        public string docpath { get; set; }
        // which mode?
        public bool debug { get; set; }
        public bool config { get; set; }
        public bool from_gui { get; set; }
        public bool clean_engine { get; set; }
        public bool fullframe_engine { get; set; }
        // which script?
        public string commandname { get; set; }
        public string commandbundle { get; set; }
        public string commandextension { get; set; }
        public string commanduniquename { get; set; }
        public string scriptpath { get; set; }
        public string arguments { get; set; }
        // returned what?
        public int resultcode { get; set; }
        public Dictionary<string, string> commandresults { get; set; }
        // any errors?
        public TraceInfo trace { get; set; }

        public ScriptTelemetryRecord() {
            meta = new Dictionary<string, string> {
                { "schema", "2.0"},
            };

            timestamp = CommonUtils.GetISOTimeStampNow();
        }
    }

    public static class Telemetry {
        public static string SerializeTelemetryRecord(object telemetryRecord) {
            return new JavaScriptSerializer().Serialize(telemetryRecord);
        }

        public static string PostTelemetryRecord(string telemetryServerUrl, object telemetryRecord) {
            var httpWebRequest = (HttpWebRequest)WebRequest.Create(telemetryServerUrl);
            httpWebRequest.ContentType = "application/json";
            httpWebRequest.Method = "POST";
            httpWebRequest.UserAgent = "pyrevit";

            using (var streamWriter = new StreamWriter(httpWebRequest.GetRequestStream())) {
                // serialize and write
                string json = SerializeTelemetryRecord(telemetryRecord);
                streamWriter.Write(json);
                streamWriter.Flush();
                streamWriter.Close();
            }

            var httpResponse = (HttpWebResponse)httpWebRequest.GetResponse();
            using (var streamReader = new StreamReader(httpResponse.GetResponseStream())) {
                return streamReader.ReadToEnd();
            }
        }

        public static void WriteTelemetryRecord<T>(string telemetryFilePath, T telemetryRecord) {
            string existingTelemetryData = "[]";
            if (File.Exists(telemetryFilePath)) {
                existingTelemetryData = File.ReadAllText(telemetryFilePath);
            }
            else {
                File.WriteAllText(telemetryFilePath, existingTelemetryData);
            }

            var telemetryData = new JavaScriptSerializer().Deserialize<List<T>>(existingTelemetryData);

            telemetryData.Add(telemetryRecord);

            existingTelemetryData = new JavaScriptSerializer().Serialize(telemetryData);
            File.WriteAllText(telemetryFilePath, existingTelemetryData);
        }
    }

    public static class ScriptTelemetry {
        public static void LogScriptTelemetryRecord(ScriptTelemetryRecord scriptTelemetryRecord) {
            var envDict = new EnvDictionary();

            if (envDict.TelemetryState) {
                if (envDict.TelemetryState
                        && envDict.TelemetryServerUrl != null
                        && !string.IsNullOrEmpty(envDict.TelemetryServerUrl))
                    new Task(() =>
                        Telemetry.PostTelemetryRecord(envDict.TelemetryServerUrl, scriptTelemetryRecord)).Start();

                if (envDict.TelemetryState
                        && envDict.TelemetryFilePath != null
                        && !string.IsNullOrEmpty(envDict.TelemetryFilePath))
                    new Task(() =>
                        Telemetry.WriteTelemetryRecord(envDict.TelemetryFilePath, scriptTelemetryRecord)).Start();
            }
        }
    }

    public class EventTelemetryRecord {
        // schema
        public Dictionary<string, string> meta { get; private set; }

        // which event?
        public string type { get; set; }
        public Dictionary<string, object> args { get; set; }
        public string status { get; set; }

        // when?
        public string timestamp { get; set; }
        // by who?
        public string username { get; set; }

        public bool cancellable { get; set; }
        public bool cancelled { get; set; }
        public int docid { get; set; }
        public string doctype { get; set; }
        public string doctemplate { get; set; }
        public string docname { get; set; }
        public string docpath { get; set; }


        public EventTelemetryRecord() {
            meta = new Dictionary<string, string> {
                { "schema", "2.0"},
            };

            timestamp = CommonUtils.GetISOTimeStampNow();
        }
    }

    public class EventTelemetry {
        private static void ToggleEventListeners(UIApplication uiApp, EventType eventType, bool toggle_on = true) {
            switch (eventType) {
                case EventType.Application_ApplicationInitialized:
                    if (toggle_on)
                        uiApp.Application.ApplicationInitialized += Application_ApplicationInitialized;
                    else
                        uiApp.Application.ApplicationInitialized -= Application_ApplicationInitialized;
                    break;

                case EventType.Application_DocumentChanged:
                    if (toggle_on)
                        uiApp.Application.DocumentChanged += Application_DocumentChanged;
                    else
                        uiApp.Application.DocumentChanged -= Application_DocumentChanged;
                    break;

                case EventType.Application_DocumentClosed:
                    if (toggle_on)
                        uiApp.Application.DocumentClosed += Application_DocumentClosed;
                    else
                        uiApp.Application.DocumentClosed -= Application_DocumentClosed;
                    break;

                case EventType.Application_DocumentClosing:
                    if (toggle_on)
                        uiApp.Application.DocumentClosing += Application_DocumentClosing;
                    else
                        uiApp.Application.DocumentClosing -= Application_DocumentClosing;
                    break;

                case EventType.Application_DocumentCreated:
                    if (toggle_on)
                        uiApp.Application.DocumentCreated += Application_DocumentCreated;
                    else
                        uiApp.Application.DocumentCreated -= Application_DocumentCreated;
                    break;

                case EventType.Application_DocumentCreating:
                    if (toggle_on)
                        uiApp.Application.DocumentCreating += Application_DocumentCreating;
                    else
                        uiApp.Application.DocumentCreating -= Application_DocumentCreating;
                    break;

                case EventType.Application_DocumentOpened:
                    if (toggle_on)
                        uiApp.Application.DocumentOpened += Application_DocumentOpened;
                    else
                        uiApp.Application.DocumentOpened -= Application_DocumentOpened;
                    break;

                case EventType.Application_DocumentOpening:
                    if (toggle_on)
                        uiApp.Application.DocumentOpening += Application_DocumentOpening;
                    else
                        uiApp.Application.DocumentOpening -= Application_DocumentOpening;
                    break;

                case EventType.Application_DocumentPrinted:
                    if (toggle_on)
                        uiApp.Application.DocumentPrinted += Application_DocumentPrinted;
                    else
                        uiApp.Application.DocumentPrinted -= Application_DocumentPrinted;
                    break;

                case EventType.Application_DocumentPrinting:
                    if (toggle_on)
                        uiApp.Application.DocumentPrinting += Application_DocumentPrinting;
                    else
                        uiApp.Application.DocumentPrinting -= Application_DocumentPrinting;
                    break;

                case EventType.Application_DocumentSaved:
                    if (toggle_on)
                        uiApp.Application.DocumentSaved += Application_DocumentSaved;
                    else
                        uiApp.Application.DocumentSaved -= Application_DocumentSaved;
                    break;

                case EventType.Application_DocumentSaving:
                    if (toggle_on)
                        uiApp.Application.DocumentSaving += Application_DocumentSaving;
                    else
                        uiApp.Application.DocumentSaving -= Application_DocumentSaving;
                    break;

                case EventType.Application_DocumentSavedAs:
                    if (toggle_on)
                        uiApp.Application.DocumentSavedAs += Application_DocumentSavedAs;
                    else
                        uiApp.Application.DocumentSavedAs -= Application_DocumentSavedAs;
                    break;

                case EventType.Application_DocumentSavingAs:
                    if (toggle_on)
                        uiApp.Application.DocumentSavingAs += Application_DocumentSavingAs;
                    else
                        uiApp.Application.DocumentSavingAs -= Application_DocumentSavingAs;
                    break;

                case EventType.Application_DocumentSynchronizedWithCentral:
                    if (toggle_on)
                        uiApp.Application.DocumentSynchronizedWithCentral += Application_DocumentSynchronizedWithCentral;
                    else
                        uiApp.Application.DocumentSynchronizedWithCentral -= Application_DocumentSynchronizedWithCentral;
                    break;

                case EventType.Application_DocumentSynchronizingWithCentral:
                    if (toggle_on)
                        uiApp.Application.DocumentSynchronizingWithCentral += Application_DocumentSynchronizingWithCentral;
                    else
                        uiApp.Application.DocumentSynchronizingWithCentral -= Application_DocumentSynchronizingWithCentral;
                    break;

                case EventType.Application_DocumentWorksharingEnabled:
                    if (toggle_on)
                        uiApp.Application.DocumentWorksharingEnabled += Application_DocumentWorksharingEnabled;
                    else
                        uiApp.Application.DocumentWorksharingEnabled -= Application_DocumentWorksharingEnabled;
                    break;

                case EventType.Application_ElementTypeDuplicated:
                    if (toggle_on)
                        uiApp.Application.ElementTypeDuplicated += Application_ElementTypeDuplicated;
                    else
                        uiApp.Application.ElementTypeDuplicated -= Application_ElementTypeDuplicated;
                    break;

                case EventType.Application_ElementTypeDuplicating:
                    if (toggle_on)
                        uiApp.Application.ElementTypeDuplicating += Application_ElementTypeDuplicating;
                    else
                        uiApp.Application.ElementTypeDuplicating -= Application_ElementTypeDuplicating;
                    break;

                case EventType.Application_FailuresProcessing:
                    if (toggle_on)
                        uiApp.Application.FailuresProcessing += Application_FailuresProcessing;
                    else
                        uiApp.Application.FailuresProcessing -= Application_FailuresProcessing;
                    break;

                case EventType.Application_FamilyLoadedIntoDocument:
                    if (toggle_on)
                        uiApp.Application.FamilyLoadedIntoDocument += Application_FamilyLoadedIntoDocument;
                    else
                        uiApp.Application.FamilyLoadedIntoDocument -= Application_FamilyLoadedIntoDocument;
                    break;

                case EventType.Application_FamilyLoadingIntoDocument:
                    if (toggle_on)
                        uiApp.Application.FamilyLoadingIntoDocument += Application_FamilyLoadingIntoDocument;
                    else
                        uiApp.Application.FamilyLoadingIntoDocument -= Application_FamilyLoadingIntoDocument;
                    break;

                case EventType.Application_FileExported:
                    if (toggle_on)
                        uiApp.Application.FileExported += Application_FileExported;
                    else
                        uiApp.Application.FileExported -= Application_FileExported;
                    break;

                case EventType.Application_FileExporting:
                    if (toggle_on)
                        uiApp.Application.FileExporting += Application_FileExporting;
                    else
                        uiApp.Application.FileExporting -= Application_FileExporting;
                    break;

                case EventType.Application_FileImported:
                    if (toggle_on)
                        uiApp.Application.FileImported += Application_FileImported;
                    else
                        uiApp.Application.FileImported -= Application_FileImported;
                    break;

                case EventType.Application_FileImporting:
                    if (toggle_on)
                        uiApp.Application.FileImporting += Application_FileImporting;
                    else
                        uiApp.Application.FileImporting -= Application_FileImporting;
                    break;

                case EventType.Application_LinkedResourceOpened:
                    if (toggle_on)
                        uiApp.Application.LinkedResourceOpened += Application_LinkedResourceOpened;
                    else
                        uiApp.Application.LinkedResourceOpened -= Application_LinkedResourceOpened;
                    break;

                case EventType.Application_LinkedResourceOpening:
                    if (toggle_on)
                        uiApp.Application.LinkedResourceOpening += Application_LinkedResourceOpening;
                    else
                        uiApp.Application.LinkedResourceOpening -= Application_LinkedResourceOpening;
                    break;

                case EventType.Application_ProgressChanged:
                    if (toggle_on)
                        uiApp.Application.ProgressChanged += Application_ProgressChanged;
                    else
                        uiApp.Application.ProgressChanged -= Application_ProgressChanged;
                    break;

                case EventType.Application_ViewExported:
                    if (toggle_on)
                        uiApp.Application.ViewExported += Application_ViewExported;
                    else
                        uiApp.Application.ViewExported -= Application_ViewExported;
                    break;

                case EventType.Application_ViewExporting:
                    if (toggle_on)
                        uiApp.Application.ViewExporting += Application_ViewExporting;
                    else
                        uiApp.Application.ViewExporting -= Application_ViewExporting;
                    break;

                case EventType.Application_ViewPrinted:
                    if (toggle_on)
                        uiApp.Application.ViewPrinted += Application_ViewPrinted;
                    else
                        uiApp.Application.ViewPrinted -= Application_ViewPrinted;
                    break;

                case EventType.Application_ViewPrinting:
                    if (toggle_on)
                        uiApp.Application.ViewPrinting += Application_ViewPrinting;
                    else
                        uiApp.Application.ViewPrinting -= Application_ViewPrinting;
                    break;

                case EventType.Application_WorksharedOperationProgressChanged:
                    if (toggle_on)
                        uiApp.Application.WorksharedOperationProgressChanged += Application_WorksharedOperationProgressChanged;
                    else
                        uiApp.Application.WorksharedOperationProgressChanged -= Application_WorksharedOperationProgressChanged;
                    break;

                case EventType.UIApplication_ApplicationClosing:
                    if (toggle_on)
                        uiApp.ApplicationClosing += UiApp_ApplicationClosing;
                    else
                        uiApp.ApplicationClosing -= UiApp_ApplicationClosing;
                    break;

                case EventType.UIApplication_DialogBoxShowing:
#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016)
                    if (toggle_on)
                        uiApp.DialogBoxShowing += UiApp_DialogBoxShowing;
                    else
                        uiApp.DialogBoxShowing -= UiApp_DialogBoxShowing;
                    break;
#else
                                        throw new Exception("Event not supported under this Revit version.");
                                        break;
#endif
                case EventType.UIApplication_DisplayingOptionsDialog:
                    if (toggle_on)
                        uiApp.DisplayingOptionsDialog += UiApp_DisplayingOptionsDialog;
                    else
                        uiApp.DisplayingOptionsDialog -= UiApp_DisplayingOptionsDialog;
                    break;

                case EventType.UIApplication_DockableFrameFocusChanged:
                    if (toggle_on)
                        uiApp.DockableFrameFocusChanged += UiApp_DockableFrameFocusChanged;
                    else
                        uiApp.DockableFrameFocusChanged -= UiApp_DockableFrameFocusChanged;
                    break;

                case EventType.UIApplication_DockableFrameVisibilityChanged:
                    if (toggle_on)
                        uiApp.DockableFrameVisibilityChanged += UiApp_DockableFrameVisibilityChanged;
                    else
                        uiApp.DockableFrameVisibilityChanged -= UiApp_DockableFrameVisibilityChanged;
                    break;

                case EventType.UIApplication_FabricationPartBrowserChanged:
#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016)
                    if (toggle_on)
                        uiApp.FabricationPartBrowserChanged += UiApp_FabricationPartBrowserChanged;
                    else
                        uiApp.FabricationPartBrowserChanged -= UiApp_FabricationPartBrowserChanged;
                    break;
#else
                                        throw new Exception("Event not supported under this Revit version.");
                                        break;
#endif

                case EventType.UIApplication_FormulaEditing:
#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017 || REVIT2018)
                    if (toggle_on)
                        uiApp.FormulaEditing += UiApp_FormulaEditing;
                    else
                        uiApp.FormulaEditing -= UiApp_FormulaEditing;
                    break;
#else
                                        throw new Exception("Event not supported under this Revit version.");
                                        break;
#endif

                case EventType.UIApplication_Idling:
                    if (toggle_on)
                        uiApp.Idling += UiApp_Idling;
                    else
                        uiApp.Idling -= UiApp_Idling;
                    break;


                case EventType.UIApplication_TransferredProjectStandards:
#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017)
                    if (toggle_on)
                        uiApp.TransferredProjectStandards += UiApp_TransferredProjectStandards;
                    else
                        uiApp.TransferredProjectStandards -= UiApp_TransferredProjectStandards;
                    break;
#else
                                        throw new Exception("Event not supported under this Revit version.");
                                        break;
#endif

                case EventType.UIApplication_TransferringProjectStandards:
#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017)
                    if (toggle_on)
                        uiApp.TransferringProjectStandards += UiApp_TransferringProjectStandards;
                    else
                        uiApp.TransferringProjectStandards -= UiApp_TransferringProjectStandards;
                    break;
#else
                                        throw new Exception("Event not supported under this Revit version.");
                                        break;
#endif

                case EventType.UIApplication_ViewActivated:
                    if (toggle_on)
                        uiApp.ViewActivated += UiApp_ViewActivated;
                    else
                        uiApp.ViewActivated -= UiApp_ViewActivated;
                    break;

                case EventType.UIApplication_ViewActivating:
                    if (toggle_on)
                        uiApp.ViewActivating += UiApp_ViewActivating;
                    else
                        uiApp.ViewActivating -= UiApp_ViewActivating;
                    break;
            }
        }

        public static void LogEventTelemetryRecord(EventTelemetryRecord eventTelemetryRecord, object sender, object args) {
            var envDict = new EnvDictionary();

            // update general properties on record
            eventTelemetryRecord.username = TryGetActiveUserName(sender);
            eventTelemetryRecord.cancellable = ((RevitAPIEventArgs)args).Cancellable;
            eventTelemetryRecord.cancelled = ((RevitAPIEventArgs)args).IsCancelled();

            if (envDict.TelemetryState) {
                if (envDict.AppTelemetryState
                        && envDict.AppTelemetryServerUrl != null
                        && !string.IsNullOrEmpty(envDict.AppTelemetryServerUrl))
                    new Task(() =>
                        Telemetry.PostTelemetryRecord(envDict.AppTelemetryServerUrl, eventTelemetryRecord)).Start();
            }
        }

        public static string TryGetActiveUserName(object sender) {
            UIControlledApplication uictrlapp = null;
            UIApplication uiapp = null;
            ControlledApplication ctrlapp = null;
            Application app = null;

            Type senderType = sender.GetType();
            if (senderType == typeof(UIControlledApplication))
                uictrlapp = (UIControlledApplication)sender;
            else if (senderType == typeof(UIApplication))
                uiapp = (UIApplication)sender;
            else if (senderType == typeof(ControlledApplication))
                ctrlapp = (ControlledApplication)sender;
            else if (senderType == typeof(Application))
                app = (Application)sender;

            if (uiapp != null
                    && uiapp.Application != null
                    && (uiapp.Application.Username != null || uiapp.Application.Username != string.Empty))
                return uiapp.Application.Username;
            else
                return string.Empty;
        }

        public static List<Element> GetElements(Document doc, IEnumerable<ElementId> elementIds) {
            var elements = new List<Element>();
            if (doc != null) {
                foreach (var eid in elementIds) {
                    if (eid != ElementId.InvalidElementId) {
                        var element = doc.GetElement(eid);
                        if (element != null)
                            elements.Add(element);
                    }
                }
            }
            return elements;
        }

        public static List<Dictionary<string,string>> GetViewData(IEnumerable<Element> elements) {
            var viewNames = new List<Dictionary<string, string>>();
            foreach (var element in elements)
                if (element is View) {
                    View view = (View)element;
                    string viewFamilyName = string.Empty;
                    if (view.Document != null) {
                        var viewamily = view.Document.GetElement(view.GetTypeId());
                        if (viewamily != null)
                            viewFamilyName = viewamily.Name;
                    }

                    viewNames.Add(new Dictionary<string, string> {
                        { "type", view.ViewType.ToString() },
                        { "family",  viewFamilyName },
                        { "name", view.Name },
                        { "title", view.get_Parameter(BuiltInParameter.VIEW_DESCRIPTION).AsString() },
                    });
                }
            return viewNames;
        }

        // event management ------------------------------------------------------------------------------------------
        public static void RegisterEventTelemetry(UIApplication uiApp, BigInteger flags) {
            foreach (EventType eventType in Enum.GetValues(typeof(EventType)))
                if ((flags & (new BigInteger(1) << (int)eventType)) > 0)
                    try {
                        ToggleEventListeners(uiApp, eventType);
                    }
                    catch (Exception registerEx) {
                        throw new Exception(
                            string.Format("Failed registering {0}, {1}",
                                          eventType.ToString(), registerEx.StackTrace)
                            );
                    }
        }

        public static void UnRegisterEventTelemetry(UIApplication uiApp, BigInteger flags) {
            foreach (EventType eventType in Enum.GetValues(typeof(EventType)))
                if ((flags & (new BigInteger(1) << (int)eventType)) > 0)
                    try {
                        ToggleEventListeners(uiApp, eventType, toggle_on: false);
                    }
                    catch (Exception unregisterEx) {
                        throw new Exception(
                            string.Format("Failed unregistering {0}, {1}",
                                          eventType.ToString(), unregisterEx.StackTrace)
                            );
                    }
        }

        // event handlers --------------------------------------------------------------------------------------------
        private static void UiApp_ViewActivating(object sender, Autodesk.Revit.UI.Events.ViewActivatingEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.UIApplication_ViewActivating),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                args = new Dictionary<string, object> {
                    { "from_view",  e.CurrentActiveView != null ? e.CurrentActiveView.Name : "" },
                    { "to_view",  e.NewActiveView != null ? e.NewActiveView.Name : "" },
                }
            }, sender, e);
        }

        private static void UiApp_ViewActivated(object sender, Autodesk.Revit.UI.Events.ViewActivatedEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.UIApplication_ViewActivated),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                args = new Dictionary<string, object> {
                    { "from_view",  e.PreviousActiveView != null ? e.PreviousActiveView.Name : "" },
                    { "to_view",  e.CurrentActiveView != null ? e.CurrentActiveView.Name : "" },
                }
            }, sender, e);
        }

#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017)
        private static void UiApp_TransferringProjectStandards(object sender, Autodesk.Revit.UI.Events.TransferringProjectStandardsEventArgs e) {
        }

        private static void UiApp_TransferredProjectStandards(object sender, Autodesk.Revit.UI.Events.TransferredProjectStandardsEventArgs e) {
        }
#endif

        private static void UiApp_Idling(object sender, Autodesk.Revit.UI.Events.IdlingEventArgs e) {
        }

#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017 || REVIT2018)
        private static void UiApp_FormulaEditing(object sender, Autodesk.Revit.UI.Events.FormulaEditingEventArgs e) {
        }
#endif

#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016)
        private static void UiApp_FabricationPartBrowserChanged(object sender, Autodesk.Revit.UI.Events.FabricationPartBrowserChangedEventArgs e) {
        }
#endif

        private static void UiApp_DockableFrameVisibilityChanged(object sender, Autodesk.Revit.UI.Events.DockableFrameVisibilityChangedEventArgs e) {
        }

        private static void UiApp_DockableFrameFocusChanged(object sender, Autodesk.Revit.UI.Events.DockableFrameFocusChangedEventArgs e) {
        }

        private static void UiApp_DisplayingOptionsDialog(object sender, Autodesk.Revit.UI.Events.DisplayingOptionsDialogEventArgs e) {
        }

#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016)
        private static void UiApp_DialogBoxShowing(object sender, Autodesk.Revit.UI.Events.DialogBoxShowingEventArgs e) {
        }
#endif

        private static void UiApp_ApplicationClosing(object sender, Autodesk.Revit.UI.Events.ApplicationClosingEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.UIApplication_ApplicationClosing),
            }, sender, e);
        }

        private static void Application_WorksharedOperationProgressChanged(object sender, WorksharedOperationProgressChangedEventArgs e) {
        }

        private static void Application_ViewPrinting(object sender, ViewPrintingEventArgs e) {
        }

        private static void Application_ViewPrinted(object sender, ViewPrintedEventArgs e) {
        }

        private static void Application_ViewExporting(object sender, ViewExportingEventArgs e) {
        }

        private static void Application_ViewExported(object sender, ViewExportedEventArgs e) {
        }

        private static void Application_ProgressChanged(object sender, ProgressChangedEventArgs e) {
        }

        private static void Application_LinkedResourceOpening(object sender, LinkedResourceOpeningEventArgs e) {
        }

        private static void Application_LinkedResourceOpened(object sender, LinkedResourceOpenedEventArgs e) {
        }

        private static void Application_FileImporting(object sender, FileImportingEventArgs e) {
        }

        private static void Application_FileImported(object sender, FileImportedEventArgs e) {
        }

        private static void Application_FileExporting(object sender, FileExportingEventArgs e) {
        }

        private static void Application_FileExported(object sender, FileExportedEventArgs e) {
        }

        private static void Application_FamilyLoadingIntoDocument(object sender, FamilyLoadingIntoDocumentEventArgs e) {
        }

        private static void Application_FamilyLoadedIntoDocument(object sender, FamilyLoadedIntoDocumentEventArgs e) {
        }

        private static void Application_FailuresProcessing(object sender, FailuresProcessingEventArgs e) {
        }

        private static void Application_ElementTypeDuplicating(object sender, ElementTypeDuplicatingEventArgs e) {
        }

        private static void Application_ElementTypeDuplicated(object sender, ElementTypeDuplicatedEventArgs e) {
        }

        private static void Application_DocumentWorksharingEnabled(object sender, DocumentWorksharingEnabledEventArgs e) {
        }

        private static void Application_DocumentSynchronizingWithCentral(object sender, DocumentSynchronizingWithCentralEventArgs e) {
        }

        private static void Application_DocumentSynchronizedWithCentral(object sender, DocumentSynchronizedWithCentralEventArgs e) {
        }

        private static void Application_DocumentSavingAs(object sender, DocumentSavingAsEventArgs e) {
        }

        private static void Application_DocumentSavedAs(object sender, DocumentSavedAsEventArgs e) {
        }

        private static void Application_DocumentSaving(object sender, DocumentSavingEventArgs e) {
        }

        private static void Application_DocumentSaved(object sender, DocumentSavedEventArgs e) {
        }

        private static void Application_DocumentPrinting(object sender, DocumentPrintingEventArgs e) {
            double marginx, marginy;
            int zoom;
            string zoom_type;
            var printParams = e.GetSettings().PrintParameters;

            // some print parameters throw exceptions
            try {
                marginx = printParams.UserDefinedMarginX;
                marginy = printParams.UserDefinedMarginY;
            } catch {
                marginx = marginy = 0.0;
            }

            try {
                zoom = printParams.Zoom;
                zoom_type = printParams.ZoomType.ToString();
            }
            catch {
                zoom = 0;
                zoom_type = string.Empty;
            }

            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_DocumentPrinting),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                args = new Dictionary<string, object> {
                { "views", GetViewData(GetElements(e.Document, e.GetViewElementIds())) },
                { "settings", new Dictionary<string,object> {
                    { "color_depth", printParams.ColorDepth.ToString() },
                    { "hidden_line_view_type", printParams.HiddenLineViews.ToString() },
                    { "hide_cropbounds", printParams.HideCropBoundaries },
                    { "hide_refplanes", printParams.HideReforWorkPlanes },
                    { "hide_scopeboxes", printParams.HideScopeBoxes },
                    { "hide_unref_vewtags", printParams.HideUnreferencedViewTags },
                    { "margin_type", printParams.MarginType.ToString() },
                    { "mask_lines", printParams.MaskCoincidentLines },
                    { "page_orientation", printParams.PageOrientation.ToString() },
                    { "paper_placement", printParams.PaperPlacement.ToString() },
                    { "paper_size", printParams.PaperSize.Name },
                    { "paper_source", printParams.PaperSource.Name },
                    { "raster_quality", printParams.RasterQuality.ToString() },
                    { "halftone_thinlines", printParams.ReplaceHalftoneWithThinLines },
                    { "user_margin_x",  marginx },
                    { "user_margin_y",  marginy },
                    { "blue_hyperlinks", printParams.ViewLinksinBlue },
                    { "zoom", zoom },
                    { "zoom_type", zoom_type },
                }},
            }
            }, sender, e);
        }

        private static void Application_DocumentPrinted(object sender, DocumentPrintedEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_DocumentPrinted),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                status = e.Status.ToString(),
                args = new Dictionary<string, object> {
                    { "print_pass_views", GetViewData(GetElements(e.Document, e.GetPrintedViewElementIds())) },
                    { "print_fail_views",  GetViewData(GetElements(e.Document, e.GetFailedViewElementIds())) },
                }
            }, sender, e);
        }

        private static void Application_DocumentOpening(object sender, DocumentOpeningEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_DocumentOpening),
                doctype = e.DocumentType.ToString(),
                docpath = e.PathName,
            }, sender, e);
        }

        private static void Application_DocumentOpened(object sender, DocumentOpenedEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_DocumentOpened),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                status = e.Status.ToString(),
            }, sender, e);
        }

        private static void Application_DocumentCreating(object sender, DocumentCreatingEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_DocumentCreating),
                doctype = e.DocumentType.ToString(),
                doctemplate = e.Template,
            }, sender, e);
        }

        private static void Application_DocumentCreated(object sender, DocumentCreatedEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_DocumentCreated),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                status = e.Status.ToString(),
            }, sender, e);
        }

        private static void Application_DocumentClosing(object sender, DocumentClosingEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_DocumentClosing),
                docid = e.DocumentId,
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
            }, sender, e);
        }

        private static void Application_DocumentClosed(object sender, DocumentClosedEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_DocumentClosed),
                docid = e.DocumentId,
                status = e.Status.ToString(),
            }, sender, e);
        }

        private static void Application_DocumentChanged(object sender, DocumentChangedEventArgs e) {
            var doc = e.GetDocument();
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_DocumentChanged),
                docname = doc != null ? doc.Title : "",
                docpath = doc != null ? doc.PathName : "",
                args = new Dictionary<string, object> {
                    { "operation",  e.Operation.ToString() },
                    { "added",  e.GetAddedElementIds().Count },
                    { "deleted",  e.GetDeletedElementIds().Count },
                    { "modified",  e.GetModifiedElementIds().Count },
                    { "txn_names",  e.GetTransactionNames().ToList() },
                }
            }, sender, e);
        }

        public static void Application_ApplicationInitialized(object sender, ApplicationInitializedEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_ApplicationInitialized),
            }, sender, e);
        }
    }
}
