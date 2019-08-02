using System;
using System.IO;
using System.Collections.Generic;
using System.Diagnostics;

using Autodesk.Revit.ApplicationServices;
using Autodesk.Revit.UI;

namespace PyRevitBaseClasses {
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

        // event management ------------------------------------------------------------------------------------------

        public static void RegisterHook(UIApplication uiApp, EventType eventType) {
            toggleHooks(uiApp, eventType);
        }

        public static void UnRegisterHook(UIApplication uiApp, EventType eventType) {
            toggleHooks(uiApp, eventType, toggle_on: false);
        }

        // event handlers --------------------------------------------------------------------------------------------

        private static void UiApp_ViewActivating(object sender, Autodesk.Revit.UI.Events.ViewActivatingEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.UIApplication_ViewActivating))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void UiApp_ViewActivated(object sender, Autodesk.Revit.UI.Events.ViewActivatedEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.UIApplication_ViewActivated))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void UiApp_TransferringProjectStandards(object sender, Autodesk.Revit.UI.Events.TransferringProjectStandardsEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.UIApplication_TransferringProjectStandards))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void UiApp_TransferredProjectStandards(object sender, Autodesk.Revit.UI.Events.TransferredProjectStandardsEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.UIApplication_TransferredProjectStandards))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void UiApp_Idling(object sender, Autodesk.Revit.UI.Events.IdlingEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.UIApplication_Idling))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void UiApp_FormulaEditing(object sender, Autodesk.Revit.UI.Events.FormulaEditingEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.UIApplication_FormulaEditing))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void UiApp_FabricationPartBrowserChanged(object sender, Autodesk.Revit.UI.Events.FabricationPartBrowserChangedEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.UIApplication_FabricationPartBrowserChanged))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void UiApp_DockableFrameVisibilityChanged(object sender, Autodesk.Revit.UI.Events.DockableFrameVisibilityChangedEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.UIApplication_DockableFrameVisibilityChanged))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void UiApp_DockableFrameFocusChanged(object sender, Autodesk.Revit.UI.Events.DockableFrameFocusChangedEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.UIApplication_DockableFrameFocusChanged))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void UiApp_DisplayingOptionsDialog(object sender, Autodesk.Revit.UI.Events.DisplayingOptionsDialogEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.UIApplication_DisplayingOptionsDialog))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void UiApp_DialogBoxShowing(object sender, Autodesk.Revit.UI.Events.DialogBoxShowingEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.UIApplication_DialogBoxShowing))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void UiApp_ApplicationClosing(object sender, Autodesk.Revit.UI.Events.ApplicationClosingEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.UIApplication_ApplicationClosing))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_WorksharedOperationProgressChanged(object sender, Autodesk.Revit.DB.Events.WorksharedOperationProgressChangedEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_WorksharedOperationProgressChanged))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_ViewPrinting(object sender, Autodesk.Revit.DB.Events.ViewPrintingEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_ViewPrinting))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_ViewPrinted(object sender, Autodesk.Revit.DB.Events.ViewPrintedEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_ViewPrinted))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_ViewExporting(object sender, Autodesk.Revit.DB.Events.ViewExportingEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_ViewExporting))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_ViewExported(object sender, Autodesk.Revit.DB.Events.ViewExportedEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_ViewExported))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_ProgressChanged(object sender, Autodesk.Revit.DB.Events.ProgressChangedEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_ProgressChanged))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_LinkedResourceOpening(object sender, Autodesk.Revit.DB.Events.LinkedResourceOpeningEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_LinkedResourceOpening))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_LinkedResourceOpened(object sender, Autodesk.Revit.DB.Events.LinkedResourceOpenedEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_LinkedResourceOpened))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_FileImporting(object sender, Autodesk.Revit.DB.Events.FileImportingEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_FileImporting))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_FileImported(object sender, Autodesk.Revit.DB.Events.FileImportedEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_FileImported))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_FileExporting(object sender, Autodesk.Revit.DB.Events.FileExportingEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_FileExporting))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_FileExported(object sender, Autodesk.Revit.DB.Events.FileExportedEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_FileExported))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_FamilyLoadingIntoDocument(object sender, Autodesk.Revit.DB.Events.FamilyLoadingIntoDocumentEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_FamilyLoadingIntoDocument))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_FamilyLoadedIntoDocument(object sender, Autodesk.Revit.DB.Events.FamilyLoadedIntoDocumentEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_FamilyLoadedIntoDocument))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_FailuresProcessing(object sender, Autodesk.Revit.DB.Events.FailuresProcessingEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_FailuresProcessing))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_ElementTypeDuplicating(object sender, Autodesk.Revit.DB.Events.ElementTypeDuplicatingEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_ElementTypeDuplicating))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_ElementTypeDuplicated(object sender, Autodesk.Revit.DB.Events.ElementTypeDuplicatedEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_ElementTypeDuplicated))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_DocumentWorksharingEnabled(object sender, Autodesk.Revit.DB.Events.DocumentWorksharingEnabledEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_DocumentWorksharingEnabled))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_DocumentSynchronizingWithCentral(object sender, Autodesk.Revit.DB.Events.DocumentSynchronizingWithCentralEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_DocumentSynchronizingWithCentral))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_DocumentSynchronizedWithCentral(object sender, Autodesk.Revit.DB.Events.DocumentSynchronizedWithCentralEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_DocumentSynchronizedWithCentral))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_DocumentSavingAs(object sender, Autodesk.Revit.DB.Events.DocumentSavingAsEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_DocumentSavingAs))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_DocumentSavedAs(object sender, Autodesk.Revit.DB.Events.DocumentSavedAsEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_DocumentSavedAs))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_DocumentSaving(object sender, Autodesk.Revit.DB.Events.DocumentSavingEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_DocumentSaving))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_DocumentSaved(object sender, Autodesk.Revit.DB.Events.DocumentSavedEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_DocumentSaved))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_DocumentPrinting(object sender, Autodesk.Revit.DB.Events.DocumentPrintingEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_DocumentPrinting))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_DocumentPrinted(object sender, Autodesk.Revit.DB.Events.DocumentPrintedEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_DocumentPrinted))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_DocumentOpening(object sender, Autodesk.Revit.DB.Events.DocumentOpeningEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_DocumentOpening))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_DocumentOpened(object sender, Autodesk.Revit.DB.Events.DocumentOpenedEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_DocumentOpened))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_DocumentCreating(object sender, Autodesk.Revit.DB.Events.DocumentCreatingEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_DocumentCreating))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_DocumentCreated(object sender, Autodesk.Revit.DB.Events.DocumentCreatedEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_DocumentCreated))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_DocumentClosing(object sender, Autodesk.Revit.DB.Events.DocumentClosingEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_DocumentClosing))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_DocumentClosed(object sender, Autodesk.Revit.DB.Events.DocumentClosedEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_DocumentClosed))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_DocumentChanged(object sender, Autodesk.Revit.DB.Events.DocumentChangedEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_DocumentChanged))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }

        private static void Application_ApplicationInitialized(object sender, Autodesk.Revit.DB.Events.ApplicationInitializedEventArgs e) {
                var env = new EnvDictionary();
                foreach (string scriptPath in env.GetEventScripts(EventType.Application_ApplicationInitialized))
                    ScriptExecutor.ExecuteEventScript(scriptPath: scriptPath, eventArgs: e);
        }
    }
}
