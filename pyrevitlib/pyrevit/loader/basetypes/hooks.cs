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

    public class PyRevitHooks : IEventTypeHandler {
        public static void Execute(EventHook eventHook, object eventSender, object eventArgs) {
            // 1: ----------------------------------------------------------------------------------------------------
            #region Setup pyRevit Command Runtime
            var pyrvtScript =
                new PyRevitScriptRuntime(
                    cmdData: null,
                    elements: new ElementSet(),
                    scriptSource: eventHook.Script,
                    configScriptSource: eventHook.Script,
                    searchpaths: eventHook.SearchPaths,
                    arguments: new string[] { },
                    helpSource: "",
                    cmdName: string.Format("hooks.{0}", Path.GetFileNameWithoutExtension(eventHook.Script)),
                    cmdBundle: string.Format("{0}.hooks", eventHook.ExtensionName),
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

        public static void ExecuteEventHooks(EventType eventType, object eventSender, object eventArgs) {
            foreach (EventHook eventHook in GetEventHooks(eventType))
                Execute(
                    eventHook: eventHook,
                    eventSender: eventSender,
                    eventArgs: eventArgs
                    );
        }

        public void RegisterEventType(UIApplication uiApp, EventType eventType) {
            EventUtils.ToggleHooks<PyRevitHooks>(this, uiApp, eventType);
        }

        public void UnRegisterEventType(UIApplication uiApp, EventType eventType) {
            EventUtils.ToggleHooks<PyRevitHooks>(this, uiApp, eventType, toggle_on: false);
        }

        public void RegisterHook(UIApplication uiApp, string script, EventType eventType, string[] searchPaths, string extName, string uniqueId) {
            var eventHook = new EventHook(script, eventType, searchPaths, extName, uniqueId);
            AddEventHook(eventHook);
        }

        public void UnRegisterHook(UIApplication uiApp, string script, EventType eventType, string[] searchPaths, string extName, string uniqueId) {
            var eventHook = new EventHook(script, eventType, searchPaths, extName, uniqueId);
            RemoveEventHook(eventHook);
        }

        public void UnRegisterAllHooks(UIApplication uiApp) {
            ClearEventHooks();
        }

        public void ActivateEventHooks(UIApplication uiApp) {
            foreach (EventHook eventHook in GetAllEventHooks())
                RegisterEventType(uiApp, eventHook.EventType);
        }

        public void DeactivateEventHooks(UIApplication uiApp) {
            foreach (EventHook eventHook in GetAllEventHooks())
                UnRegisterEventType(uiApp, eventHook.EventType);
        }

        // event handlers --------------------------------------------------------------------------------------------

        public void UIApplication_ViewActivating(object sender, Autodesk.Revit.UI.Events.ViewActivatingEventArgs e) {
            ExecuteEventHooks(EventType.UIApplication_ViewActivating, sender, e);
        }

        public void UIApplication_ViewActivated(object sender, Autodesk.Revit.UI.Events.ViewActivatedEventArgs e) {
            ExecuteEventHooks(EventType.UIApplication_ViewActivated, sender, e);
        }

#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017)
        public void UIApplication_TransferringProjectStandards(object sender, Autodesk.Revit.UI.Events.TransferringProjectStandardsEventArgs e) {
            ExecuteEventHooks(EventType.UIApplication_TransferringProjectStandards, sender, e);
        }

        public void UIApplication_TransferredProjectStandards(object sender, Autodesk.Revit.UI.Events.TransferredProjectStandardsEventArgs e) {
            ExecuteEventHooks(EventType.UIApplication_TransferredProjectStandards, sender, e);
        }
#endif

        public void UIApplication_Idling(object sender, Autodesk.Revit.UI.Events.IdlingEventArgs e) {
            ExecuteEventHooks(EventType.UIApplication_Idling, sender, e);
        }

#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017 || REVIT2018)
        public void UIApplication_FormulaEditing(object sender, Autodesk.Revit.UI.Events.FormulaEditingEventArgs e) {
            ExecuteEventHooks(EventType.UIApplication_FormulaEditing, sender, e);
        }
#endif

#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016)
        public void UIApplication_FabricationPartBrowserChanged(object sender, Autodesk.Revit.UI.Events.FabricationPartBrowserChangedEventArgs e) {
            ExecuteEventHooks(EventType.UIApplication_FabricationPartBrowserChanged, sender, e);
        }
#endif

#if !(REVIT2013 || REVIT2014)
        public void UIApplication_DockableFrameVisibilityChanged(object sender, Autodesk.Revit.UI.Events.DockableFrameVisibilityChangedEventArgs e) {
            ExecuteEventHooks(EventType.UIApplication_DockableFrameVisibilityChanged, sender, e);
        }

        public void UIApplication_DockableFrameFocusChanged(object sender, Autodesk.Revit.UI.Events.DockableFrameFocusChangedEventArgs e) {
            ExecuteEventHooks(EventType.UIApplication_DockableFrameFocusChanged, sender, e);
        }
#endif

        public void UIApplication_DisplayingOptionsDialog(object sender, Autodesk.Revit.UI.Events.DisplayingOptionsDialogEventArgs e) {
            ExecuteEventHooks(EventType.UIApplication_DisplayingOptionsDialog, sender, e);
        }

        public void UIApplication_DialogBoxShowing(object sender, Autodesk.Revit.UI.Events.DialogBoxShowingEventArgs e) {
            ExecuteEventHooks(EventType.UIApplication_DialogBoxShowing, sender, e);
        }

        public void UIApplication_ApplicationClosing(object sender, Autodesk.Revit.UI.Events.ApplicationClosingEventArgs e) {
            ExecuteEventHooks(EventType.UIApplication_ApplicationClosing, sender, e);
        }

#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017)
        public void Application_WorksharedOperationProgressChanged(object sender, Autodesk.Revit.DB.Events.WorksharedOperationProgressChangedEventArgs e) {
            ExecuteEventHooks(EventType.Application_WorksharedOperationProgressChanged, sender, e);
        }
#endif
        public void Application_ViewPrinting(object sender, Autodesk.Revit.DB.Events.ViewPrintingEventArgs e) {
            ExecuteEventHooks(EventType.Application_ViewPrinting, sender, e);
        }

        public void Application_ViewPrinted(object sender, Autodesk.Revit.DB.Events.ViewPrintedEventArgs e) {
            ExecuteEventHooks(EventType.Application_ViewPrinted, sender, e);
        }

#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017)
        public void Application_ViewExporting(object sender, Autodesk.Revit.DB.Events.ViewExportingEventArgs e) {
            ExecuteEventHooks(EventType.Application_ViewExporting, sender, e);
        }

        public void Application_ViewExported(object sender, Autodesk.Revit.DB.Events.ViewExportedEventArgs e) {
            ExecuteEventHooks(EventType.Application_ViewExported, sender, e);
        }
#endif
        public void Application_ProgressChanged(object sender, Autodesk.Revit.DB.Events.ProgressChangedEventArgs e) {
            ExecuteEventHooks(EventType.Application_ProgressChanged, sender, e);
        }

#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017)
        public void Application_LinkedResourceOpening(object sender, Autodesk.Revit.DB.Events.LinkedResourceOpeningEventArgs e) {
            ExecuteEventHooks(EventType.Application_LinkedResourceOpening, sender, e);
        }

        public void Application_LinkedResourceOpened(object sender, Autodesk.Revit.DB.Events.LinkedResourceOpenedEventArgs e) {
            ExecuteEventHooks(EventType.Application_LinkedResourceOpened, sender, e);
        }
#endif

        public void Application_FileImporting(object sender, Autodesk.Revit.DB.Events.FileImportingEventArgs e) {
            ExecuteEventHooks(EventType.Application_FileImporting, sender, e);
        }

        public void Application_FileImported(object sender, Autodesk.Revit.DB.Events.FileImportedEventArgs e) {
            ExecuteEventHooks(EventType.Application_FileImported, sender, e);
        }

        public void Application_FileExporting(object sender, Autodesk.Revit.DB.Events.FileExportingEventArgs e) {
            ExecuteEventHooks(EventType.Application_FileExporting, sender, e);
        }

        public void Application_FileExported(object sender, Autodesk.Revit.DB.Events.FileExportedEventArgs e) {
            ExecuteEventHooks(EventType.Application_FileExported, sender, e);
        }

#if !(REVIT2013 || REVIT2014)
        public void Application_FamilyLoadingIntoDocument(object sender, Autodesk.Revit.DB.Events.FamilyLoadingIntoDocumentEventArgs e) {
            ExecuteEventHooks(EventType.Application_FamilyLoadingIntoDocument, sender, e);
        }

        public void Application_FamilyLoadedIntoDocument(object sender, Autodesk.Revit.DB.Events.FamilyLoadedIntoDocumentEventArgs e) {
            ExecuteEventHooks(EventType.Application_FamilyLoadedIntoDocument, sender, e);
        }
#endif

        public void Application_FailuresProcessing(object sender, Autodesk.Revit.DB.Events.FailuresProcessingEventArgs e) {
            ExecuteEventHooks(EventType.Application_FailuresProcessing, sender, e);
        }

#if !(REVIT2013 || REVIT2014)
        public void Application_ElementTypeDuplicating(object sender, Autodesk.Revit.DB.Events.ElementTypeDuplicatingEventArgs e) {
            ExecuteEventHooks(EventType.Application_ElementTypeDuplicating, sender, e);
        }

        public void Application_ElementTypeDuplicated(object sender, Autodesk.Revit.DB.Events.ElementTypeDuplicatedEventArgs e) {
            ExecuteEventHooks(EventType.Application_ElementTypeDuplicated, sender, e);
        }
        public void Application_DocumentWorksharingEnabled(object sender, Autodesk.Revit.DB.Events.DocumentWorksharingEnabledEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentWorksharingEnabled, sender, e);
        }
#endif

        public void Application_DocumentSynchronizingWithCentral(object sender, Autodesk.Revit.DB.Events.DocumentSynchronizingWithCentralEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentSynchronizingWithCentral, sender, e);
        }

        public void Application_DocumentSynchronizedWithCentral(object sender, Autodesk.Revit.DB.Events.DocumentSynchronizedWithCentralEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentSynchronizedWithCentral, sender, e);
        }

        public void Application_DocumentSavingAs(object sender, Autodesk.Revit.DB.Events.DocumentSavingAsEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentSavingAs, sender, e);
        }

        public void Application_DocumentSavedAs(object sender, Autodesk.Revit.DB.Events.DocumentSavedAsEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentSavedAs, sender, e);
        }

        public void Application_DocumentSaving(object sender, Autodesk.Revit.DB.Events.DocumentSavingEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentSaving, sender, e);
        }

        public void Application_DocumentSaved(object sender, Autodesk.Revit.DB.Events.DocumentSavedEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentSaved, sender, e);
        }

        public void Application_DocumentPrinting(object sender, Autodesk.Revit.DB.Events.DocumentPrintingEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentPrinting, sender, e);
        }

        public void Application_DocumentPrinted(object sender, Autodesk.Revit.DB.Events.DocumentPrintedEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentPrinted, sender, e);
        }

        public void Application_DocumentOpening(object sender, Autodesk.Revit.DB.Events.DocumentOpeningEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentOpening, sender, e);
        }

        public void Application_DocumentOpened(object sender, Autodesk.Revit.DB.Events.DocumentOpenedEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentOpened, sender, e);
        }

        public void Application_DocumentCreating(object sender, Autodesk.Revit.DB.Events.DocumentCreatingEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentCreating, sender, e);
        }

        public void Application_DocumentCreated(object sender, Autodesk.Revit.DB.Events.DocumentCreatedEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentCreated, sender, e);
        }

        public void Application_DocumentClosing(object sender, Autodesk.Revit.DB.Events.DocumentClosingEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentClosing, sender, e);
        }

        public void Application_DocumentClosed(object sender, Autodesk.Revit.DB.Events.DocumentClosedEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentClosed, sender, e);
        }

        public void Application_DocumentChanged(object sender, Autodesk.Revit.DB.Events.DocumentChangedEventArgs e) {
            ExecuteEventHooks(EventType.Application_DocumentChanged, sender, e);
        }

        public void Application_ApplicationInitialized(object sender, Autodesk.Revit.DB.Events.ApplicationInitializedEventArgs e) {
            ExecuteEventHooks(EventType.Application_ApplicationInitialized, sender, e);
        }
    }
}
