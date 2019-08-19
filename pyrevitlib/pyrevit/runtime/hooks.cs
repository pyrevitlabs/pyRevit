using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;

using Autodesk.Revit.UI;
using Autodesk.Revit.DB;

using pyRevitLabs.NLog;

namespace PyRevitLabs.PyRevit.Runtime {
    public class EventHook {
        public const string id_key = "id";
        public const string name_key = "name";
        public const string script_key = "script";
        public const string syspaths_key = "syspaths";
        public const string extension_name_key = "extension_name";

        public string EventName;
        public string Script;
        public string[] SearchPaths;
        public string ExtensionName;
        public string UniqueId;

        public EventType? EventType {
            get {
                return EventUtils.GetEventType(EventName);
            }
        }

        public EventHook(string uniqueId, string eventName, string scriptPath, string syspaths, string extension_name) {
            UniqueId = uniqueId;
            EventName = eventName;
            Script = scriptPath;
            SearchPaths = syspaths.Split(Path.PathSeparator);
            ExtensionName = extension_name;
        }

        public override int GetHashCode() {
            return UniqueId.GetHashCode();
        }

        public static bool IsValid(string eventName) {
            return EventUtils.GetEventType(eventName) != null;
        }
    }

    public class PyRevitHooks : IEventTypeHandler {
        static Logger logger = LogManager.GetCurrentClassLogger();

        public string HandlerId;

        public PyRevitHooks(string handlerId) {
            if (handlerId == null)
                handlerId = Guid.NewGuid().ToString();
            HandlerId = handlerId;
        }

        public static int Execute(EventHook eventHook, object eventSender, object eventArgs) {
            // 1: ----------------------------------------------------------------------------------------------------
            #region Setup pyRevit Command Runtime
            var pyrvtScript =
                new ScriptRuntime(
                    cmdData: null,
                    elements: new ElementSet(),
                    scriptData: new ScriptData {
                        ScriptPath = eventHook.Script,
                        ConfigScriptPath = eventHook.Script,
                        CommandUniqueId = eventHook.UniqueId,
                        CommandName = string.Format("hooks.{0}", Path.GetFileNameWithoutExtension(eventHook.Script)),
                        CommandBundle = string.Format("{0}.hooks", eventHook.ExtensionName),
                        CommandExtension = eventHook.ExtensionName,
                        HelpSource = "",
                    },
                    searchpaths: eventHook.SearchPaths,
                    arguments: new string[] { },
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
            return ScriptExecutor.ExecuteScript(ref pyrvtScript);

            // TODO: log results into command execution telemetry?
            #endregion
        }

        public static List<EventHook> GetAllEventHooks() {
            var env = new EnvDictionary();
            var eventHooks = new List<EventHook>();
            foreach (KeyValuePair<string, Dictionary<string, string>> eventHookInfo in env.EventHooks) {
                var eventName = eventHookInfo.Value[EventHook.name_key];
                if (EventHook.IsValid(eventName)) {
                    eventHooks.Add(new EventHook(
                        uniqueId: eventHookInfo.Value[EventHook.id_key],
                        eventName: eventName,
                        scriptPath: eventHookInfo.Value[EventHook.script_key],
                        syspaths: eventHookInfo.Value[EventHook.syspaths_key],
                        extension_name: eventHookInfo.Value[EventHook.extension_name_key]
                    ));
                }
            }
            return eventHooks;
        }

        public static List<EventHook> GetEventHooks(EventType eventType) {
            var eventName = EventUtils.GetEventName(eventType);
            return GetAllEventHooks().Where(x => x.EventName == eventName).ToList();
        }

        public void ExecuteEventHooks(EventType eventType, object eventSender, object eventArgs) {
            try {
                //var logMsg = string.Format("Executing event hook {0}", eventType.ToString());
                foreach (EventHook eventHook in GetEventHooks(eventType))
                    Execute(eventHook: eventHook,
                            eventSender: eventSender,
                            eventArgs: eventArgs);
            }
            catch {
                //var logMsg = string.Join(Environment.NewLine, ex.Message, ex.StackTrace, SessionUUID);
            }
        }

        public void ActivateEventType(UIApplication uiApp, EventType eventType) {
            try {
                // remove first
                EventUtils.ToggleHooks<PyRevitHooks>(this, uiApp, eventType, toggle_on: false);
                // then add again
                EventUtils.ToggleHooks<PyRevitHooks>(this, uiApp, eventType);
            }
            catch (NotSupportedFeatureException) {
                logger.Debug(string.Format("Hook type {0} not supported under this Revit version. Skipped.",
                                           eventType.ToString()));
            }
            catch (Exception) {
                logger.Debug(string.Format("Failed registering hook type {0}", eventType.ToString()));
            }
        }

        public void DeactivateEventType(UIApplication uiApp, EventType eventType) {
            try {
                EventUtils.ToggleHooks<PyRevitHooks>(this, uiApp, eventType, toggle_on: false);
            }
            catch (NotSupportedFeatureException) {
                logger.Debug(string.Format("Hook type {0} not supported under this Revit version. Skipped.",
                                           eventType.ToString()));
            }
            catch (Exception) {
                logger.Debug(string.Format("Failed unregistering hook type {0}", eventType.ToString()));
            }
        }

        public void RegisterHook(string uniqueId, string eventName, string scriptPath, string[] searchPaths, string extensionName) {
            if (EventHook.IsValid(eventName)) {
                var env = new EnvDictionary();
                env.EventHooks[uniqueId] = new Dictionary<string, string> {
                    { EventHook.id_key, uniqueId },
                    { EventHook.name_key, eventName },
                    { EventHook.script_key, scriptPath },
                    { EventHook.syspaths_key, string.Join(Path.PathSeparator.ToString(), searchPaths) },
                    { EventHook.extension_name_key, extensionName },
                };
            }
        }

        public void UnRegisterHook(string uniqueId) {
            var env = new EnvDictionary();
            if (env.EventHooks.ContainsKey(uniqueId))
                env.EventHooks.Remove(uniqueId);
        }

        public void UnRegisterAllHooks(UIApplication uiApp) {
            var env = new EnvDictionary();
            env.ResetEventHooks();
        }

        public void ActivateEventHooks(UIApplication uiApp) {
            foreach (var eventHook in GetAllEventHooks())
                if (eventHook.EventType != null)
                    ActivateEventType(uiApp, (EventType)eventHook.EventType);
        }

        public void DeactivateEventHooks(UIApplication uiApp) {
            foreach (var eventHook in GetAllEventHooks())
                if (eventHook.EventType != null)
                    DeactivateEventType(uiApp, (EventType)eventHook.EventType);
        }

        public void DeactivateAllEventHooks(UIApplication uiApp) {
            foreach (EventType eventType in EventUtils.GetSupportedEventTypes())
                DeactivateEventType(uiApp, eventType);
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
