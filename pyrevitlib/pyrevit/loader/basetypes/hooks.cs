using System;
using System.IO;
using System.Collections.Generic;
using System.Diagnostics;

using Autodesk.Revit.ApplicationServices;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;

namespace PyRevitBaseClasses {
    public class EventHook {
        public const string script_key = "script";
        public const string event_type_key = "event_type";
        public const string syspaths_key = "syspaths";
        public const string extension_name_key = "extension_name";
        public const string id_key = "id";

        public string Script;
        public EventType EventType;
        public string[] SearchPaths;
        public string ExtensionName;
        public string UniqueId;

        public EventHook(string script, EventType event_type, string[] syspaths, string extension_name, string id) {
            Script = script;
            EventType = event_type;
            SearchPaths = syspaths;
            ExtensionName = extension_name;
            UniqueId = id;
        }

        public override int GetHashCode() {
            return UniqueId.GetHashCode();
        }
    }

    public static class PyRevitHooks {
        private static void toggleHooks(UIApplication uiApp, EventType eventType, bool toggle_on = true) {
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

        public static void Execute(EventHook eventHook, object eventSender, object eventArgs) {
            // 1: ----------------------------------------------------------------------------------------------------
            #region Setup pyRevit Command Runtime
            var pyrvtScript =
                new PyRevitScriptRuntime(
                    cmdData: null,
                    elements: new ElementSet(),
                    scriptSource: eventHook.Script,
                    configScriptSource: eventHook.Script,
                    syspaths: eventHook.SearchPaths,
                    arguments: new string[] { },
                    helpSource: "",
                    cmdName: "",
                    cmdBundle: "",
                    cmdExtension: eventHook.ExtensionName,
                    cmdUniqueName: eventHook.UniqueId,
                    needsCleanEngine: false,
                    needsFullFrameEngine: false,
                    needsPersistentEngine: false,
                    refreshEngine: false,
                    forcedDebugMode: false,
                    configScriptMode: false,
                    executedFromUI: false
                    );

            // set sender and args for events
            pyrvtScript.EventSender = eventSender;
            pyrvtScript.EventArgs = eventArgs;
            #endregion

            // 2: ----------------------------------------------------------------------------------------------------
            #region Execute and log results
            var res = ScriptExecutor.ExecuteScript(ref pyrvtScript);

            // TODO: log results into command execution telemetry?
            #endregion
        }

        public static HashSet<EventHook> GetEventHooks(EventType eventType) {
            var env = new EnvDictionary();
            var eventHooks = new HashSet<EventHook>();
            foreach (Dictionary<string, object> eventHook in env.EventHooks)
                if ((EventType)eventHook[EventHook.event_type_key] == eventType)
                    eventHooks.Add(
                        new EventHook(
                            script: (string)eventHook[EventHook.script_key],
                            event_type: (EventType)eventHook[EventHook.event_type_key],
                            syspaths: (string[])eventHook[EventHook.syspaths_key],
                            extension_name: (string)eventHook[EventHook.extension_name_key],
                            id: (string)eventHook[EventHook.id_key]
                            )
                        );
            return eventHooks;
        }

        public static HashSet<EventHook> GetAllEventHooks() {
            var env = new EnvDictionary();
            var eventHooks = new HashSet<EventHook>();
            foreach (Dictionary<string, object> eventHook in env.EventHooks)
                eventHooks.Add(
                    new EventHook(
                        script: (string)eventHook[EventHook.script_key],
                        event_type: (EventType)eventHook[EventHook.event_type_key],
                        syspaths: (string[])eventHook[EventHook.syspaths_key],
                        extension_name: (string)eventHook[EventHook.extension_name_key],
                        id: (string)eventHook[EventHook.id_key]
                        )
                    );
            return eventHooks;
        }

        public static void ClearEventHooks() {
            var env = new EnvDictionary();
            env.ResetEventHooks();
        }

        public static void AddEventHook(EventHook eventHook) {
            var env = new EnvDictionary();
            env.EventHooks.Add(
                new Dictionary<string, object> {
                    { EventHook.script_key, eventHook.Script },
                    { EventHook.event_type_key, eventHook.EventType },
                    { EventHook.syspaths_key, eventHook.SearchPaths },
                    { EventHook.extension_name_key, eventHook.ExtensionName },
                    { EventHook.id_key, eventHook.UniqueId },
                }
            );
        }

        public static void RemoveEventHook(EventHook eventHook) {
            var env = new EnvDictionary();
            env.EventHooks.Remove(
                 new Dictionary<string, object> {
                    { EventHook.script_key, eventHook.Script },
                    { EventHook.event_type_key, eventHook.EventType },
                    { EventHook.syspaths_key, eventHook.SearchPaths },
                    { EventHook.extension_name_key, eventHook.ExtensionName },
                    { EventHook.id_key, eventHook.UniqueId },
                });
        }

        public static void RegisterEventType(UIApplication uiApp, EventType eventType) {
            toggleHooks(uiApp, eventType);
        }

        public static void UnRegisterEventType(UIApplication uiApp, EventType eventType) {
            toggleHooks(uiApp, eventType, toggle_on: false);
        }

        public static void RegisterHook(UIApplication uiApp, string script, EventType eventType, string[] searchPaths, string extName, string uniqueId) {
            var eventHook = new EventHook(script, eventType, searchPaths, extName, uniqueId);
            AddEventHook(eventHook);
        }

        public static void UnRegisterHook(UIApplication uiApp, string script, EventType eventType, string[] searchPaths, string extName, string uniqueId) {
            var eventHook = new EventHook(script, eventType, searchPaths, extName, uniqueId);
            RemoveEventHook(eventHook);
        }

        public static void UnRegisterAllHooks(UIApplication uiApp) {
            ClearEventHooks();
        }

        public static void ExecuteEventHooks(EventType eventType, object eventSender, object eventArgs) {
            foreach (EventHook eventHook in GetEventHooks(eventType))
                Execute(
                    eventHook: eventHook,
                    eventSender: eventSender,
                    eventArgs: eventArgs
                    );
        }

        public static void ActivateEventHooks(UIApplication uiApp) {
            foreach (EventHook eventHook in GetAllEventHooks())
                RegisterEventType(uiApp, eventHook.EventType);
        }

        public static void DeactivateEventHooks(UIApplication uiApp) {
            foreach (EventHook eventHook in GetAllEventHooks())
                UnRegisterEventType(uiApp, eventHook.EventType);
        }

        // event handlers --------------------------------------------------------------------------------------------

        private static void UiApp_ViewActivating(object sender, Autodesk.Revit.UI.Events.ViewActivatingEventArgs e) {
            ExecuteEventHooks(EventType.UIApplication_ViewActivating, sender, e);
        }

        private static void UiApp_ViewActivated(object sender, Autodesk.Revit.UI.Events.ViewActivatedEventArgs e) {
            ExecuteEventHooks(EventType.UIApplication_ViewActivated, sender, e);
        }

#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017)
        private static void UiApp_TransferringProjectStandards(object sender, Autodesk.Revit.UI.Events.TransferringProjectStandardsEventArgs e) {
            ExecuteEventHooks(EventType.UIApplication_TransferringProjectStandards, sender, e);
        }

        private static void UiApp_TransferredProjectStandards(object sender, Autodesk.Revit.UI.Events.TransferredProjectStandardsEventArgs e) {
            ExecuteEventHooks(EventType.UIApplication_TransferredProjectStandards, sender, e);
        }
#endif

        private static void UiApp_Idling(object sender, Autodesk.Revit.UI.Events.IdlingEventArgs e) {
            ExecuteEventHooks(EventType.UIApplication_Idling, sender, e);
        }

#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017 || REVIT2018)
        private static void UiApp_FormulaEditing(object sender, Autodesk.Revit.UI.Events.FormulaEditingEventArgs e) {
            ExecuteEventHooks(EventType.UIApplication_FormulaEditing, sender, e);
        }
#endif

#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016)
        private static void UiApp_FabricationPartBrowserChanged(object sender, Autodesk.Revit.UI.Events.FabricationPartBrowserChangedEventArgs e) {
            ExecuteEventHooks(EventType.UIApplication_FabricationPartBrowserChanged, sender, e);
        }
#endif

        private static void UiApp_DockableFrameVisibilityChanged(object sender, Autodesk.Revit.UI.Events.DockableFrameVisibilityChangedEventArgs e) {
            ExecuteEventHooks(EventType.UIApplication_DockableFrameVisibilityChanged, sender, e);
        }

        private static void UiApp_DockableFrameFocusChanged(object sender, Autodesk.Revit.UI.Events.DockableFrameFocusChangedEventArgs e) {
            ExecuteEventHooks(EventType.UIApplication_DockableFrameFocusChanged, sender, e);
        }

        private static void UiApp_DisplayingOptionsDialog(object sender, Autodesk.Revit.UI.Events.DisplayingOptionsDialogEventArgs e) {
            ExecuteEventHooks(EventType.UIApplication_DisplayingOptionsDialog, sender, e);
        }

#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016)
        private static void UiApp_DialogBoxShowing(object sender, Autodesk.Revit.UI.Events.DialogBoxShowingEventArgs e) {
            ExecuteEventHooks(EventType.UIApplication_DialogBoxShowing, sender, e);
        }
#endif

        private static void UiApp_ApplicationClosing(object sender, Autodesk.Revit.UI.Events.ApplicationClosingEventArgs e) {
            ExecuteEventHooks(EventType.UIApplication_ApplicationClosing, sender, e);
        }

        private static void Application_WorksharedOperationProgressChanged(object sender, Autodesk.Revit.DB.Events.WorksharedOperationProgressChangedEventArgs e) {
            ExecuteEventHooks(EventType.Application_WorksharedOperationProgressChanged, sender, e);
        }

        private static void Application_ViewPrinting(object sender, Autodesk.Revit.DB.Events.ViewPrintingEventArgs e) {
            ExecuteEventHooks(EventType.Application_ViewPrinting, sender, e);
        }

        private static void Application_ViewPrinted(object sender, Autodesk.Revit.DB.Events.ViewPrintedEventArgs e) {
            ExecuteEventHooks(EventType.Application_ViewPrinted, sender, e);
        }

        private static void Application_ViewExporting(object sender, Autodesk.Revit.DB.Events.ViewExportingEventArgs e) {
            ExecuteEventHooks(EventType.Application_ViewExporting, sender, e);
        }

        private static void Application_ViewExported(object sender, Autodesk.Revit.DB.Events.ViewExportedEventArgs e) {
            ExecuteEventHooks(EventType.Application_ViewExported, sender, e);
        }

        private static void Application_ProgressChanged(object sender, Autodesk.Revit.DB.Events.ProgressChangedEventArgs e) {
            ExecuteEventHooks(EventType.Application_ProgressChanged, sender, e);
        }

        private static void Application_LinkedResourceOpening(object sender, Autodesk.Revit.DB.Events.LinkedResourceOpeningEventArgs e) {
            ExecuteEventHooks(EventType.Application_LinkedResourceOpening, sender, e);
        }

        private static void Application_LinkedResourceOpened(object sender, Autodesk.Revit.DB.Events.LinkedResourceOpenedEventArgs e) {
            ExecuteEventHooks(EventType.Application_LinkedResourceOpened, sender, e);
        }

        private static void Application_FileImporting(object sender, Autodesk.Revit.DB.Events.FileImportingEventArgs e) {
            ExecuteEventHooks(EventType.Application_FileImporting, sender, e);
        }

        private static void Application_FileImported(object sender, Autodesk.Revit.DB.Events.FileImportedEventArgs e) {
            ExecuteEventHooks(EventType.Application_FileImported, sender, e);
        }

        private static void Application_FileExporting(object sender, Autodesk.Revit.DB.Events.FileExportingEventArgs e) {
            ExecuteEventHooks(EventType.Application_FileExporting, sender, e);
        }

        private static void Application_FileExported(object sender, Autodesk.Revit.DB.Events.FileExportedEventArgs e) {
            ExecuteEventHooks(EventType.Application_FileExported, sender, e);
        }

        private static void Application_FamilyLoadingIntoDocument(object sender, Autodesk.Revit.DB.Events.FamilyLoadingIntoDocumentEventArgs e) {
            ExecuteEventHooks(EventType.Application_FamilyLoadingIntoDocument, sender, e);
        }

        private static void Application_FamilyLoadedIntoDocument(object sender, Autodesk.Revit.DB.Events.FamilyLoadedIntoDocumentEventArgs e) {
            ExecuteEventHooks(EventType.Application_FamilyLoadedIntoDocument, sender, e);
        }

        private static void Application_FailuresProcessing(object sender, Autodesk.Revit.DB.Events.FailuresProcessingEventArgs e) {
            ExecuteEventHooks(EventType.Application_FailuresProcessing, sender, e);
        }

        private static void Application_ElementTypeDuplicating(object sender, Autodesk.Revit.DB.Events.ElementTypeDuplicatingEventArgs e) {
            ExecuteEventHooks(EventType.Application_ElementTypeDuplicating, sender, e);
        }

        private static void Application_ElementTypeDuplicated(object sender, Autodesk.Revit.DB.Events.ElementTypeDuplicatedEventArgs e) {
            ExecuteEventHooks(EventType.Application_ElementTypeDuplicated, sender, e);
        }

        private static void Application_DocumentWorksharingEnabled(object sender, Autodesk.Revit.DB.Events.DocumentWorksharingEnabledEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentWorksharingEnabled, sender, e);
        }

        private static void Application_DocumentSynchronizingWithCentral(object sender, Autodesk.Revit.DB.Events.DocumentSynchronizingWithCentralEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentSynchronizingWithCentral, sender, e);
        }

        private static void Application_DocumentSynchronizedWithCentral(object sender, Autodesk.Revit.DB.Events.DocumentSynchronizedWithCentralEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentSynchronizedWithCentral, sender, e);
        }

        private static void Application_DocumentSavingAs(object sender, Autodesk.Revit.DB.Events.DocumentSavingAsEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentSavingAs, sender, e);
        }

        private static void Application_DocumentSavedAs(object sender, Autodesk.Revit.DB.Events.DocumentSavedAsEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentSavedAs, sender, e);
        }

        private static void Application_DocumentSaving(object sender, Autodesk.Revit.DB.Events.DocumentSavingEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentSaving, sender, e);
        }

        private static void Application_DocumentSaved(object sender, Autodesk.Revit.DB.Events.DocumentSavedEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentSaved, sender, e);
        }

        private static void Application_DocumentPrinting(object sender, Autodesk.Revit.DB.Events.DocumentPrintingEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentPrinting, sender, e);
        }

        private static void Application_DocumentPrinted(object sender, Autodesk.Revit.DB.Events.DocumentPrintedEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentPrinted, sender, e);
        }

        private static void Application_DocumentOpening(object sender, Autodesk.Revit.DB.Events.DocumentOpeningEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentOpening, sender, e);
        }

        private static void Application_DocumentOpened(object sender, Autodesk.Revit.DB.Events.DocumentOpenedEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentOpened, sender, e);
        }

        private static void Application_DocumentCreating(object sender, Autodesk.Revit.DB.Events.DocumentCreatingEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentCreating, sender, e);
        }

        private static void Application_DocumentCreated(object sender, Autodesk.Revit.DB.Events.DocumentCreatedEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentCreated, sender, e);
        }

        private static void Application_DocumentClosing(object sender, Autodesk.Revit.DB.Events.DocumentClosingEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentClosing, sender, e);
        }

        private static void Application_DocumentClosed(object sender, Autodesk.Revit.DB.Events.DocumentClosedEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentClosed, sender, e);
        }

        private static void Application_DocumentChanged(object sender, Autodesk.Revit.DB.Events.DocumentChangedEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentChanged, sender, e);
        }

        private static void Application_ApplicationInitialized(object sender, Autodesk.Revit.DB.Events.ApplicationInitializedEventArgs e) {
            ExecuteEventHooks(EventType.Application_ApplicationInitialized, sender, e);
        }
    }
}
