using System;
using System.Numerics;
using System.Collections.Generic;
using System.Net;
using System.Web.Script.Serialization;
using System.IO;
using System.Threading.Tasks;
using Autodesk.Revit.ApplicationServices;
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


    public class TelemetryRecord {
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

        public TelemetryRecord(
                string revitUsername,
                string revitVersion,
                string revitBuild,
                string revitProcessId,
                string pyRevitVersion,
                string cloneName,
                bool debugModeEnabled,
                bool configModeEnabled,
                bool execFromGUI,
                bool cleanEngine,
                bool fullframeEngine,
                string pyRevitCommandName,
                string pyRevitCommandBundle,
                string pyRevitCommandExtension,
                string pyRevitCommandUniqueName,
                string pyRevitCommandPath,
                string docName,
                string docPath,
                int executorResultCode,
                Dictionary<string, string> resultDict,
                TraceInfo traceInfo) {
            meta = new Dictionary<string, string> {
                { "schema", "2.0"},
            };

            timestamp = CommonUtils.GetISOTimeStampNow();

            username = revitUsername;
            revit = revitVersion;
            revitbuild = revitBuild;
            sessionid = revitProcessId;
            pyrevit = pyRevitVersion;
            clone = cloneName;
            debug = debugModeEnabled;
            config = configModeEnabled;
            from_gui = execFromGUI;
            clean_engine = cleanEngine;
            fullframe_engine = fullframeEngine;
            commandname = pyRevitCommandName;
            commandbundle = pyRevitCommandBundle;
            commandextension = pyRevitCommandExtension;
            commanduniquename = pyRevitCommandUniqueName;
            scriptpath = pyRevitCommandPath;
            docname = docName;
            docpath = docPath;
            resultcode = executorResultCode;
            commandresults = resultDict;
            trace = traceInfo;
        }
    }


    public class ScriptTelemetry {
        public static string MakeTelemetryRecord(TelemetryRecord record) {
            return new JavaScriptSerializer().Serialize(record);
        }

        public static void PostTelemetryRecordToServer(string _telemetryServerUrl, TelemetryRecord record) {
            var httpWebRequest = (HttpWebRequest)WebRequest.Create(_telemetryServerUrl);
            httpWebRequest.ContentType = "application/json";
            httpWebRequest.Method = "POST";
            httpWebRequest.UserAgent = "pyrevit";

            using (var streamWriter = new StreamWriter(httpWebRequest.GetRequestStream())) {
                string json = MakeTelemetryRecord(record);

                streamWriter.Write(json);
                streamWriter.Flush();
                streamWriter.Close();
            }

            var httpResponse = (HttpWebResponse)httpWebRequest.GetResponse();
            using (var streamReader = new StreamReader(httpResponse.GetResponseStream())) {
                var result = streamReader.ReadToEnd();
            }
        }

        public static void WriteTelemetryRecordToFile(string _telemetryFilePath, TelemetryRecord record) {
            // Read existing json data
            string jsonData = "[]";
            if (File.Exists(_telemetryFilePath)) {
                jsonData = File.ReadAllText(_telemetryFilePath);
            }
            else {
                File.WriteAllText(_telemetryFilePath, jsonData);
            }

            // De-serialize to object or create new list
            var logData = new JavaScriptSerializer().Deserialize<List<TelemetryRecord>>(jsonData);

            // Add any new employees
            logData.Add(record);

            // Update json data string
            jsonData = new JavaScriptSerializer().Serialize(logData);
            File.WriteAllText(_telemetryFilePath, jsonData);
        }

        public static void LogTelemetryRecord(TelemetryRecord record) {
            var envDict = new EnvDictionary();

            if (envDict.TelemetryState) {
                if (envDict.TelemetryState && envDict.TelemetryServerUrl != null && !string.IsNullOrEmpty(envDict.TelemetryServerUrl))
                    new Task(() => PostTelemetryRecordToServer(envDict.TelemetryServerUrl, record)).Start();

                if (envDict.TelemetryState && envDict.TelemetryFilePath != null && !string.IsNullOrEmpty(envDict.TelemetryFilePath))
                    new Task(() => WriteTelemetryRecordToFile(envDict.TelemetryFilePath, record)).Start();
            }
        }
    }


    public class EventTelemetry {
        private static void toggleEventListeners(UIApplication uiApp, EventType eventType, bool toggle_on = true) {
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

        // event management ------------------------------------------------------------------------------------------
        public static void RegisterEventTelemetry(UIApplication uiApp, BigInteger flags) {
            foreach (EventType eventType in Enum.GetValues(typeof(EventType)))
                if ((flags & (new BigInteger(1) << (int)eventType)) > 0)
                    toggleEventListeners(uiApp, eventType);
        }

        public static void UnRegisterEventTelemetry(UIApplication uiApp, BigInteger flags) {
            foreach (EventType eventType in Enum.GetValues(typeof(EventType)))
                if ((flags & (new BigInteger(1) << (int)eventType)) > 0)
                    toggleEventListeners(uiApp, eventType, toggle_on: false);
        }

        // event handlers --------------------------------------------------------------------------------------------
        private static void UiApp_ViewActivating(object sender, Autodesk.Revit.UI.Events.ViewActivatingEventArgs e) {
        }

        private static void UiApp_ViewActivated(object sender, Autodesk.Revit.UI.Events.ViewActivatedEventArgs e) {
        }

        private static void UiApp_TransferringProjectStandards(object sender, Autodesk.Revit.UI.Events.TransferringProjectStandardsEventArgs e) {
        }

        private static void UiApp_TransferredProjectStandards(object sender, Autodesk.Revit.UI.Events.TransferredProjectStandardsEventArgs e) {
        }

        private static void UiApp_Idling(object sender, Autodesk.Revit.UI.Events.IdlingEventArgs e) {
        }

        private static void UiApp_FormulaEditing(object sender, Autodesk.Revit.UI.Events.FormulaEditingEventArgs e) {
        }

        private static void UiApp_FabricationPartBrowserChanged(object sender, Autodesk.Revit.UI.Events.FabricationPartBrowserChangedEventArgs e) {
        }

        private static void UiApp_DockableFrameVisibilityChanged(object sender, Autodesk.Revit.UI.Events.DockableFrameVisibilityChangedEventArgs e) {
        }

        private static void UiApp_DockableFrameFocusChanged(object sender, Autodesk.Revit.UI.Events.DockableFrameFocusChangedEventArgs e) {
        }

        private static void UiApp_DisplayingOptionsDialog(object sender, Autodesk.Revit.UI.Events.DisplayingOptionsDialogEventArgs e) {
        }

        private static void UiApp_DialogBoxShowing(object sender, Autodesk.Revit.UI.Events.DialogBoxShowingEventArgs e) {
        }

        private static void UiApp_ApplicationClosing(object sender, Autodesk.Revit.UI.Events.ApplicationClosingEventArgs e) {
        }

        private static void Application_WorksharedOperationProgressChanged(object sender, Autodesk.Revit.DB.Events.WorksharedOperationProgressChangedEventArgs e) {
        }

        private static void Application_ViewPrinting(object sender, Autodesk.Revit.DB.Events.ViewPrintingEventArgs e) {
        }

        private static void Application_ViewPrinted(object sender, Autodesk.Revit.DB.Events.ViewPrintedEventArgs e) {
        }

        private static void Application_ViewExporting(object sender, Autodesk.Revit.DB.Events.ViewExportingEventArgs e) {
        }

        private static void Application_ViewExported(object sender, Autodesk.Revit.DB.Events.ViewExportedEventArgs e) {
        }

        private static void Application_ProgressChanged(object sender, Autodesk.Revit.DB.Events.ProgressChangedEventArgs e) {
        }

        private static void Application_LinkedResourceOpening(object sender, Autodesk.Revit.DB.Events.LinkedResourceOpeningEventArgs e) {
        }

        private static void Application_LinkedResourceOpened(object sender, Autodesk.Revit.DB.Events.LinkedResourceOpenedEventArgs e) {
        }

        private static void Application_FileImporting(object sender, Autodesk.Revit.DB.Events.FileImportingEventArgs e) {
        }

        private static void Application_FileImported(object sender, Autodesk.Revit.DB.Events.FileImportedEventArgs e) {
        }

        private static void Application_FileExporting(object sender, Autodesk.Revit.DB.Events.FileExportingEventArgs e) {
        }

        private static void Application_FileExported(object sender, Autodesk.Revit.DB.Events.FileExportedEventArgs e) {
        }

        private static void Application_FamilyLoadingIntoDocument(object sender, Autodesk.Revit.DB.Events.FamilyLoadingIntoDocumentEventArgs e) {
        }

        private static void Application_FamilyLoadedIntoDocument(object sender, Autodesk.Revit.DB.Events.FamilyLoadedIntoDocumentEventArgs e) {
        }

        private static void Application_FailuresProcessing(object sender, Autodesk.Revit.DB.Events.FailuresProcessingEventArgs e) {
        }

        private static void Application_ElementTypeDuplicating(object sender, Autodesk.Revit.DB.Events.ElementTypeDuplicatingEventArgs e) {
        }

        private static void Application_ElementTypeDuplicated(object sender, Autodesk.Revit.DB.Events.ElementTypeDuplicatedEventArgs e) {
        }

        private static void Application_DocumentWorksharingEnabled(object sender, Autodesk.Revit.DB.Events.DocumentWorksharingEnabledEventArgs e) {
        }

        private static void Application_DocumentSynchronizingWithCentral(object sender, Autodesk.Revit.DB.Events.DocumentSynchronizingWithCentralEventArgs e) {
        }

        private static void Application_DocumentSynchronizedWithCentral(object sender, Autodesk.Revit.DB.Events.DocumentSynchronizedWithCentralEventArgs e) {
        }

        private static void Application_DocumentSavingAs(object sender, Autodesk.Revit.DB.Events.DocumentSavingAsEventArgs e) {
        }

        private static void Application_DocumentSavedAs(object sender, Autodesk.Revit.DB.Events.DocumentSavedAsEventArgs e) {
        }

        private static void Application_DocumentSaving(object sender, Autodesk.Revit.DB.Events.DocumentSavingEventArgs e) {
        }

        private static void Application_DocumentSaved(object sender, Autodesk.Revit.DB.Events.DocumentSavedEventArgs e) {
        }

        private static void Application_DocumentPrinting(object sender, Autodesk.Revit.DB.Events.DocumentPrintingEventArgs e) {
        }

        private static void Application_DocumentPrinted(object sender, Autodesk.Revit.DB.Events.DocumentPrintedEventArgs e) {
        }

        private static void Application_DocumentOpening(object sender, Autodesk.Revit.DB.Events.DocumentOpeningEventArgs e) {
        }

        private static void Application_DocumentOpened(object sender, Autodesk.Revit.DB.Events.DocumentOpenedEventArgs e) {
        }

        private static void Application_DocumentCreating(object sender, Autodesk.Revit.DB.Events.DocumentCreatingEventArgs e) {
        }

        private static void Application_DocumentCreated(object sender, Autodesk.Revit.DB.Events.DocumentCreatedEventArgs e) {
        }

        private static void Application_DocumentClosing(object sender, Autodesk.Revit.DB.Events.DocumentClosingEventArgs e) {
        }

        private static void Application_DocumentClosed(object sender, Autodesk.Revit.DB.Events.DocumentClosedEventArgs e) {
        }

        private static void Application_DocumentChanged(object sender, Autodesk.Revit.DB.Events.DocumentChangedEventArgs e) {
        }

        public static void Application_ApplicationInitialized(object sender, Autodesk.Revit.DB.Events.ApplicationInitializedEventArgs e) {
        }
    }
}
