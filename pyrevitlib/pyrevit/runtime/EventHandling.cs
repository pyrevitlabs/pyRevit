using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Controls;
using System.Windows.Media;
using System.Reflection;
using MEDIA = System.Windows.Media;

using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Events;
using Autodesk.Revit.UI;
using Autodesk.Revit.UI.Events;

using UIFramework;

#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017 || REVIT2018)
using Xceed.Wpf.AvalonDock.Layout;
using Xceed.Wpf.AvalonDock.Controls;
#endif

using pyRevitLabs.NLog;
using pyRevitLabs.PyRevit;

namespace PyRevitLabs.PyRevit.Runtime {
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

        // Autodesk.Revit.UI.AddInCommandBinding Events
        AddInCommandBinding_BeforeExecuted,
        AddInCommandBinding_CanExecute,
        AddInCommandBinding_Executed,

        // pyRevit-defined events
        Application_JournalUpdated,
        Application_JournalCommandExecuted,
        Application_IUpdater,
    }

    public interface IEventTypeHandler {
#if !(REVIT2013)
        void AddInCommandBinding_BeforeExecuted(object sender, BeforeExecutedEventArgs e);
#endif

#if !(REVIT2013 || REVIT2014)
        void Application_FamilyLoadingIntoDocument(object sender, FamilyLoadingIntoDocumentEventArgs e);
        void Application_FamilyLoadedIntoDocument(object sender, FamilyLoadedIntoDocumentEventArgs e);
        void Application_ElementTypeDuplicating(object sender, ElementTypeDuplicatingEventArgs e);
        void Application_ElementTypeDuplicated(object sender, ElementTypeDuplicatedEventArgs e);
        void Application_DocumentWorksharingEnabled(object sender, DocumentWorksharingEnabledEventArgs e);
        void UIApplication_DockableFrameVisibilityChanged(object sender, DockableFrameVisibilityChangedEventArgs e);
        void UIApplication_DockableFrameFocusChanged(object sender, DockableFrameFocusChangedEventArgs e);
#endif

#if !(REVIT2013 || REVIT2014 || REVIT2015)
#endif

#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016)
        void UIApplication_FabricationPartBrowserChanged(object sender, FabricationPartBrowserChangedEventArgs e);
#endif

#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017)
        void Application_ViewExporting(object sender, ViewExportingEventArgs e);
        void Application_ViewExported(object sender, ViewExportedEventArgs e);
        void Application_LinkedResourceOpening(object sender, LinkedResourceOpeningEventArgs e);
        void Application_LinkedResourceOpened(object sender, LinkedResourceOpenedEventArgs e);
        void Application_WorksharedOperationProgressChanged(object sender, WorksharedOperationProgressChangedEventArgs e);
        void UIApplication_TransferringProjectStandards(object sender, TransferringProjectStandardsEventArgs e);
        void UIApplication_TransferredProjectStandards(object sender, TransferredProjectStandardsEventArgs e);
#endif

#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017 || REVIT2018)
        void UIApplication_FormulaEditing(object sender, FormulaEditingEventArgs e);
#endif

        void Application_ViewPrinting(object sender, ViewPrintingEventArgs e);
        void Application_ViewPrinted(object sender, ViewPrintedEventArgs e);
        void Application_ProgressChanged(object sender, ProgressChangedEventArgs e);
        void Application_FileImporting(object sender, FileImportingEventArgs e);
        void Application_FileImported(object sender, FileImportedEventArgs e);
        void Application_FileExporting(object sender, FileExportingEventArgs e);
        void Application_FileExported(object sender, FileExportedEventArgs e);
        void Application_FailuresProcessing(object sender, FailuresProcessingEventArgs e);
        void Application_DocumentSynchronizingWithCentral(object sender, DocumentSynchronizingWithCentralEventArgs e);
        void Application_DocumentSynchronizedWithCentral(object sender, DocumentSynchronizedWithCentralEventArgs e);
        void Application_DocumentSavingAs(object sender, DocumentSavingAsEventArgs e);
        void Application_DocumentSavedAs(object sender, DocumentSavedAsEventArgs e);
        void Application_DocumentSaving(object sender, DocumentSavingEventArgs e);
        void Application_DocumentSaved(object sender, DocumentSavedEventArgs e);
        void Application_DocumentPrinting(object sender, DocumentPrintingEventArgs e);
        void Application_DocumentPrinted(object sender, DocumentPrintedEventArgs e);
        void Application_DocumentOpening(object sender, DocumentOpeningEventArgs e);
        void Application_DocumentOpened(object sender, DocumentOpenedEventArgs e);
        void Application_DocumentCreating(object sender, DocumentCreatingEventArgs e);
        void Application_DocumentCreated(object sender, DocumentCreatedEventArgs e);
        void Application_DocumentClosing(object sender, DocumentClosingEventArgs e);
        void Application_DocumentClosed(object sender, DocumentClosedEventArgs e);
        void Application_DocumentChanged(object sender, DocumentChangedEventArgs e);
        void Application_ApplicationInitialized(object sender, ApplicationInitializedEventArgs e);
        void UIApplication_ViewActivating(object sender, ViewActivatingEventArgs e);
        void UIApplication_ViewActivated(object sender, ViewActivatedEventArgs e);
        void UIApplication_Idling(object sender, IdlingEventArgs e);
        void UIApplication_DisplayingOptionsDialog(object sender, DisplayingOptionsDialogEventArgs e);
        void UIApplication_ApplicationClosing(object sender, ApplicationClosingEventArgs e);
        void UIApplication_DialogBoxShowing(object sender, DialogBoxShowingEventArgs e);
        void AddInCommandBinding_CanExecute(object sender, CanExecuteEventArgs e);
        void AddInCommandBinding_Executed(object sender, ExecutedEventArgs e);

        // custom events. These are called from a non-main thread
        void Application_JournalUpdated(object sender, JournalUpdateArgs e);
        void Application_JournalCommandExecuted(object sender, CommandExecutedArgs e);

        void Application_IUpdater(object sender, UpdaterData d);
    }

    public static class EventUtils {
        private static JournalListener journalListener = null;
        private static UpdaterListener updaterListener = null;

        private static Dictionary<EventType, string> eventNames = new Dictionary<EventType, string> {
            { EventType.UIApplication_ApplicationClosing,  "app-closing" },
            { EventType.UIApplication_Idling, "app-idling" },
            { EventType.Application_ApplicationInitialized, "app-init" },
            { EventType.UIApplication_DialogBoxShowing, "dialog-showing" },
            { EventType.Application_DocumentChanged, "doc-changed" },
            { EventType.Application_DocumentClosed, "doc-closed" },
            { EventType.Application_DocumentClosing, "doc-closing" },
            { EventType.Application_DocumentCreated, "doc-created" },
            { EventType.Application_DocumentCreating, "doc-creating" },
            { EventType.Application_DocumentOpened, "doc-opened" },
            { EventType.Application_DocumentOpening, "doc-opening" },
            { EventType.Application_DocumentPrinted, "doc-printed" },
            { EventType.Application_DocumentPrinting, "doc-printing" },
            { EventType.Application_DocumentSavedAs, "doc-saved-as" },
            { EventType.Application_DocumentSaved, "doc-saved" },
            { EventType.Application_DocumentSavingAs, "doc-saving-as" },
            { EventType.Application_DocumentSaving, "doc-saving" },
            { EventType.Application_DocumentSynchronizedWithCentral, "doc-synced" },
            { EventType.Application_DocumentSynchronizingWithCentral, "doc-syncing" },
            { EventType.Application_DocumentWorksharingEnabled, "doc-worksharing-enabled" },
            { EventType.UIApplication_DockableFrameFocusChanged, "dock-focus-changed" },
            { EventType.UIApplication_DockableFrameVisibilityChanged, "dock-visibility-changed" },
            { EventType.UIApplication_FabricationPartBrowserChanged, "fabparts-browser-changed" },
            { EventType.Application_FailuresProcessing, "failure-processing" },
            { EventType.Application_FamilyLoadedIntoDocument, "family-loaded" },
            { EventType.Application_FamilyLoadingIntoDocument, "family-loading" },
            { EventType.Application_FileExported, "file-exported" },
            { EventType.Application_FileExporting, "file-exporting" },
            { EventType.Application_FileImported, "file-imported" },
            { EventType.Application_FileImporting, "file-importing" },
            { EventType.UIApplication_FormulaEditing, "formula-editing" },
            { EventType.Application_LinkedResourceOpened, "link-opened" },
            { EventType.Application_LinkedResourceOpening, "link-opening" },
            { EventType.UIApplication_DisplayingOptionsDialog, "options-showing" },
            { EventType.Application_ProgressChanged, "progress-changed" },
            { EventType.UIApplication_TransferredProjectStandards, "transferred-project-standards" },
            { EventType.UIApplication_TransferringProjectStandards, "transferring-project-standards" },
            { EventType.Application_ElementTypeDuplicated, "type-duplicated" },
            { EventType.Application_ElementTypeDuplicating, "type-duplicating" },
            { EventType.UIApplication_ViewActivated, "view-activated" },
            { EventType.UIApplication_ViewActivating, "view-activating" },
            { EventType.Application_ViewExported, "view-exported" },
            { EventType.Application_ViewExporting, "view-exporting" },
            { EventType.Application_ViewPrinted, "view-printed" },
            { EventType.Application_ViewPrinting, "view-printing" },
            { EventType.Application_WorksharedOperationProgressChanged, "worksharing-ops-progress-changed" },
            { EventType.AddInCommandBinding_BeforeExecuted, "command-before-exec" },
            { EventType.AddInCommandBinding_CanExecute, "command-can-exec" },
            { EventType.AddInCommandBinding_Executed, "command-exec" },
            { EventType.Application_JournalUpdated, "journal-updated" },
            { EventType.Application_JournalCommandExecuted, "journal-command-exec" },
            { EventType.Application_IUpdater, "doc-updater" },
        };

        public static string GetEventName(EventType eventType) {
            string eventName = null;
            eventNames.TryGetValue(eventType, out eventName);
            return eventName;
        }

        public static EventType? GetEventType(string eventName) {
            try {
                return eventNames.First(x => x.Value == eventName).Key;
            }
            catch {
                return null;
            }
        }

        public static Array GetAllEventTypes() {
            return Enum.GetValues(typeof(EventType));
        }

        public static List<EventType> GetSupportedEventTypes() {
            var supTypes = new List<EventType>();
            var supportedHandlers = typeof(IEventTypeHandler).GetMembers().Select(m => m.Name);
            foreach (EventType eventType in Enum.GetValues(typeof(EventType)))
                if (supportedHandlers.Contains(eventType.ToString()))
                    supTypes.Add(eventType);
            return supTypes;
        }

        public static AddInCommandBinding GetCommandBinding(UIApplication uiApp, string commandName) {
            try {
                RevitCommandId commandId = RevitCommandId.LookupCommandId(commandName);
                if (commandId != null)
                    return uiApp.CreateAddInCommandBinding(commandId);
            }
            catch { }
            return null;
        }

        private static void ActivateJournalListener(UIApplication uiapp) {
            if (journalListener == null) {
                journalListener = new JournalListener(uiapp);
                journalListener.Start();
            }
        }

        private static void DeactivateJournalListener(UIApplication uiapp) {
            // shut down the listener only if it is not firing any events
            if (journalListener != null && !(journalListener.JournalUpdateEvents || journalListener.JournalCommandExecutedEvents)) {
                journalListener.Stop();
                journalListener = null;
            }
        }

        private static void ActivateUpdaterListener() {
            if (updaterListener == null) {
                updaterListener = new UpdaterListener();
                UpdaterRegistry.RegisterUpdater(updaterListener);
                UpdaterRegistry.AddTrigger(
                    updaterListener.GetUpdaterId(),
                    new ElementCategoryFilter(BuiltInCategory.INVALID, inverted: true),
                    Element.GetChangeTypeAny());
            }
        }

        private static void DeactivateUpdaterListener() {
            // shut down the listener only if it is not firing any events
            if (updaterListener != null) {
                var updaterId = updaterListener.GetUpdaterId();
                UpdaterRegistry.RemoveAllTriggers(updaterId);
                UpdaterRegistry.UnregisterUpdater(updaterId);
                updaterListener = null;
            }
        }

#if (!REVIT2013)
        public static List<AddInCommandBinding> GetAllCommandBindings(UIApplication uiApp) {
            var cmdBindings = new List<AddInCommandBinding>();
            foreach (PostableCommand postableCommand in Enum.GetValues(typeof(PostableCommand))) {
                try {
                    RevitCommandId commandId = RevitCommandId.LookupPostableCommandId(postableCommand);
                    if (commandId != null)
                        cmdBindings.Add(
                            uiApp.CreateAddInCommandBinding(commandId)
                            );
                }
                catch { }
            }
            return cmdBindings;
        }
#endif

        public static void ToggleHooks<T>(T hndlr, UIApplication uiApp, EventType eventType, string eventTarget = null, bool toggle_on = true) where T : IEventTypeHandler {
            AddInCommandBinding cmdBinding;

            switch (eventType) {
                case EventType.Application_ApplicationInitialized:
                    if (toggle_on)
                        uiApp.Application.ApplicationInitialized += hndlr.Application_ApplicationInitialized;
                    else
                        uiApp.Application.ApplicationInitialized -= hndlr.Application_ApplicationInitialized;
                    break;

                case EventType.Application_DocumentChanged:
                    if (toggle_on)
                        uiApp.Application.DocumentChanged += hndlr.Application_DocumentChanged;
                    else
                        uiApp.Application.DocumentChanged -= hndlr.Application_DocumentChanged;
                    break;

                case EventType.Application_DocumentClosed:
                    if (toggle_on)
                        uiApp.Application.DocumentClosed += hndlr.Application_DocumentClosed;
                    else
                        uiApp.Application.DocumentClosed -= hndlr.Application_DocumentClosed;
                    break;

                case EventType.Application_DocumentClosing:
                    if (toggle_on)
                        uiApp.Application.DocumentClosing += hndlr.Application_DocumentClosing;
                    else
                        uiApp.Application.DocumentClosing -= hndlr.Application_DocumentClosing;
                    break;

                case EventType.Application_DocumentCreated:
                    if (toggle_on)
                        uiApp.Application.DocumentCreated += hndlr.Application_DocumentCreated;
                    else
                        uiApp.Application.DocumentCreated -= hndlr.Application_DocumentCreated;
                    break;

                case EventType.Application_DocumentCreating:
                    if (toggle_on)
                        uiApp.Application.DocumentCreating += hndlr.Application_DocumentCreating;
                    else
                        uiApp.Application.DocumentCreating -= hndlr.Application_DocumentCreating;
                    break;

                case EventType.Application_DocumentOpened:
                    if (toggle_on)
                        uiApp.Application.DocumentOpened += hndlr.Application_DocumentOpened;
                    else
                        uiApp.Application.DocumentOpened -= hndlr.Application_DocumentOpened;
                    break;

                case EventType.Application_DocumentOpening:
                    if (toggle_on)
                        uiApp.Application.DocumentOpening += hndlr.Application_DocumentOpening;
                    else
                        uiApp.Application.DocumentOpening -= hndlr.Application_DocumentOpening;
                    break;

                case EventType.Application_DocumentPrinted:
                    if (toggle_on)
                        uiApp.Application.DocumentPrinted += hndlr.Application_DocumentPrinted;
                    else
                        uiApp.Application.DocumentPrinted -= hndlr.Application_DocumentPrinted;
                    break;

                case EventType.Application_DocumentPrinting:
                    if (toggle_on)
                        uiApp.Application.DocumentPrinting += hndlr.Application_DocumentPrinting;
                    else
                        uiApp.Application.DocumentPrinting -= hndlr.Application_DocumentPrinting;
                    break;

                case EventType.Application_DocumentSaved:
                    if (toggle_on)
                        uiApp.Application.DocumentSaved += hndlr.Application_DocumentSaved;
                    else
                        uiApp.Application.DocumentSaved -= hndlr.Application_DocumentSaved;
                    break;

                case EventType.Application_DocumentSaving:
                    if (toggle_on)
                        uiApp.Application.DocumentSaving += hndlr.Application_DocumentSaving;
                    else
                        uiApp.Application.DocumentSaving -= hndlr.Application_DocumentSaving;
                    break;

                case EventType.Application_DocumentSavedAs:
                    if (toggle_on)
                        uiApp.Application.DocumentSavedAs += hndlr.Application_DocumentSavedAs;
                    else
                        uiApp.Application.DocumentSavedAs -= hndlr.Application_DocumentSavedAs;
                    break;

                case EventType.Application_DocumentSavingAs:
                    if (toggle_on)
                        uiApp.Application.DocumentSavingAs += hndlr.Application_DocumentSavingAs;
                    else
                        uiApp.Application.DocumentSavingAs -= hndlr.Application_DocumentSavingAs;
                    break;

                case EventType.Application_DocumentSynchronizedWithCentral:
                    if (toggle_on)
                        uiApp.Application.DocumentSynchronizedWithCentral += hndlr.Application_DocumentSynchronizedWithCentral;
                    else
                        uiApp.Application.DocumentSynchronizedWithCentral -= hndlr.Application_DocumentSynchronizedWithCentral;
                    break;

                case EventType.Application_DocumentSynchronizingWithCentral:
                    if (toggle_on)
                        uiApp.Application.DocumentSynchronizingWithCentral += hndlr.Application_DocumentSynchronizingWithCentral;
                    else
                        uiApp.Application.DocumentSynchronizingWithCentral -= hndlr.Application_DocumentSynchronizingWithCentral;
                    break;

                case EventType.Application_DocumentWorksharingEnabled:
#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016)
                    if (toggle_on)
                        uiApp.Application.DocumentWorksharingEnabled += hndlr.Application_DocumentWorksharingEnabled;
                    else
                        uiApp.Application.DocumentWorksharingEnabled -= hndlr.Application_DocumentWorksharingEnabled;
                    break;
#else
                    throw new NotSupportedFeatureException();
#endif

                case EventType.Application_ElementTypeDuplicated:
#if !(REVIT2013 || REVIT2014)
                    if (toggle_on)
                        uiApp.Application.ElementTypeDuplicated += hndlr.Application_ElementTypeDuplicated;
                    else
                        uiApp.Application.ElementTypeDuplicated -= hndlr.Application_ElementTypeDuplicated;
                    break;
#else
                    throw new NotSupportedFeatureException();
#endif

                case EventType.Application_ElementTypeDuplicating:
#if !(REVIT2013 || REVIT2014)
                    if (toggle_on)
                        uiApp.Application.ElementTypeDuplicating += hndlr.Application_ElementTypeDuplicating;
                    else
                        uiApp.Application.ElementTypeDuplicating -= hndlr.Application_ElementTypeDuplicating;
                    break;
#else
                    throw new NotSupportedFeatureException();
#endif

                case EventType.Application_FailuresProcessing:
                    if (toggle_on)
                        uiApp.Application.FailuresProcessing += hndlr.Application_FailuresProcessing;
                    else
                        uiApp.Application.FailuresProcessing -= hndlr.Application_FailuresProcessing;
                    break;

                case EventType.Application_FamilyLoadedIntoDocument:
#if !(REVIT2013 || REVIT2014)
                    if (toggle_on)
                        uiApp.Application.FamilyLoadedIntoDocument += hndlr.Application_FamilyLoadedIntoDocument;
                    else
                        uiApp.Application.FamilyLoadedIntoDocument -= hndlr.Application_FamilyLoadedIntoDocument;
                    break;
#else
                    throw new NotSupportedFeatureException();
#endif

                case EventType.Application_FamilyLoadingIntoDocument:
#if !(REVIT2013 || REVIT2014)
                    if (toggle_on)
                        uiApp.Application.FamilyLoadingIntoDocument += hndlr.Application_FamilyLoadingIntoDocument;
                    else
                        uiApp.Application.FamilyLoadingIntoDocument -= hndlr.Application_FamilyLoadingIntoDocument;
                    break;
#else
                    throw new NotSupportedFeatureException();
#endif

                case EventType.Application_FileExported:
                    if (toggle_on)
                        uiApp.Application.FileExported += hndlr.Application_FileExported;
                    else
                        uiApp.Application.FileExported -= hndlr.Application_FileExported;
                    break;

                case EventType.Application_FileExporting:
                    if (toggle_on)
                        uiApp.Application.FileExporting += hndlr.Application_FileExporting;
                    else
                        uiApp.Application.FileExporting -= hndlr.Application_FileExporting;
                    break;

                case EventType.Application_FileImported:
                    if (toggle_on)
                        uiApp.Application.FileImported += hndlr.Application_FileImported;
                    else
                        uiApp.Application.FileImported -= hndlr.Application_FileImported;
                    break;

                case EventType.Application_FileImporting:
                    if (toggle_on)
                        uiApp.Application.FileImporting += hndlr.Application_FileImporting;
                    else
                        uiApp.Application.FileImporting -= hndlr.Application_FileImporting;
                    break;

                case EventType.Application_LinkedResourceOpened:
#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017)
                    if (toggle_on)
                        uiApp.Application.LinkedResourceOpened += hndlr.Application_LinkedResourceOpened;
                    else
                        uiApp.Application.LinkedResourceOpened -= hndlr.Application_LinkedResourceOpened;
                    break;
#else
                    throw new NotSupportedFeatureException();
#endif

                case EventType.Application_LinkedResourceOpening:
#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017)
                    if (toggle_on)
                        uiApp.Application.LinkedResourceOpening += hndlr.Application_LinkedResourceOpening;
                    else
                        uiApp.Application.LinkedResourceOpening -= hndlr.Application_LinkedResourceOpening;
                    break;
#else
                    throw new NotSupportedFeatureException();
#endif

                case EventType.Application_ProgressChanged:
                    if (toggle_on)
                        uiApp.Application.ProgressChanged += hndlr.Application_ProgressChanged;
                    else
                        uiApp.Application.ProgressChanged -= hndlr.Application_ProgressChanged;
                    break;

                case EventType.Application_ViewExported:
#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017)
                    if (toggle_on)
                        uiApp.Application.ViewExported += hndlr.Application_ViewExported;
                    else
                        uiApp.Application.ViewExported -= hndlr.Application_ViewExported;
                    break;
#else
                    throw new NotSupportedFeatureException();
#endif

                case EventType.Application_ViewExporting:
#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017)
                    if (toggle_on)
                        uiApp.Application.ViewExporting += hndlr.Application_ViewExporting;
                    else
                        uiApp.Application.ViewExporting -= hndlr.Application_ViewExporting;
                    break;
#else
                    throw new NotSupportedFeatureException();
#endif

                case EventType.Application_ViewPrinted:
                    if (toggle_on)
                        uiApp.Application.ViewPrinted += hndlr.Application_ViewPrinted;
                    else
                        uiApp.Application.ViewPrinted -= hndlr.Application_ViewPrinted;
                    break;

                case EventType.Application_ViewPrinting:
                    if (toggle_on)
                        uiApp.Application.ViewPrinting += hndlr.Application_ViewPrinting;
                    else
                        uiApp.Application.ViewPrinting -= hndlr.Application_ViewPrinting;
                    break;

                case EventType.Application_WorksharedOperationProgressChanged:
#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017)
                    if (toggle_on)
                        uiApp.Application.WorksharedOperationProgressChanged += hndlr.Application_WorksharedOperationProgressChanged;
                    else
                        uiApp.Application.WorksharedOperationProgressChanged -= hndlr.Application_WorksharedOperationProgressChanged;
                    break;
#else
                    throw new NotSupportedFeatureException();
#endif

                case EventType.UIApplication_ApplicationClosing:
                    if (toggle_on)
                        uiApp.ApplicationClosing += hndlr.UIApplication_ApplicationClosing;
                    else
                        uiApp.ApplicationClosing -= hndlr.UIApplication_ApplicationClosing;
                    break;

                case EventType.UIApplication_DialogBoxShowing:
#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016)
                    if (toggle_on)
                        uiApp.DialogBoxShowing += hndlr.UIApplication_DialogBoxShowing;
                    else
                        uiApp.DialogBoxShowing -= hndlr.UIApplication_DialogBoxShowing;
                    break;
#else
                    throw new NotSupportedFeatureException();
#endif
                case EventType.UIApplication_DisplayingOptionsDialog:
                    if (toggle_on)
                        uiApp.DisplayingOptionsDialog += hndlr.UIApplication_DisplayingOptionsDialog;
                    else
                        uiApp.DisplayingOptionsDialog -= hndlr.UIApplication_DisplayingOptionsDialog;
                    break;

                case EventType.UIApplication_DockableFrameFocusChanged:
#if !(REVIT2013 || REVIT2014)
                    if (toggle_on)
                        uiApp.DockableFrameFocusChanged += hndlr.UIApplication_DockableFrameFocusChanged;
                    else
                        uiApp.DockableFrameFocusChanged -= hndlr.UIApplication_DockableFrameFocusChanged;
                    break;
#else
                    throw new NotSupportedFeatureException();
#endif

                case EventType.UIApplication_DockableFrameVisibilityChanged:
#if !(REVIT2013 || REVIT2014)
                    if (toggle_on)
                        uiApp.DockableFrameVisibilityChanged += hndlr.UIApplication_DockableFrameVisibilityChanged;
                    else
                        uiApp.DockableFrameVisibilityChanged -= hndlr.UIApplication_DockableFrameVisibilityChanged;
                    break;
#else
                    throw new NotSupportedFeatureException();
#endif

                case EventType.UIApplication_FabricationPartBrowserChanged:
#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016)
                    if (toggle_on)
                        uiApp.FabricationPartBrowserChanged += hndlr.UIApplication_FabricationPartBrowserChanged;
                    else
                        uiApp.FabricationPartBrowserChanged -= hndlr.UIApplication_FabricationPartBrowserChanged;
                    break;
#else
                    throw new NotSupportedFeatureException();
#endif

                case EventType.UIApplication_FormulaEditing:
#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017 || REVIT2018)
                    if (toggle_on)
                        uiApp.FormulaEditing += hndlr.UIApplication_FormulaEditing;
                    else
                        uiApp.FormulaEditing -= hndlr.UIApplication_FormulaEditing;
                    break;
#else
                    throw new NotSupportedFeatureException();
#endif

                case EventType.UIApplication_Idling:
                    if (toggle_on)
                        uiApp.Idling += hndlr.UIApplication_Idling;
                    else
                        uiApp.Idling -= hndlr.UIApplication_Idling;
                    break;


                case EventType.UIApplication_TransferredProjectStandards:
#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017)
                    if (toggle_on)
                        uiApp.TransferredProjectStandards += hndlr.UIApplication_TransferredProjectStandards;
                    else
                        uiApp.TransferredProjectStandards -= hndlr.UIApplication_TransferredProjectStandards;
                    break;
#else
                    throw new NotSupportedFeatureException();
#endif

                case EventType.UIApplication_TransferringProjectStandards:
#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017)
                    if (toggle_on)
                        uiApp.TransferringProjectStandards += hndlr.UIApplication_TransferringProjectStandards;
                    else
                        uiApp.TransferringProjectStandards -= hndlr.UIApplication_TransferringProjectStandards;
                    break;
#else
                    throw new NotSupportedFeatureException();
#endif

                case EventType.UIApplication_ViewActivated:
                    if (toggle_on)
                        uiApp.ViewActivated += hndlr.UIApplication_ViewActivated;
                    else
                        uiApp.ViewActivated -= hndlr.UIApplication_ViewActivated;
                    break;

                case EventType.UIApplication_ViewActivating:
                    if (toggle_on)
                        uiApp.ViewActivating += hndlr.UIApplication_ViewActivating;
                    else
                        uiApp.ViewActivating -= hndlr.UIApplication_ViewActivating;
                    break;

#if !(REVIT2013)
                case EventType.AddInCommandBinding_BeforeExecuted:
                    if (eventTarget == null) {
                        // activate before existing handler on ALL known commands
                        foreach (AddInCommandBinding addinCmdBinding in GetAllCommandBindings(uiApp))
                            if (toggle_on)
                                addinCmdBinding.BeforeExecuted += hndlr.AddInCommandBinding_BeforeExecuted;
                            else
                                addinCmdBinding.BeforeExecuted -= hndlr.AddInCommandBinding_BeforeExecuted;
                    }
                    else {
                        cmdBinding = GetCommandBinding(uiApp, eventTarget);
                        if (toggle_on)
                            cmdBinding.BeforeExecuted += hndlr.AddInCommandBinding_BeforeExecuted;
                        else
                            cmdBinding.BeforeExecuted -= hndlr.AddInCommandBinding_BeforeExecuted;
                    }
                    break;
#else
                    throw new NotSupportedFeatureException();
#endif

                case EventType.AddInCommandBinding_CanExecute:
                    if (eventTarget != null) {
                        cmdBinding = GetCommandBinding(uiApp, eventTarget);
                        if (toggle_on)
                            cmdBinding.CanExecute += hndlr.AddInCommandBinding_CanExecute;
                        else
                            cmdBinding.CanExecute -= hndlr.AddInCommandBinding_CanExecute;
                    }
                    break;

                case EventType.AddInCommandBinding_Executed:
                    if (eventTarget != null) {
                        cmdBinding = GetCommandBinding(uiApp, eventTarget);
                        if (toggle_on)
                            cmdBinding.Executed += hndlr.AddInCommandBinding_Executed;
                        else
                            cmdBinding.Executed -= hndlr.AddInCommandBinding_Executed;
                    }
                    break;

                case EventType.Application_JournalUpdated:
                    if (toggle_on) {
                        ActivateJournalListener(uiApp);
                        journalListener.OnJournalUpdate += hndlr.Application_JournalUpdated;
                        journalListener.JournalUpdateEvents = true;
                    }
                    else if (journalListener != null) {
                        journalListener.OnJournalUpdate -= hndlr.Application_JournalUpdated;
                        journalListener.JournalUpdateEvents = false;
                        DeactivateJournalListener(uiApp);
                    }
                    break;

                case EventType.Application_JournalCommandExecuted:
                    if (toggle_on) {
                        ActivateJournalListener(uiApp);
                        journalListener.OnJournalCommandExecuted += hndlr.Application_JournalCommandExecuted;
                        journalListener.JournalCommandExecutedEvents = true;
                    }
                    else if (journalListener != null) {
                        journalListener.OnJournalCommandExecuted -= hndlr.Application_JournalCommandExecuted;
                        journalListener.JournalCommandExecutedEvents = false;
                        DeactivateJournalListener(uiApp);
                    }
                    break;

                case EventType.Application_IUpdater:
                    if (toggle_on) {
                        ActivateUpdaterListener();
                        updaterListener.OnUpdaterExecute += hndlr.Application_IUpdater;
                    }
                    else if (updaterListener != null) {
                        updaterListener.OnUpdaterExecute -= hndlr.Application_IUpdater;
                        DeactivateUpdaterListener();
                    }
                    break;
            }
        }
    }

    public class AppEventUtils {
    }

    public class UIAppEventUtils {
        public static Visual GetWindowRoot(UIApplication uiapp) {
            IntPtr wndHndle = IntPtr.Zero;
            try {
#if (REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017 || REVIT2018)
                wndHndle = Autodesk.Windows.ComponentManager.ApplicationWindow;
#else
                wndHndle = uiapp.MainWindowHandle;
#endif

            }
            catch { }

            if (wndHndle != IntPtr.Zero) {
                var wndSource = HwndSource.FromHwnd(wndHndle);
                return wndSource.RootVisual;
            }
            return null;
        }
    }

    public static class DocumentEventUtils {
        private static bool _txnCompleted = false;
        private static Document _doc = null;
        private static string _txnName = null;
        private static BuiltInParameter _paramToUpdate;
        private static string _paramToUpdateStringValue = null;
        private static UIApplication _uiApp = null;
        private static List<ElementId> _newElements = null;

        private static void OnDocumentChanged(object sender, DocumentChangedEventArgs e) {
            if (_newElements == null)
                _newElements = new List<ElementId>();
            _newElements.AddRange(e.GetAddedElementIds());
        }

        private static void CancelAllDialogs(object sender, DialogBoxShowingEventArgs e) {
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

        private static void NewElementPropertyValueUpdater(object sender, IdlingEventArgs e) {
            // cancel if txn is completed
            if (_txnCompleted) {
                _uiApp.Idling -= NewElementPropertyValueUpdater;
                EndCancellingAllDialogs();
                EndTrackingElements();
            }

            // now update element parameters
            try {
                var TXN = new Transaction(_doc, _txnName);
                TXN.Start();
                foreach (var newElId in _newElements) {
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

        private static void Init() {
            _txnCompleted = false;
            _doc = null;
            _txnName = null;
            _paramToUpdateStringValue = null;
            _uiApp = null;
            _newElements = null;
        }

        private static void StartTrackingElements() {
            _uiApp.Application.DocumentChanged += OnDocumentChanged;
        }

        private static void EndTrackingElements() {
            _uiApp.Application.DocumentChanged -= OnDocumentChanged;
        }

        private static void StartCancellingAllDialogs() {
            _uiApp.DialogBoxShowing += CancelAllDialogs;
        }

        private static void EndCancellingAllDialogs() {
            _uiApp.DialogBoxShowing -= CancelAllDialogs;
        }

        private static void PostElementPropertyUpdateRequest(Document doc, string txnName, BuiltInParameter bip, string value) {
            _doc = doc;
            _txnName = txnName;
            _paramToUpdate = bip;
            _paramToUpdateStringValue = value;
            _uiApp.Idling += NewElementPropertyValueUpdater;
        }

#if !(REVIT2013)
        public static void PostCommandAndUpdateNewElementProperties(UIApplication uiapp, Document doc, PostableCommand postableCommand, string transactionName, BuiltInParameter bip, string value) {
            Init();

            _uiApp = uiapp;
            StartTrackingElements();
            StartCancellingAllDialogs();

            var postableCommandId = RevitCommandId.LookupPostableCommandId(postableCommand);
            _uiApp.PostCommand(postableCommandId);

            PostElementPropertyUpdateRequest(doc, transactionName, bip, value);
        }
#endif
    }

    public class PlaceKeynoteExternalEventHandler : IExternalEventHandler {
        public string KeynoteKey = null;
#if !(REVIT2013)
        public PostableCommand KeynoteType = PostableCommand.UserKeynote;
#endif
        public void Execute(UIApplication uiApp) {
#if !(REVIT2013)
            DocumentEventUtils.PostCommandAndUpdateNewElementProperties(
                uiApp,
                uiApp.ActiveUIDocument.Document,
                KeynoteType,
                "Update",
                BuiltInParameter.KEY_VALUE,
                KeynoteKey
                );
#else
            throw new NotSupportedFeatureException();
#endif
        }

        public string GetName() {
            return "PlaceKeynoteExternalEvent";
        }
    }

    // https://tinyurl.com/yj8x4azp
    public class HSLColor {
        public readonly double h, s, l, a;

        public HSLColor(double h, double s, double l, double a) {
            this.h = h;
            this.s = s;
            this.l = l;
            this.a = a;
        }

        public HSLColor(System.Windows.Media.Color rgb) {
            RgbToHls(rgb.R, rgb.G, rgb.B, out h, out l, out s);
            a = rgb.A / 255.0;
        }

        public System.Windows.Media.Color ToRgb() {
            int r, g, b;
            HlsToRgb(h, l, s, out r, out g, out b);
            return System.Windows.Media.Color.FromArgb((byte)(a * 255.0), (byte)r, (byte)g, (byte)b);
        }

        public HSLColor Lighten(double amount) {
            return new HSLColor(h, s, Clamp(l * amount, 0, 1), a);
        }

        private static double Clamp(double value, double min, double max) {
            if (value < min)
                return min;
            if (value > max)
                return max;

            return value;
        }

        // Convert an RGB value into an HLS value.
        static void RgbToHls(int r, int g, int b,
            out double h, out double l, out double s) {
            // Convert RGB to a 0.0 to 1.0 range.
            double double_r = r / 255.0;
            double double_g = g / 255.0;
            double double_b = b / 255.0;

            // Get the maximum and minimum RGB components.
            double max = double_r;
            if (max < double_g) max = double_g;
            if (max < double_b) max = double_b;

            double min = double_r;
            if (min > double_g) min = double_g;
            if (min > double_b) min = double_b;

            double diff = max - min;
            l = (max + min) / 2;
            if (Math.Abs(diff) < 0.00001) {
                s = 0;
                h = 0;  // H is really undefined.
            }
            else {
                if (l <= 0.5) s = diff / (max + min);
                else s = diff / (2 - max - min);

                double r_dist = (max - double_r) / diff;
                double g_dist = (max - double_g) / diff;
                double b_dist = (max - double_b) / diff;

                if (double_r == max) h = b_dist - g_dist;
                else if (double_g == max) h = 2 + r_dist - b_dist;
                else h = 4 + g_dist - r_dist;

                h = h * 60;
                if (h < 0) h += 360;
            }
        }

        // Convert an HLS value into an RGB value.
        static void HlsToRgb(double h, double l, double s,
            out int r, out int g, out int b) {
            double p2;
            if (l <= 0.5) p2 = l * (1 + s);
            else p2 = l + s - l * s;

            double p1 = 2 * l - p2;
            double double_r, double_g, double_b;
            if (s == 0) {
                double_r = l;
                double_g = l;
                double_b = l;
            }
            else {
                double_r = QqhToRgb(p1, p2, h + 120);
                double_g = QqhToRgb(p1, p2, h);
                double_b = QqhToRgb(p1, p2, h - 120);
            }

            // Convert RGB to the 0 to 255 range.
            r = (int)(double_r * 255.0);
            g = (int)(double_g * 255.0);
            b = (int)(double_b * 255.0);
        }

        private static double QqhToRgb(double q1, double q2, double hue) {
            if (hue > 360) hue -= 360;
            else if (hue < 0) hue += 360;

            if (hue < 60) return q1 + (q2 - q1) * hue / 60;
            if (hue < 180) return q2;
            if (hue < 240) return q1 + (q2 - q1) * (240 - hue) / 60;
            return q1;
        }
    }

    public class TabColoringRule {
        public SolidColorBrush Brush { get; set; }
        public Regex TitleFilter { get; set; }

        public TabColoringRule(SolidColorBrush brush, string filter = null) {
            Brush = brush;
            try {
                if (filter is string regexFilter)
                    TitleFilter = new Regex(regexFilter);
            }
            catch {
            }
        }

        public bool IsMatch(string tabTitle) {
            if (TitleFilter is Regex filter)
                return filter.IsMatch(tabTitle);
            return false;
        }
    }

    public class TabColoringStyle {
        public string Name { get; private set; }
        public Thickness BorderThinkness = new Thickness();
        public bool FillBackground = false;

        public TabColoringStyle(string name) => Name = name;

        public static readonly Thickness DefaultBorderThickness = new Thickness();
        public static readonly Brush DefaultBorderBrush = Brushes.White;
        public static readonly Brush DefaultBackground = Brushes.Transparent;
        public static readonly Brush DefaultSelectedBackground = Brushes.White;
        public static readonly Brush DefaultForeground = Brushes.Black;
        public static readonly Brush LightForeground = Brushes.White;

        public Style CreateStyle(TabItem tab, TabColoringRule rule) {
            // create a style based on given control
            Style tabStyle = new Style(typeof(TabItem), tab.Style);
            var mouseOverTrigger = new Trigger {
                Property = TabItem.IsMouseOverProperty,
                Value = true
            };

            var selectedDt = new Trigger {
                Property = TabItem.IsSelectedProperty,
                Value = true
            };

            var hslColor = new HSLColor(rule.Brush.Color);

            // apply the new styling
            if (FillBackground) {
                MEDIA.Color c = rule.Brush.Color;
                float luminance = 0.2126f * c.R + 0.7152f * c.G + 0.0722f * c.B;
                var forgeround = luminance > 127.0f ? DefaultForeground : LightForeground;

                tabStyle.Setters.Add(
                    new Setter { Property = TabItem.BackgroundProperty, Value = rule.Brush }
                );

                var bgHightlightBrush = new SolidColorBrush(hslColor.Lighten(1.1).ToRgb());
                mouseOverTrigger.Setters.Add(
                    new Setter { Property = TabItem.BackgroundProperty, Value = bgHightlightBrush }
                );

                selectedDt.Setters.Add(
                    new Setter { Property = TabItem.BackgroundProperty, Value = bgHightlightBrush }
                    );

                tabStyle.Setters.Add(
                    new Setter { Property = TabItem.ForegroundProperty, Value = forgeround }
                );

                tabStyle.Resources["ClientAreaForegroundBrush"] = forgeround;
            }

            tabStyle.Setters.Add(
                new Setter { Property = TabItem.BorderBrushProperty, Value = rule.Brush }
            );
            tabStyle.Setters.Add(
                new Setter { Property = TabItem.BorderThicknessProperty, Value = BorderThinkness }
            );

            var borderHighlightBrush = new SolidColorBrush(hslColor.Lighten(0.9).ToRgb());
            var selectedThickness = BorderThinkness;
            selectedThickness.Bottom = 0;
            selectedDt.Setters.Add(
                new Setter { Property = TabItem.BorderThicknessProperty, Value = FillBackground ? new Thickness(1,1,1,0) : selectedThickness }
            );
            if (FillBackground) {
                selectedDt.Setters.Add(
                    new Setter { Property = TabItem.BorderBrushProperty, Value = Brushes.White }
                );

            } else {
                selectedDt.Setters.Add(
                    new Setter { Property = TabItem.BorderBrushProperty, Value = borderHighlightBrush }
                );
            }

            mouseOverTrigger.Setters.Add(
                new Setter { Property = TabItem.BorderBrushProperty, Value = borderHighlightBrush }
            );

            tabStyle.Triggers.Add(selectedDt);
            tabStyle.Triggers.Add(mouseOverTrigger);

            return tabStyle;
        }
    }

    public class TabColoringTheme {
        public class RuleSlot {
            public RuleSlot(TabColoringRule rule) => Rule = rule;

            public long Id { get; set; }
            public bool IsFamily { get; set; }
            public TabColoringRule Rule { get; private set; }

            public void Clear() {
                Id = -1;
                IsFamily = false;
            }
        }

        public bool SortDocTabs { get; set; } = false;

        public TabColoringStyle TabStyle { get; set; }
        public TabColoringStyle FamilyTabStyle { get; set; }
        public List<TabColoringRule> TabOrderRules { get; set; }
        public List<TabColoringRule> TabFilterRules { get; set; }

        public static readonly List<Brush> DefaultBrushes = new List<Brush> {
            PyRevitConsts.PyRevitAccentBrush,
            PyRevitConsts.PyRevitBackgroundBrush,
            Brushes.Blue,
            Brushes.SaddleBrown,
            Brushes.Gold,
            Brushes.DarkTurquoise,
            Brushes.OrangeRed,
            Brushes.Aqua,
            Brushes.YellowGreen,
            Brushes.DeepPink
        };

        public static readonly List<TabColoringStyle> AvailableStyles = new List<TabColoringStyle> {
            new TabColoringStyle("Top Bar - Light") { BorderThinkness = new Thickness(0,1,0,0) },
            new TabColoringStyle("Top Bar - Medium") { BorderThinkness = new Thickness(0,2,0,0) },
            new TabColoringStyle("Top Bar - Heavy") { BorderThinkness = new Thickness(0,3,0,0) },
            new TabColoringStyle("Border - Light") { BorderThinkness = new Thickness(1) },
            new TabColoringStyle("Border - Medium") { BorderThinkness = new Thickness(2) },
            new TabColoringStyle("Border - Heavy") { BorderThinkness = new Thickness(3) },
            new TabColoringStyle("Background Fill") { BorderThinkness = new Thickness(2), FillBackground = true },
        };

        public static readonly uint DefaultTabColoringStyleIndex = 0;
        public static readonly uint DefaultFamilyTabColoringStyleIndex = 3;

        string _lastTabState = string.Empty;
        Dictionary<TabItem, Style> _tabOrigStyles = new Dictionary<TabItem, Style>();
        List<RuleSlot> _ruleSlots = new List<RuleSlot>();

        public List<RuleSlot> StyledDocuments => _ruleSlots.ToList();

        static string GetTabUniqueId(TabItem tab) {
            return $"{((LayoutDocument)tab.Header).Title}+{tab.GetHashCode()}+{tab.IsSelected}";
        }

        static long GetTabDocumentId(TabItem tab) {
            return (
                (MFCMDIFrameHost)(
                    (MFCMDIChildFrameControl)(
                        (Xceed.Wpf.AvalonDock.Layout.LayoutDocument)tab.Content
                    ).Content
                ).Content
            ).document.ToInt64();
        }

        static long GetAPIDocumentId(Document doc) {
            MethodInfo getMFCDocMethod = doc.GetType().GetMethod("getMFCDoc", BindingFlags.Instance | BindingFlags.NonPublic);
            object mfcDoc = getMFCDocMethod.Invoke(doc, new object[] { });
            MethodInfo ptfValMethod = mfcDoc.GetType().GetMethod("GetPointerValue", BindingFlags.Instance | BindingFlags.NonPublic);
            return ((IntPtr)ptfValMethod.Invoke(mfcDoc, new object[] { })).ToInt64();
        }

        public void SetTheme(UIApplication uiApp, IEnumerable<TabItem> docTabs) {
            // dont do anything if it is the same tabs as before
            string newState = string.Join(";", docTabs.Select(t => GetTabUniqueId(t)));
            if (newState == _lastTabState)
                return;
            else
                _lastTabState = newState;


            // collect ids of family documents
            var allDocs = new List<long>();
            var familyDocs = new List<long>();
            foreach (Document doc in uiApp.Application.Documents) {
                // skip linked docs. they don't have tabs
                if (doc.IsLinked)
                    continue;

                var docId = GetAPIDocumentId(doc);
                allDocs.Add(docId);
                if (doc.IsFamilyDocument)
                    familyDocs.Add(docId);
            }

            // cleanup styling for docs that do no exists anymore
            // empty this before setting new styles so empty slots can be taken
            var removedDocs = _ruleSlots.Where(d => !allDocs.Contains(d.Id)).ToList();
            foreach (RuleSlot rslot in removedDocs)
                rslot.Clear();

            // cleanup any recorded tabs that do not exist anymore
            var removedTabs = _tabOrigStyles.Keys.Where(t => !docTabs.Contains(t)).ToList();
            foreach (TabItem tab in removedTabs)
                _tabOrigStyles.Remove(tab);

            // go over each tab and determine
            foreach (TabItem tab in docTabs) {
                long docId = GetTabDocumentId(tab);

                if (!_tabOrigStyles.ContainsKey(tab))
                    _tabOrigStyles[tab] = tab.Style;

                Set(
                    tab: tab,
                    docId: docId,
                    isFamilyTab: familyDocs.Contains(docId)
                );
            }
        }
        
        void Set(TabItem tab, long docId, bool isFamilyTab) {
            // determine style
            TabColoringStyle tstyle = isFamilyTab ? FamilyTabStyle : TabStyle;

            string title = ((LayoutDocument)tab.Header).Title;
            
            // apply colors by filter
            bool filtered = false;
            foreach (var rule in TabFilterRules) {
                //if tab title does not match the filter do not do anything
                if (!rule.IsMatch(title))
                    continue;

                tab.Style = tstyle.CreateStyle(tab, rule);
                filtered = true;
                break;
            }

            // if filter is applied to the tab, move on to next
            if (filtered) return;

            // otherwise apply colors by order
            var docSlot = _ruleSlots.Where(d => d.Id == docId).FirstOrDefault();
            if (docSlot is RuleSlot) {
                Style style = tstyle.CreateStyle(tab, docSlot.Rule);
                tab.Style = style;
            }
            else {
                RuleSlot slot = null;

                if (_ruleSlots != null && _ruleSlots.Count() >= 1) {
                    int nextRuleIndex = _ruleSlots.Count();
                    if (nextRuleIndex >= TabOrderRules.Count) {
                        var firstEmptySlot = _ruleSlots.Where(r => r.Id == -1).FirstOrDefault();
                        if (firstEmptySlot is RuleSlot) {
                            slot = firstEmptySlot;
                            slot.Id = docId;
                            slot.IsFamily = isFamilyTab;
                        }
                    }
                    else {
                        slot = new RuleSlot(TabOrderRules[nextRuleIndex]) {
                            Id = docId,
                            IsFamily = isFamilyTab,
                        };
                        _ruleSlots.Add(slot);
                    }
                }
                else {
                    slot = new RuleSlot(TabOrderRules.FirstOrDefault()) {
                        Id = docId,
                        IsFamily = isFamilyTab,
                    };
                    _ruleSlots.Add(slot);
                }


                if (slot is RuleSlot) {
                    Style style = tstyle.CreateStyle(tab, slot.Rule);
                    tab.Style = style;
                }
            }
        }

        public void ClearTheme(UIApplication uiApp, IEnumerable<TabItem> docTabs) {
            foreach (TabItem tab in docTabs)
                if (_tabOrigStyles.TryGetValue(tab, out var tabStyle))
                    tab.Style = tabStyle;
            _tabOrigStyles.Clear();
            _lastTabState = string.Empty;
        }
    
        public void InitSlots(TabColoringTheme theme) {
            // copy the reserved slots in previous theme to new one
            _ruleSlots.Clear();
            int ruleCount = TabOrderRules.Count();
            if (ruleCount > 0) {
                int index = 0;
                foreach (RuleSlot slot in theme._ruleSlots) {
                    if (index >= ruleCount)
                        break;
                    
                    _ruleSlots.Add(
                        new RuleSlot(TabOrderRules[index]) {
                            Id = slot.Id,
                            IsFamily = slot.IsFamily
                        }
                    );
                    index++;
                }
            }
        }
    }

    public static class DocumentTabEventUtils {
        static readonly Logger logger = LogManager.GetCurrentClassLogger();

        public static UIApplication UIApp { get; private set; }

        public static bool IsUpdatingDocumentTabs { get; private set; }

        static object UpdateLock = new object();

        static TabColoringTheme _tabColoringTheme = null;
        public static TabColoringTheme TabColoringTheme {
            get => _tabColoringTheme;
            set {
                // copy the reserved slots in previous theme to new one
                if (value is TabColoringTheme && _tabColoringTheme != null)
                    value.InitSlots(_tabColoringTheme);
                _tabColoringTheme = value;
            }
        }

#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017 || REVIT2018)
        public static Xceed.Wpf.AvalonDock.DockingManager GetDockingManager(UIApplication uiapp) {
            var wndRoot = (MainWindow)UIAppEventUtils.GetWindowRoot(uiapp);
            if (wndRoot != null) {
                return MainWindow.FindFirstChild<Xceed.Wpf.AvalonDock.DockingManager>(wndRoot);
            }
            return null;
        }

        public static LayoutDocumentPaneGroupControl GetDocumentTabGroup(UIApplication uiapp) {
            var wndRoot = UIAppEventUtils.GetWindowRoot(uiapp);
            if (wndRoot != null) {
                return MainWindow.FindFirstChild<LayoutDocumentPaneGroupControl>((MainWindow)wndRoot);
            }
            return null;
        }

        public static IEnumerable<LayoutDocumentPaneControl> GetDocumentPanes(LayoutDocumentPaneGroupControl docTabGroup) {
            if (docTabGroup != null) {
                return docTabGroup.FindVisualChildren<LayoutDocumentPaneControl>();
            }
            return new List<LayoutDocumentPaneControl>();
        }

        public static DocumentPaneTabPanel GetDocumentTabsPane(LayoutDocumentPaneGroupControl docTabGroup) {
            return docTabGroup?.FindVisualChildren<DocumentPaneTabPanel>()?.FirstOrDefault();
        }

        public static IEnumerable<TabItem> GetDocumentTabs(LayoutDocumentPaneControl docPane) {
            if (docPane != null) {
                return docPane.FindVisualChildren<TabItem>();
            }
            return new List<TabItem>();
        }

        public static IEnumerable<TabItem> GetDocumentTabs(LayoutDocumentPaneGroupControl docTabGroup) {
            if (docTabGroup != null) {
                return docTabGroup.FindVisualChildren<TabItem>();
            }
            return new List<TabItem>();
        }

        public static void StartGroupingDocumentTabs(UIApplication uiapp) {
            lock (UpdateLock) {
                if (!IsUpdatingDocumentTabs) {
                    UIApp = uiapp;
                    IsUpdatingDocumentTabs = true;

                    var docMgr = GetDockingManager(UIApp);
                    docMgr.LayoutUpdated += UpdateDockingManagerLayout;
                }
            }
        }

        public static void StopGroupingDocumentTabs() {
            lock (UpdateLock) {
                if (IsUpdatingDocumentTabs) {
                    var docMgr = GetDockingManager(UIApp);
                    docMgr.LayoutUpdated -= UpdateDockingManagerLayout;

                    ClearDocumentTabGroups();

                    IsUpdatingDocumentTabs = false;
                }
            }
        }

        static void UpdateDockingManagerLayout(object sender, EventArgs e) {
            UpdateDocumentTabGroups();
        }

        static void ClearDocumentTabGroups() {
            lock (UpdateLock) {
                var docTabGroup = GetDocumentTabGroup(UIApp);
                if (docTabGroup != null) {
                    var docTabs = GetDocumentTabs(docTabGroup);
                    // dont do anything if there are no tabs
                    if (docTabs.Count() == 0)
                        return;

                    // reset tabs
                    if (TabColoringTheme is TabColoringTheme theme)
                        theme.ClearTheme(UIApp, docTabs);
                }
            }
        }

        static void UpdateDocumentTabGroups() {
            lock (UpdateLock) {
                if (IsUpdatingDocumentTabs) {
                    // get the ui tabs
                    var docTabGroup = GetDocumentTabGroup(UIApp);
                    if (docTabGroup != null) {
                        var docTabs = GetDocumentTabs(docTabGroup);

                        // dont do anything if there are no tabs
                        if (docTabs.Count() == 0)
                            return;

                        // update tabs
                        if (TabColoringTheme is TabColoringTheme theme)
                            theme.SetTheme(UIApp, docTabs);
                    }
                }
            }
        }
#endif
    }

    public static class RibbonEventUtils {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        public static bool IsUpdatingRibbon { get; private set; }
        private static object UpdateLock = new object();

        // updating flow direction on tabs
        public static StackPanel PanelSet;
        public static string RibbonTabTag;
        public static System.Windows.FlowDirection FlowDirection { get; set; }

        public static void StartUpdatingRibbon(StackPanel panelSet, System.Windows.FlowDirection flowDir, string tagTag) {
            PanelSet = panelSet;
            FlowDirection = flowDir;
            RibbonTabTag = tagTag;

            if (PanelSet != null && RibbonTabTag != null) {
                PanelSet.LayoutUpdated += PanelSet_LayoutUpdated;
                IsUpdatingRibbon = true;
            }
        }

        public static void StopUpdatingRibbon() {
            FlowDirection = System.Windows.FlowDirection.LeftToRight;

            // reset the ui to default flow direction
            if (PanelSet != null && RibbonTabTag != null) {
                PanelSet.LayoutUpdated -= PanelSet_LayoutUpdated;
                SetTabFlowDirection();
            }

            RibbonTabTag = null;
            IsUpdatingRibbon = false;
        }

        public static void PanelSet_LayoutUpdated(object sender, EventArgs e) {
            lock (UpdateLock) {
                SetTabFlowDirection();
            }
        }

        public static void SetTabFlowDirection() {
            foreach (ContentPresenter cpresenter in PanelSet.Children.OfType<ContentPresenter>()) {
                if (cpresenter.DataContext is Autodesk.Windows.RibbonTab) {
                    var ribbonTab = (Autodesk.Windows.RibbonTab)cpresenter.DataContext;
                    if (ribbonTab.Tag is string
                            && (string)ribbonTab.Tag == RibbonTabTag
                            && cpresenter.FlowDirection != FlowDirection)
                        cpresenter.FlowDirection = FlowDirection;
                }
            }
        }
    }
}
