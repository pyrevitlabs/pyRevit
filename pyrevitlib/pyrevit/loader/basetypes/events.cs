using System;
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
using Autodesk.Revit.UI.Events;

using pyRevitLabs.Common;
using pyRevitLabs.TargetApps.Revit;

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

    public interface IEventTypeHandler {
#if !(REVIT2013)
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
    }

    public static class EventUtils {
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
            { EventType.UIApplication_TransferredProjectStandards, "transferred_project_standards" },
            { EventType.UIApplication_TransferringProjectStandards, "transferring_project_standards" },
            { EventType.Application_ElementTypeDuplicated, "type-duplicated" },
            { EventType.Application_ElementTypeDuplicating, "type-duplicating" },
            { EventType.UIApplication_ViewActivated, "view-activated" },
            { EventType.UIApplication_ViewActivating, "view-activating" },
            { EventType.Application_ViewExported, "view-exported" },
            { EventType.Application_ViewExporting, "view-exporting" },
            { EventType.Application_ViewPrinted, "view-printed" },
            { EventType.Application_ViewPrinting, "view-printing" },
            { EventType.Application_WorksharedOperationProgressChanged, "worksharing-ops-progress-changed" },
        };

        public static string GetEventName(EventType eventType) {
            string eventName = null;
            eventNames.TryGetValue(eventType, out eventName);
            return eventName;
        }

        public static EventType GetEventType(string eventName) {
            return eventNames.FirstOrDefault(x => x.Value == eventName).Key;
        }

        public static List<EventType> GetSupportedEventTypes(RevitProduct revit) {
            return GetSupportedEventTypes(revit.ProductYear);
        }

        public static List<EventType> GetSupportedEventTypes(int productYear) {
            var supTypes = new List<EventType>();
            var supportedHandlers = typeof(IEventTypeHandler).GetMembers().Select(m => m.Name);
            foreach (EventType eventType in Enum.GetValues(typeof(EventType)))
                if (supportedHandlers.Contains(eventType.ToString()))
                    supTypes.Add(eventType);
            return supTypes;
        }

        public static void ToggleHooks<T>(T hndlr, UIApplication uiApp, EventType eventType, bool toggle_on = true) where T: IEventTypeHandler {
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
                    throw new PyRevitNotSupportedFeatureException();
#endif

                case EventType.Application_ElementTypeDuplicated:
#if !(REVIT2013 || REVIT2014)
                    if (toggle_on)
                        uiApp.Application.ElementTypeDuplicated += hndlr.Application_ElementTypeDuplicated;
                    else
                        uiApp.Application.ElementTypeDuplicated -= hndlr.Application_ElementTypeDuplicated;
                    break;
#else
                    throw new PyRevitNotSupportedFeatureException();
#endif

                case EventType.Application_ElementTypeDuplicating:
#if !(REVIT2013 || REVIT2014)
                    if (toggle_on)
                        uiApp.Application.ElementTypeDuplicating += hndlr.Application_ElementTypeDuplicating;
                    else
                        uiApp.Application.ElementTypeDuplicating -= hndlr.Application_ElementTypeDuplicating;
                    break;
#else
                    throw new PyRevitNotSupportedFeatureException();
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
                    throw new PyRevitNotSupportedFeatureException();
#endif

                case EventType.Application_FamilyLoadingIntoDocument:
#if !(REVIT2013 || REVIT2014)
                    if (toggle_on)
                        uiApp.Application.FamilyLoadingIntoDocument += hndlr.Application_FamilyLoadingIntoDocument;
                    else
                        uiApp.Application.FamilyLoadingIntoDocument -= hndlr.Application_FamilyLoadingIntoDocument;
                    break;
#else
                    throw new PyRevitNotSupportedFeatureException();
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
                    throw new PyRevitNotSupportedFeatureException();
#endif

                case EventType.Application_LinkedResourceOpening:
#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017)
                    if (toggle_on)
                        uiApp.Application.LinkedResourceOpening += hndlr.Application_LinkedResourceOpening;
                    else
                        uiApp.Application.LinkedResourceOpening -= hndlr.Application_LinkedResourceOpening;
                    break;
#else
                    throw new PyRevitNotSupportedFeatureException();
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
                    throw new PyRevitNotSupportedFeatureException();
#endif

                case EventType.Application_ViewExporting:
#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017)
                    if (toggle_on)
                        uiApp.Application.ViewExporting += hndlr.Application_ViewExporting;
                    else
                        uiApp.Application.ViewExporting -= hndlr.Application_ViewExporting;
                    break;
#else
                    throw new PyRevitNotSupportedFeatureException();
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
                    throw new PyRevitNotSupportedFeatureException();
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
                    throw new PyRevitNotSupportedFeatureException();
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
                    throw new PyRevitNotSupportedFeatureException();
#endif

                case EventType.UIApplication_DockableFrameVisibilityChanged:
#if !(REVIT2013 || REVIT2014)
                    if (toggle_on)
                        uiApp.DockableFrameVisibilityChanged += hndlr.UIApplication_DockableFrameVisibilityChanged;
                    else
                        uiApp.DockableFrameVisibilityChanged -= hndlr.UIApplication_DockableFrameVisibilityChanged;
                    break;
#else
                    throw new PyRevitNotSupportedFeatureException();
#endif

                case EventType.UIApplication_FabricationPartBrowserChanged:
#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016)
                    if (toggle_on)
                        uiApp.FabricationPartBrowserChanged += hndlr.UIApplication_FabricationPartBrowserChanged;
                    else
                        uiApp.FabricationPartBrowserChanged -= hndlr.UIApplication_FabricationPartBrowserChanged;
                    break;
#else
                    throw new PyRevitNotSupportedFeatureException();
#endif

                case EventType.UIApplication_FormulaEditing:
#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017 || REVIT2018)
                    if (toggle_on)
                        uiApp.FormulaEditing += hndlr.UIApplication_FormulaEditing;
                    else
                        uiApp.FormulaEditing -= hndlr.UIApplication_FormulaEditing;
                    break;
#else
                    throw new PyRevitNotSupportedFeatureException();
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
                    throw new PyRevitNotSupportedFeatureException();
#endif

                case EventType.UIApplication_TransferringProjectStandards:
#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017)
                    if (toggle_on)
                        uiApp.TransferringProjectStandards += hndlr.UIApplication_TransferringProjectStandards;
                    else
                        uiApp.TransferringProjectStandards -= hndlr.UIApplication_TransferringProjectStandards;
                    break;
#else
                    throw new PyRevitNotSupportedFeatureException();
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
            }
        }
    }

    public class AppEventUtils {
        public Application App { get; private set; }

        public AppEventUtils(Application app) {
            if (app != null) {
                App = app;
            }
            else
                throw new Exception("Application can not be null.");
        }
    }

    public class UIEventUtils {
        private bool _txnCompleted = false;
        private Document _doc = null;
        private string _txnName = null;
        private BuiltInParameter _paramToUpdate;
        private string _paramToUpdateStringValue = null;

        public UIApplication UIApp { get; private set; }
        public List<ElementId> NewElements { get; private set; }

        public UIEventUtils(UIApplication uiApp) {
            if (uiApp != null) {
                UIApp = uiApp;
                NewElements = new List<ElementId>();
            }
            else
                throw new Exception("UIApplication can not be null.");
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
                UIApp.Idling -= NewElementPropertyValueUpdater;
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
            UIApp.Application.DocumentChanged += OnDocumentChanged;
        }

        public void EndTrackingElements() {
            UIApp.Application.DocumentChanged -= OnDocumentChanged;
        }

        public void StartCancellingAllDialogs() {
            UIApp.DialogBoxShowing += CancelAllDialogs;
        }

        public void EndCancellingAllDialogs() {
            UIApp.DialogBoxShowing -= CancelAllDialogs;
        }

        public void PostElementPropertyUpdateRequest(Document doc,
                                                     string txnName,
                                                     BuiltInParameter bip,
                                                     string value) {
            _doc = doc;
            _txnName = txnName;
            _paramToUpdate = bip;
            _paramToUpdateStringValue = value;
            UIApp.Idling += NewElementPropertyValueUpdater;
        }

 #if !(REVIT2013)
        public void PostCommandAndUpdateNewElementProperties(Document doc,
                                                             PostableCommand postableCommand, string transactionName,
                                                             BuiltInParameter bip, string value) {
            StartTrackingElements();
            StartCancellingAllDialogs();
            var postableCommandId = RevitCommandId.LookupPostableCommandId(postableCommand);
            UIApp.PostCommand(postableCommandId);
            PostElementPropertyUpdateRequest(doc, transactionName, bip, value);
        }
#endif
    }

    public class PlaceKeynoteExternalEventHandler : IExternalEventHandler {
        public string KeynoteKey = null;
#if !(REVIT2013)
        public PostableCommand KeynoteType = PostableCommand.UserKeynote;
#endif
        public PlaceKeynoteExternalEventHandler() {}

        public void Execute(UIApplication app) {
#if !(REVIT2013)
            var docutils = new UIEventUtils(app);
            docutils.PostCommandAndUpdateNewElementProperties(
                app.ActiveUIDocument.Document,
                KeynoteType,
                "Update",
                BuiltInParameter.KEY_VALUE,
                KeynoteKey
                );
#else
            throw new PyRevitNotSupportedFeatureException();
#endif
        }

        public string GetName() {
            return "PlaceKeynoteExternalEvent";
        }
    }
}
