using System;
using System.Numerics;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

using Autodesk.Revit.ApplicationServices;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Events;
using Autodesk.Revit.UI;

using pyRevitLabs.NLog;
using Autodesk.Revit.UI.Events;

namespace PyRevitLabs.PyRevit.Runtime {
    public class EventTelemetryRecord : TelemetryRecord {
        // which event?
        public string type { get; set; }
        public Dictionary<string, object> args { get; set; }
        public string status { get; set; }

        // by who?
        public string username { get; set; }
        // on what?
        public string handler_id { get; set; }
        public string revit { get; set; }
        public string revitbuild { get; set; }

        public bool cancellable { get; set; }
        public bool cancelled { get; set; }
        public int docid { get; set; }
        public string doctype { get; set; }
        public string doctemplate { get; set; }
        public string docname { get; set; }
        public string docpath { get; set; }

        public string projectnum { get; set; }
        public string projectname { get; set; }

        public EventTelemetryRecord() : base() { }
    }

    public delegate void EventTelemetryExternalEventDelegate(UIApplication uiapp, object sender, object e);

    public class EventTelemetryExternalEventHandler : IExternalEventHandler {
        public object Sender;
        public CommandExecutedArgs CommandExecArgs;

        public EventTelemetryExternalEventDelegate EventTelemetryDelegate;

        public void Execute(UIApplication uiApp) {
            if (EventTelemetryDelegate != null)
                EventTelemetryDelegate(uiApp, Sender, CommandExecArgs);
        }

        public string GetName() {
            return "EventTelemetryExternalEventHandler";
        }
    }

    public class EventTelemetry : IEventTypeHandler {
        private static Logger logger = LogManager.GetCurrentClassLogger();

        public string HandlerId;
        private static EventTelemetryExternalEventHandler extTelemetryEventHandler;
        private static ExternalEvent extTelemetryEvent;

        public EventTelemetry(string handlerId) {
            if (handlerId == null)
                handlerId = Guid.NewGuid().ToString();
            HandlerId = handlerId;
            extTelemetryEventHandler = new EventTelemetryExternalEventHandler();
            extTelemetryEvent = ExternalEvent.Create(extTelemetryEventHandler);
        }

        public static string GetParameterValue(Parameter param) {
            switch (param.StorageType) {
                case StorageType.Double: return param.AsValueString();
                case StorageType.ElementId: return param.AsValueString();
                case StorageType.Integer: return param.AsValueString();
                case StorageType.String: return param.AsString();
                default: return null;
            }
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

        public static Dictionary<string, string> GetViewData(Element element) {
            var viewData = new Dictionary<string, string>();
            if (element is View) {
                View view = (View)element;
                string viewFamilyName = string.Empty;
                if (view.Document != null) {
                    var viewamily = view.Document.GetElement(view.GetTypeId());
                    if (viewamily != null)
                        viewFamilyName = viewamily.Name;
                }

                viewData = new Dictionary<string, string> {
                    { "type", view.ViewType.ToString() },
                    { "family",  viewFamilyName },
                    { "name", view.Name },
                    { "title", view.get_Parameter(BuiltInParameter.VIEW_DESCRIPTION).AsString() },
                };
            }
            return viewData;
        }

        public static List<Dictionary<string, string>> GetViewsData(IEnumerable<Element> elements) {
            var viewsData = new List<Dictionary<string, string>>();
            foreach (var element in elements)
                if (element is View) {
                    viewsData.Add(GetViewData(element));
                }
            return viewsData;
        }

        public static Dictionary<string, object> GetPrintSettings(PrintParameters printParams) {
            double marginx, marginy;
            int zoom;
            string zoom_type;

            // some print parameters throw exceptions
            try {
                marginx = printParams.UserDefinedMarginX;
                marginy = printParams.UserDefinedMarginY;
            }
            catch {
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
            var settings = new Dictionary<string, object> {
            { "color_depth", printParams.ColorDepth.ToString() },
                    { "hidden_line_view_type", printParams.HiddenLineViews.ToString() },
                    { "hide_cropbounds", printParams.HideCropBoundaries },
                    { "hide_refplanes", printParams.HideReforWorkPlanes },
                    { "hide_scopeboxes", printParams.HideScopeBoxes },
#if !(REVIT2013)
                    { "hide_unref_viewtags", printParams.HideUnreferencedViewTags },
#else
                    { "hide_unref_viewtags", null },
#endif
                    { "margin_type", printParams.MarginType.ToString() },
#if !(REVIT2013 || REVIT2014)
                    { "mask_lines", printParams.MaskCoincidentLines },
#else
                    { "mask_lines", null },
#endif
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
            };

            return settings;
        }

        public static string GetProjectNumber(Document doc) {
            if (doc != null)
                return doc.ProjectInformation.get_Parameter(BuiltInParameter.PROJECT_NUMBER).AsString();
            else
                return null;
        }

        public static string GetProjectName(Document doc) {
            if (doc != null)
                return doc.ProjectInformation.get_Parameter(BuiltInParameter.PROJECT_NAME).AsString();
            else
                return null;
        }

        public static Dictionary<string, object> GetProjectInfo(Document doc) {
            var docProps = new Dictionary<string, object>();
            if (doc != null) {
                var pinfo = doc.ProjectInformation;

                var docProjProps = new Dictionary<string, object>();
                foreach (Parameter param in pinfo.Parameters)
                    if (param.Id.IntegerValue > 0)
                        docProjProps.Add(param.Definition.Name, GetParameterValue(param));

                docProps = new Dictionary<string, object> {
                    { "org_name", pinfo.get_Parameter(BuiltInParameter.PROJECT_ORGANIZATION_NAME).AsString() },
                    { "org_description", pinfo.get_Parameter(BuiltInParameter.PROJECT_ORGANIZATION_DESCRIPTION).AsString() },
                    { "project_number", GetProjectNumber(doc) },
                    { "project_name", GetProjectName(doc) },
                    { "project_client_name", pinfo.get_Parameter(BuiltInParameter.CLIENT_NAME).AsString() },
                    { "project_building_name", pinfo.get_Parameter(BuiltInParameter.PROJECT_BUILDING_NAME).AsString() },
                    { "project_issue_date", pinfo.get_Parameter(BuiltInParameter.PROJECT_ISSUE_DATE).AsString() },
                    { "project_status", pinfo.get_Parameter(BuiltInParameter.PROJECT_STATUS).AsString() },
                    { "project_author", pinfo.get_Parameter(BuiltInParameter.PROJECT_AUTHOR).AsString() },
                    { "project_address", pinfo.get_Parameter(BuiltInParameter.PROJECT_ADDRESS).AsString() },
                    { "project_parameters", docProjProps },
                };

            }
            return docProps;
        }

        // event management ------------------------------------------------------------------------------------------
        public void LogEventTelemetryRecord(EventTelemetryRecord eventTelemetryRecord, object sender, object args) {
            var envDict = new EnvDictionary();

            // update general properties on record
            // host info
            if (sender != null) {
                // set the host info based on the sender type
                eventTelemetryRecord.host_user = string.Format("{0}\\{1}", Environment.UserDomainName, Environment.UserName);
                eventTelemetryRecord.username = Telemetry.GetRevitUser(sender);
                eventTelemetryRecord.revit = Telemetry.GetRevitVersion(sender);
                eventTelemetryRecord.revitbuild = Telemetry.GetRevitBuild(sender);
            }

            // set pyrevit info
            eventTelemetryRecord.handler_id = HandlerId;
            // event general info
            var apiEventArgs = args as RevitAPIEventArgs;
            if (apiEventArgs != null) {
                eventTelemetryRecord.cancellable = ((RevitAPIEventArgs)args).Cancellable;
                eventTelemetryRecord.cancelled = ((RevitAPIEventArgs)args).IsCancelled();
            }
            else {
                var eventArgs = args as RevitEventArgs;
                if (eventArgs != null) {
                    eventTelemetryRecord.cancellable = ((RevitEventArgs)args).Cancellable;
                }
            }

            // now post the telemetry record
            if (envDict.AppTelemetryState) {
                if (envDict.AppTelemetryState
                        && envDict.AppTelemetryServerUrl != null
                        && !string.IsNullOrEmpty(envDict.AppTelemetryServerUrl))
                    new Task(() =>
                        Telemetry.PostTelemetryRecord(envDict.AppTelemetryServerUrl, eventTelemetryRecord)).Start();
            }
        }

        public void RegisterEventTelemetry(UIApplication uiApp, BigInteger flags) {
            foreach (EventType eventType in EventUtils.GetAllEventTypes())
                if ((flags & (new BigInteger(1) << (int)eventType)) > 0) {
                    try {
                        // remove first
                        EventUtils.ToggleHooks<EventTelemetry>(this, uiApp, eventType, toggle_on: false);
                        // then add again
                        EventUtils.ToggleHooks<EventTelemetry>(this, uiApp, eventType);
                    }
                    catch (NotSupportedFeatureException) {
                        logger.Debug(
                            string.Format("Event telemetry {0} not supported under this Revit version. Skipped.",
                                          eventType.ToString()));
                    }
                    catch {
                        logger.Debug(string.Format("Failed registering event telemetry {0}", eventType.ToString()));
                    }
                }

        }

        public void UnRegisterEventTelemetry(UIApplication uiApp, BigInteger flags) {
            foreach (EventType eventType in Enum.GetValues(typeof(EventType)))
                if ((flags & (new BigInteger(1) << (int)eventType)) > 0)
                    try {
                        EventUtils.ToggleHooks<EventTelemetry>(this, uiApp, eventType, toggle_on: false);
                    }
                    catch (NotSupportedFeatureException) {
                        logger.Debug(
                            string.Format("Event telemetry {0} not supported under this Revit version. Skipped.",
                                          eventType.ToString()));
                    }
                    catch {
                        logger.Debug(string.Format("Failed unregistering event telemetry {0}", eventType.ToString()));
                    }
        }

        // event handlers --------------------------------------------------------------------------------------------
        public void UIApplication_ViewActivating(object sender, Autodesk.Revit.UI.Events.ViewActivatingEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.UIApplication_ViewActivating),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                projectnum = GetProjectNumber(e.Document),
                projectname = GetProjectName(e.Document),
                args = new Dictionary<string, object> {
                    { "from_view",  e.CurrentActiveView != null ? GetViewData(e.CurrentActiveView) : null },
                    { "to_view",  e.NewActiveView != null ? GetViewData(e.NewActiveView) : null },
                }
            }, sender, e);
        }

        public void UIApplication_ViewActivated(object sender, Autodesk.Revit.UI.Events.ViewActivatedEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.UIApplication_ViewActivated),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                projectnum = GetProjectNumber(e.Document),
                projectname = GetProjectName(e.Document),
                args = new Dictionary<string, object> {
                    { "from_view",  e.PreviousActiveView != null ? GetViewData(e.PreviousActiveView) : null },
                    { "to_view",  e.CurrentActiveView != null ? GetViewData(e.CurrentActiveView) : null },
                }
            }, sender, e);
        }

#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017)
        public void UIApplication_TransferringProjectStandards(object sender, Autodesk.Revit.UI.Events.TransferringProjectStandardsEventArgs e) {
            var extItems = new Dictionary<string, string>();
            foreach (var kvpair in e.GetExternalItems())
                extItems.Add(kvpair.Key.ToString(), kvpair.Value);
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.UIApplication_TransferringProjectStandards),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                projectnum = GetProjectNumber(e.Document),
                projectname = GetProjectName(e.Document),
                args = new Dictionary<string, object> {
                    { "from_document",  new Dictionary<string,string>{
                        { "docname", e.SourceDocument != null ? e.SourceDocument.Title : "" },
                        { "docpath", e.SourceDocument != null ? e.SourceDocument.PathName : "" },
                        { "projectnum", GetProjectNumber(e.SourceDocument) },
                        { "projectname", GetProjectName(e.SourceDocument) },
                    } },
                    { "to_document",  new Dictionary<string,string>{
                        { "docname", e.TargetDocument != null ? e.TargetDocument.Title : "" },
                        { "docpath", e.TargetDocument != null ? e.TargetDocument.PathName : "" },
                        { "projectnum", GetProjectNumber(e.TargetDocument) },
                        { "projectname", GetProjectName(e.TargetDocument) },
                    } },
                    { "external_items",  extItems },
                }
            }, sender, e);
        }

        public void UIApplication_TransferredProjectStandards(object sender, Autodesk.Revit.UI.Events.TransferredProjectStandardsEventArgs e) {
            var extItems = new Dictionary<string, string>();
            foreach (var kvpair in e.GetSelectedExternalItems())
                extItems.Add(kvpair.Key.ToString(), kvpair.Value);
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.UIApplication_TransferredProjectStandards),
                docname = e.SourceDocument != null ? e.SourceDocument.Title : "",
                docpath = e.SourceDocument != null ? e.SourceDocument.PathName : "",
                projectnum = GetProjectNumber(e.SourceDocument),
                projectname = GetProjectName(e.SourceDocument),
                args = new Dictionary<string, object> {
                    { "to_document",  new Dictionary<string,string>{
                        { "docname", e.TargetDocument != null ? e.TargetDocument.Title : "" },
                        { "docpath", e.TargetDocument != null ? e.TargetDocument.PathName : "" },
                        { "projectnum", GetProjectNumber(e.TargetDocument) },
                        { "projectname", GetProjectName(e.TargetDocument) },
                    } },
                    { "external_items",  extItems },
                }
            }, sender, e);
        }
#endif

        public void UIApplication_Idling(object sender, Autodesk.Revit.UI.Events.IdlingEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.UIApplication_Idling),
            }, sender, e);
        }

#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017 || REVIT2018)
        public void UIApplication_FormulaEditing(object sender, Autodesk.Revit.UI.Events.FormulaEditingEventArgs e) {
            var paramId = e.ParameterId;
            int paramIdInt = 0;
            string paramName = string.Empty;
            Element param = null;
            if (paramId != null && paramId != ElementId.InvalidElementId) {
                param = e.CurrentDocument != null ? e.CurrentDocument.GetElement(paramId) : param;
                paramIdInt = paramId.IntegerValue;
                paramName = ((ParameterElement)param).Name;
            }
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.UIApplication_FormulaEditing),
                docname = e.CurrentDocument != null ? e.CurrentDocument.Title : "",
                docpath = e.CurrentDocument != null ? e.CurrentDocument.PathName : "",
                projectnum = GetProjectNumber(e.CurrentDocument),
                projectname = GetProjectName(e.CurrentDocument),
                args = new Dictionary<string, object> {
                    { "param_id", paramIdInt },
                    { "param_name", paramName },
                    { "formula", e.Formula },
                }
            }, sender, e);
        }
#endif

#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016)
        public void UIApplication_FabricationPartBrowserChanged(object sender, Autodesk.Revit.UI.Events.FabricationPartBrowserChangedEventArgs e) {
            // TODO: implement
            //e.GetAllSolutionsPartsTypeCounts
            //e.GetCurrentSolutionPartTypeIds
            //e.GetFabricationPartTypeIds
            //e.GetFilteredSolutionsPartsTypeCounts
            //e.GetRequiredFabricationPartTypeIds
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.UIApplication_FabricationPartBrowserChanged),
                args = new Dictionary<string, object> {
                    { "operation", e.Operation.ToString() },
                    { "service_id", e.ServiceId },
                    { "solutions_count", e.NumberOfSolutions },
                }
            }, sender, e);
        }
#endif

#if !(REVIT2013 || REVIT2014)
        public void UIApplication_DockableFrameVisibilityChanged(object sender, Autodesk.Revit.UI.Events.DockableFrameVisibilityChangedEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.UIApplication_DockableFrameVisibilityChanged),
                args = new Dictionary<string, object> {
                    { "pane_id", e.PaneId.ToString() },
                    { "frame_shown", e.DockableFrameShown },
                }
            }, sender, e);
        }

        public void UIApplication_DockableFrameFocusChanged(object sender, Autodesk.Revit.UI.Events.DockableFrameFocusChangedEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.UIApplication_DockableFrameFocusChanged),
                args = new Dictionary<string, object> {
                    { "pane_id", e.PaneId.ToString() },
                    { "focus_gained", e.FocusGained },
                }
            }, sender, e);
        }
#endif

        public void UIApplication_DisplayingOptionsDialog(object sender, Autodesk.Revit.UI.Events.DisplayingOptionsDialogEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.UIApplication_DisplayingOptionsDialog),
                args = new Dictionary<string, object> {
                    { "page_count", e.PagesCount },
                }
            }, sender, e);
        }

        public void UIApplication_DialogBoxShowing(object sender, Autodesk.Revit.UI.Events.DialogBoxShowingEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.UIApplication_DialogBoxShowing),
                args = new Dictionary<string, object> {
#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016)
                    { "dialog_id", e.DialogId },
#else
                    { "dialog_id", null },
#endif
                }
            }, sender, e);
        }

        public void UIApplication_ApplicationClosing(object sender, Autodesk.Revit.UI.Events.ApplicationClosingEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.UIApplication_ApplicationClosing),
            }, sender, e);
        }

#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017)
        public void Application_WorksharedOperationProgressChanged(object sender, WorksharedOperationProgressChangedEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_WorksharedOperationProgressChanged),
                docpath = e.Location,
                status = e.Status.ToString(),
            }, sender, e);
        }
#endif

        public void Application_ViewPrinting(object sender, ViewPrintingEventArgs e) {
            var views = new List<Element>() { e.View };
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_ViewPrinting),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                projectnum = GetProjectNumber(e.Document),
                projectname = GetProjectName(e.Document),
                args = new Dictionary<string, object> {
                    { "view", GetViewsData(views) },
                    { "view_index", e.Index },
                    { "total_views", e.TotalViews },
#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016)
                    { "settings", GetPrintSettings(e.GetSettings().PrintParameters) },
#else
                    { "settings", null },
#endif
                }
            }, sender, e);
        }

        public void Application_ViewPrinted(object sender, ViewPrintedEventArgs e) {
            var views = new List<Element>() { e.View };
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_ViewPrinted),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                projectnum = GetProjectNumber(e.Document),
                projectname = GetProjectName(e.Document),
                status = e.Status.ToString(),
                args = new Dictionary<string, object> {
                    { "view", GetViewsData(views) },
                    { "view_index", e.Index },
                    { "total_views", e.TotalViews },
                }
            }, sender, e);
        }

#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017)
        public void Application_ViewExporting(object sender, ViewExportingEventArgs e) {
            var views = new List<Element>();
            if (e.Document != null)
                views.Add(e.Document.GetElement(e.ViewId));

            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_ViewExporting),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                projectnum = GetProjectNumber(e.Document),
                projectname = GetProjectName(e.Document),
                args = new Dictionary<string, object> {
                    { "view", GetViewsData(views) },
                }
            }, sender, e);
        }

        public void Application_ViewExported(object sender, ViewExportedEventArgs e) {
            var views = new List<Element>();
            if (e.Document != null)
                views.Add(e.Document.GetElement(e.ViewId));

            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_ViewExported),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                projectnum = GetProjectNumber(e.Document),
                projectname = GetProjectName(e.Document),
                status = e.Status.ToString(),
                args = new Dictionary<string, object> {
                    { "view", GetViewsData(views) },
                }
            }, sender, e);
        }
#endif

        public void Application_ProgressChanged(object sender, ProgressChangedEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_ProgressChanged),
                args = new Dictionary<string, object> {
                    { "stage", e.Stage.ToString() },
                    { "caption", e.Caption },
                    { "position", e.Position },
                    { "lower", e.LowerRange },
                    { "upper",  e.UpperRange },
                }
            }, sender, e);
        }

#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017)
        public void Application_LinkedResourceOpening(object sender, LinkedResourceOpeningEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_LinkedResourceOpening),
                args = new Dictionary<string, object> {
                    { "link_path", e.LinkedResourcePathName },
                    { "link_type",  e.ResourceType.ToString() },
                }
            }, sender, e);
        }

        public void Application_LinkedResourceOpened(object sender, LinkedResourceOpenedEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_LinkedResourceOpened),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                projectnum = GetProjectNumber(e.Document),
                projectname = GetProjectName(e.Document),
                status = e.Status.ToString(),
                args = new Dictionary<string, object> {
                    { "link_path", e.LinkedResourcePathName },
                    { "link_type",  e.ResourceType.ToString() },
                }
            }, sender, e);
        }
#endif

        public void Application_FileImporting(object sender, FileImportingEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_FileImporting),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                projectnum = GetProjectNumber(e.Document),
                projectname = GetProjectName(e.Document),
                args = new Dictionary<string, object> {
                    { "import_path", e.Path },
                    { "import_format",  e.Format },
                }
            }, sender, e);
        }

        public void Application_FileImported(object sender, FileImportedEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_FileImported),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                projectnum = GetProjectNumber(e.Document),
                projectname = GetProjectName(e.Document),
                status = e.Status.ToString(),
                args = new Dictionary<string, object> {
                    { "import_path", e.Path },
                    { "import_format",  e.Format },
                }
            }, sender, e);
        }

        public void Application_FileExporting(object sender, FileExportingEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_FileExporting),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                projectnum = GetProjectNumber(e.Document),
                projectname = GetProjectName(e.Document),
                args = new Dictionary<string, object> {
                    { "export_path", e.Path },
                    { "export_format",  e.Format },
                }
            }, sender, e);
        }

        public void Application_FileExported(object sender, FileExportedEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_FileExported),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                projectnum = GetProjectNumber(e.Document),
                projectname = GetProjectName(e.Document),
                status = e.Status.ToString(),
                args = new Dictionary<string, object> {
                    { "export_path", e.Path },
                    { "export_format",  e.Format },
                }
            }, sender, e);
        }

#if !(REVIT2013 || REVIT2014)
        public void Application_FamilyLoadingIntoDocument(object sender, FamilyLoadingIntoDocumentEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_FamilyLoadingIntoDocument),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                projectnum = GetProjectNumber(e.Document),
                projectname = GetProjectName(e.Document),
                args = new Dictionary<string, object> {
                    { "family_name", e.FamilyName },
                    { "family_path", e.FamilyPath },
                }
            }, sender, e);
        }

        public void Application_FamilyLoadedIntoDocument(object sender, FamilyLoadedIntoDocumentEventArgs e) {
            var doc = e.Document;
            string familyCategory = string.Empty;
            string originalFamilyName = string.Empty;

            if (doc != null) {
                // grab original name and category
                if (e.OriginalFamilyId != ElementId.InvalidElementId) {
                    var origFamily = doc.GetElement(e.OriginalFamilyId);
                    if (origFamily != null) {
                        originalFamilyName = origFamily.Name;
                        familyCategory = origFamily.Category != null ? origFamily.Category.Name : "";
                    }
                }

                // grab category from new family
                if (familyCategory == string.Empty && e.NewFamilyId != ElementId.InvalidElementId) {
                    var newFamily = doc.GetElement(e.NewFamilyId);
                    if (newFamily != null)
                        familyCategory = newFamily.Category != null ? newFamily.Category.Name : "";
                }
            }

            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_FamilyLoadedIntoDocument),
                docname = doc != null ? doc.Title : "",
                docpath = doc != null ? doc.PathName : "",
                projectnum = GetProjectNumber(doc),
                projectname = GetProjectName(doc),
                status = e.Status.ToString(),
                args = new Dictionary<string, object> {
                    { "family_name", e.FamilyName },
                    { "family_path", e.FamilyPath },
                    { "family_category",  familyCategory},
                    { "original_family_name", originalFamilyName },
                }
            }, sender, e);
        }
#endif

        public void Application_FailuresProcessing(object sender, FailuresProcessingEventArgs e) {
            Document doc = null;
            var failAcc = e.GetFailuresAccessor();

            var args = new Dictionary<string, object>();
            var failMessages = new Dictionary<string, object>();
            if (failAcc != null) {
                doc = failAcc.GetDocument();
                var failOptions = failAcc.GetFailureHandlingOptions();
                // collect failure information

                foreach (var fMsg in failAcc.GetFailureMessages()) {
                    var attemptedResTypes = new List<string>();
                    foreach (var aResType in failAcc.GetAttemptedResolutionTypes(fMsg))
                        attemptedResTypes.Add(aResType.ToString());
                    failMessages.Add(
                        fMsg.GetFailureDefinitionId().Guid.ToString(),
                        new Dictionary<string, object> {
                            { "description" , fMsg.GetDescriptionText() },
                            { "severity" , fMsg.GetSeverity().ToString() },
                            { "failing_elements_count" , fMsg.GetFailingElementIds().Count },
                            { "has_resolutions" , fMsg.HasResolutions() },
                            { "resolutions_count" , fMsg.GetNumberOfResolutions() },
                            { "current_resolution" , fMsg.GetCurrentResolutionType().ToString() },
                            { "default_resolution" , fMsg.GetDefaultResolutionCaption() },
                            { "attempted_resolutions" , attemptedResTypes },
                        });
                }

                args = new Dictionary<string, object> {
                    { "txn_committing", failAcc.IsTransactionBeingCommitted() },
                    { "pending", failAcc.IsPending() },
                    { "permits_resolution", failAcc.IsFailureResolutionPermitted() },
                    { "permits_deletion", failAcc.IsElementsDeletionPermitted() },
                    { "active", failAcc.IsActive() },
                    { "txn_name", failAcc.GetTransactionName() },
                    { "severity", failAcc.GetSeverity().ToString() },
                    { "messages", failMessages },
                    { "can_rollback", failAcc.CanRollBackPendingTransaction() },
                    { "can_commit", failAcc.CanCommitPendingTransaction() },
                };
            }

            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_FailuresProcessing),
                docname = doc != null ? doc.Title : "",
                docpath = doc != null ? doc.PathName : "",
                projectnum = GetProjectNumber(doc),
                projectname = GetProjectName(doc),
                args = args,
            }, sender, e);
        }

#if !(REVIT2013 || REVIT2014)
        public void Application_ElementTypeDuplicating(object sender, ElementTypeDuplicatingEventArgs e) {
            var doc = e.Document;
            string typeCategory = string.Empty;
            string origTypeName = string.Empty;

            if (doc != null) {
                if (e.ElementTypeId != ElementId.InvalidElementId) {
                    var origType = doc.GetElement(e.ElementTypeId);
                    if (origType != null) {
                        origTypeName = origType.Name;
                        typeCategory = origType.Category != null ? origType.Category.Name : "";
                    }
                }
            }

            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_ElementTypeDuplicating),
                docname = doc != null ? doc.Title : "",
                docpath = doc != null ? doc.PathName : "",
                args = new Dictionary<string, object> {
                    { "category", typeCategory },
                    { "from_typename", origTypeName },
                }
            }, sender, e);
        }

        public void Application_ElementTypeDuplicated(object sender, ElementTypeDuplicatedEventArgs e) {
            var doc = e.Document;
            string typeCategory = string.Empty;
            string origTypeName = string.Empty;

            if (doc != null) {
                if (e.OriginalElementTypeId != ElementId.InvalidElementId) {
                    var origType = doc.GetElement(e.OriginalElementTypeId);
                    if (origType != null) {
                        origTypeName = origType.Name;
                        typeCategory = origType.Category != null ? origType.Category.Name : "";
                    }
                }
            }

            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_ElementTypeDuplicated),
                docname = doc != null ? doc.Title : "",
                docpath = doc != null ? doc.PathName : "",
                projectnum = GetProjectNumber(doc),
                projectname = GetProjectName(doc),
                status = e.Status.ToString(),
                args = new Dictionary<string, object> {
                    { "category", typeCategory },
                    { "from_typename", origTypeName },
                    { "to_typename", e.NewName },
                    { "to_typeid", e.NewElementTypeId.IntegerValue },
                }
            }, sender, e);
        }

        public void Application_DocumentWorksharingEnabled(object sender, DocumentWorksharingEnabledEventArgs e) {
            var doc = e.GetDocument();
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_DocumentWorksharingEnabled),
                docname = doc != null ? doc.Title : "",
                docpath = doc != null ? doc.PathName : "",
                projectnum = GetProjectNumber(doc),
                projectname = GetProjectName(doc),
            }, sender, e);
        }
#endif

        public void Application_DocumentSynchronizingWithCentral(object sender, DocumentSynchronizingWithCentralEventArgs e) {
            var syncOpts = e.Options;
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_DocumentSynchronizingWithCentral),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                projectnum = GetProjectNumber(e.Document),
                projectname = GetProjectName(e.Document),
                args = new Dictionary<string, object> {
                    { "comments", e.Comments },
                    { "location", e.Location },
                    { "options", new Dictionary<string,object> {
#if !(REVIT2013)
                        { "comment", syncOpts.Comment },
                        { "compact", syncOpts.Compact },
#else
                        { "comment", null },
                        { "compact", null },
#endif
                        { "relinquish_borrowed", syncOpts.RelinquishBorrowedElements },
                        { "relinquish_family_worksets", syncOpts.RelinquishFamilyWorksets },
                        { "relinquish_projectstd_worksets", syncOpts.RelinquishProjectStandardWorksets },
                        { "relinquish_user_worksets", syncOpts.RelinquishUserCreatedWorksets },
                        { "relinquish_view_worksets", syncOpts.RelinquishViewWorksets },
#if !(REVIT2013)
                        { "save_local_after", syncOpts.SaveLocalAfter },
                        { "save_local_before", syncOpts.SaveLocalBefore },
#else
                        { "save_local_after", null },
                        { "save_local_before", null },
#endif
                    } },
                }
            }, sender, e);
        }

        public void Application_DocumentSynchronizedWithCentral(object sender, DocumentSynchronizedWithCentralEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_DocumentSynchronizedWithCentral),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                projectnum = GetProjectNumber(e.Document),
                projectname = GetProjectName(e.Document),
                args = new Dictionary<string, object> {
                    { "status", e.Status.ToString() },
                }
            }, sender, e);
        }

        public void Application_DocumentSavingAs(object sender, DocumentSavingAsEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_DocumentSavingAs),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                projectnum = GetProjectNumber(e.Document),
                projectname = GetProjectName(e.Document),
                args = new Dictionary<string, object> {
#if (REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017 || REVIT2018 || REVIT2019 || REVIT2020 || REVIT2021_0)
                    { "as_master_file", e.IsSavingAsMasterFile },
#else
                    // this change was made in Revit 2021.1
                    { "as_master_file", e.IsSavingAsCentralFile },
#endif
                    { "path", e.PathName },
                }
            }, sender, e);
        }

        public void Application_DocumentSavedAs(object sender, DocumentSavedAsEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_DocumentSavedAs),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                projectnum = GetProjectNumber(e.Document),
                projectname = GetProjectName(e.Document),
                status = e.Status.ToString(),
                args = new Dictionary<string, object> {
#if (REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017 || REVIT2018 || REVIT2019 || REVIT2020 || REVIT2021_0)
                    { "as_master_file", e.IsSavingAsMasterFile },
#else
                    // this change was made in Revit 2021.1
                    { "as_master_file", e.IsSavingAsCentralFile },
#endif
                    { "original_path",  e.OriginalPath },
                    { "project_info", GetProjectInfo(e.Document) }
                }
            }, sender, e);
        }

        public void Application_DocumentSaving(object sender, DocumentSavingEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_DocumentSaving),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                projectnum = GetProjectNumber(e.Document),
                projectname = GetProjectName(e.Document),
            }, sender, e);
        }

        public void Application_DocumentSaved(object sender, DocumentSavedEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_DocumentSaved),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                projectnum = GetProjectNumber(e.Document),
                projectname = GetProjectName(e.Document),
                status = e.Status.ToString(),
                args = new Dictionary<string, object> {
                    { "project_info", GetProjectInfo(e.Document) }
                }
            }, sender, e);
        }

        public void Application_DocumentPrinting(object sender, DocumentPrintingEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_DocumentPrinting),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                projectnum = GetProjectNumber(e.Document),
                projectname = GetProjectName(e.Document),
                args = new Dictionary<string, object> {
                { "views", GetViewsData(GetElements(e.Document, e.GetViewElementIds())) },
#if !(REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016)
                { "settings", GetPrintSettings(e.GetSettings().PrintParameters) },
#else
                { "settings", null },
#endif
                }
            }, sender, e);
        }

        public void Application_DocumentPrinted(object sender, DocumentPrintedEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_DocumentPrinted),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                projectnum = GetProjectNumber(e.Document),
                projectname = GetProjectName(e.Document),
                status = e.Status.ToString(),
                args = new Dictionary<string, object> {
                    { "print_pass_views", GetViewsData(GetElements(e.Document, e.GetPrintedViewElementIds())) },
                    { "print_fail_views",  GetViewsData(GetElements(e.Document, e.GetFailedViewElementIds())) },
                }
            }, sender, e);
        }

        public void Application_DocumentOpening(object sender, DocumentOpeningEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_DocumentOpening),
                doctype = e.DocumentType.ToString(),
                docpath = e.PathName,
            }, sender, e);
        }

        public void Application_DocumentOpened(object sender, DocumentOpenedEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_DocumentOpened),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                projectnum = GetProjectNumber(e.Document),
                projectname = GetProjectName(e.Document),
                status = e.Status.ToString(),
                args = new Dictionary<string, object> {
                    { "project_info", GetProjectInfo(e.Document) }
                }
            }, sender, e);
        }

        public void Application_DocumentCreating(object sender, DocumentCreatingEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_DocumentCreating),
                doctype = e.DocumentType.ToString(),
                doctemplate = e.Template,
            }, sender, e);
        }

        public void Application_DocumentCreated(object sender, DocumentCreatedEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_DocumentCreated),
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                projectnum = GetProjectNumber(e.Document),
                projectname = GetProjectName(e.Document),
                status = e.Status.ToString(),
                args = new Dictionary<string, object> {
                    { "project_info", GetProjectInfo(e.Document) }
                }
            }, sender, e);
        }

        public void Application_DocumentClosing(object sender, DocumentClosingEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_DocumentClosing),
                docid = e.DocumentId,
                docname = e.Document != null ? e.Document.Title : "",
                docpath = e.Document != null ? e.Document.PathName : "",
                projectnum = GetProjectNumber(e.Document),
                projectname = GetProjectName(e.Document),
            }, sender, e);
        }

        public void Application_DocumentClosed(object sender, DocumentClosedEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_DocumentClosed),
                docid = e.DocumentId,
                status = e.Status.ToString(),
            }, sender, e);
        }

        public void Application_DocumentChanged(object sender, DocumentChangedEventArgs e) {
            var doc = e.GetDocument();
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_DocumentChanged),
                docname = doc != null ? doc.Title : "",
                docpath = doc != null ? doc.PathName : "",
                projectnum = GetProjectNumber(doc),
                projectname = GetProjectName(doc),
                args = new Dictionary<string, object> {
                    { "operation",  e.Operation.ToString() },
                    { "added",  e.GetAddedElementIds().Count },
                    { "deleted",  e.GetDeletedElementIds().Count },
                    { "modified",  e.GetModifiedElementIds().Count },
                    { "txn_names",  e.GetTransactionNames().ToList() },
                }
            }, sender, e);
        }

        public void Application_ApplicationInitialized(object sender, ApplicationInitializedEventArgs e) {
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_ApplicationInitialized),
            }, sender, e);
        }

#if !(REVIT2013)
        public void AddInCommandBinding_BeforeExecuted(object sender, BeforeExecutedEventArgs e) {
            var doc = e.ActiveDocument;
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.AddInCommandBinding_BeforeExecuted),
                docname = doc != null ? doc.Title : "",
                docpath = doc != null ? doc.PathName : "",
                projectnum = GetProjectNumber(doc),
                projectname = GetProjectName(doc),
                args = new Dictionary<string, object> {
                    { "command_id",  e.CommandId.Name },
                }
            }, sender, e);
        }
#endif

        public void AddInCommandBinding_CanExecute(object sender, CanExecuteEventArgs e) {
            // do nothing. no interesting telemetry data
        }

        public void AddInCommandBinding_Executed(object sender, ExecutedEventArgs e) {
            // do nothing. no interesting telemetry data
        }

        // custom events being called from non-main thread
        public void Application_JournalUpdated(object sender, JournalUpdateArgs e) {
            // do nothing. no interesting telemetry data
        }

        public void Application_JournalCommandExecuted(object sender, CommandExecutedArgs e) {
            if (extTelemetryEvent != null) {
                extTelemetryEventHandler.Sender = sender;
                extTelemetryEventHandler.CommandExecArgs = e;
                extTelemetryEventHandler.EventTelemetryDelegate = SendJournalCommandExecutedTelemetry;

                extTelemetryEvent.Raise();
                while (extTelemetryEvent.IsPending);
            }
        }

        public void SendJournalCommandExecutedTelemetry(UIApplication uiapp, object sender, object e) {
            // grab document data
            var doc = uiapp.ActiveUIDocument != null ? uiapp.ActiveUIDocument.Document : null;

            // get args
            CommandExecutedArgs args = e as CommandExecutedArgs;

            // send event info
            LogEventTelemetryRecord(new EventTelemetryRecord {
                type = EventUtils.GetEventName(EventType.Application_JournalCommandExecuted),
                docname = doc != null ? doc.Title : "",
                docpath = doc != null ? doc.PathName : "",
                projectnum = GetProjectNumber(doc),
                projectname = GetProjectName(doc),
                args = new Dictionary<string, object> {
                        { "command_id",  args.CommandId },
                    }
            }, uiapp, args);
        }
    }
}