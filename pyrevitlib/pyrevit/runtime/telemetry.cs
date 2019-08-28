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

using pyRevitLabs.NLog;
using pyRevitLabs.Common;

using pyRevitLabs.PyRevit;

namespace PyRevitLabs.PyRevit.Runtime {
    public class EngineInfo {
        public string type { get; set; }
        public string version { get; set; }
        public List<string> syspath { get; set; }
        public Dictionary<string, string> configs { get; set; }
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

            var env = new EnvDictionary();
            if (env.TelemetryUTCTimeStamps)
                timestamp = CommonUtils.GetISOTimeStampNow();
            else
                timestamp = CommonUtils.GetISOTimeStampLocalNow();
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
            httpWebRequest.UserAgent = PyRevitLabsConsts.ProductName;

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
        private static ScriptTelemetryRecord MakeTelemetryRecord(ref ScriptRuntime runtime) {
            // setup a new telemetry record
            return new ScriptTelemetryRecord {
                username = runtime.App.Username,
                revit = runtime.App.VersionNumber,
                revitbuild = runtime.App.VersionBuild,
                sessionid = runtime.SessionUUID,
                pyrevit = runtime.PyRevitVersion,
                clone = runtime.CloneName,
                debug = runtime.ScriptRuntimeConfigs.DebugMode,
                config = runtime.ScriptRuntimeConfigs.ConfigMode,
                from_gui = runtime.ScriptRuntimeConfigs.ExecutedFromUI,
                commandname = runtime.ScriptData.CommandName,
                commandbundle = runtime.ScriptData.CommandBundle,
                commandextension = runtime.ScriptData.CommandExtension,
                commanduniquename = runtime.ScriptData.CommandUniqueId,
                scriptpath = runtime.ScriptSourceFile,
                docname = runtime.DocumentName,
                docpath = runtime.DocumentPath,
                resultcode = runtime.ExecutionResult,
                commandresults = runtime.GetResultsDictionary(),
                trace = new TraceInfo {
                    engine = new EngineInfo {
                        type = runtime.EngineType.ToString().ToLower(),
                        version = runtime.EngineVersion,
                        syspath = runtime.ScriptRuntimeConfigs.SearchPaths,
                        configs = new JavaScriptSerializer().Deserialize<Dictionary<string, string>>(runtime.ScriptRuntimeConfigs.EngineConfigs),
                    },
                    message = runtime.TraceMessage
                }
            };
        }

        public static void LogScriptTelemetryRecord(ref ScriptRuntime runtime) {
            var envDict = new EnvDictionary();

            var record = MakeTelemetryRecord(ref runtime);

            if (envDict.TelemetryState) {
                if (envDict.TelemetryState
                        && envDict.TelemetryServerUrl != null
                        && !string.IsNullOrEmpty(envDict.TelemetryServerUrl))
                    new Task(() =>
                        Telemetry.PostTelemetryRecord(envDict.TelemetryServerUrl, record)).Start();

                if (envDict.TelemetryState
                        && envDict.TelemetryFilePath != null
                        && !string.IsNullOrEmpty(envDict.TelemetryFilePath))
                    new Task(() =>
                        Telemetry.WriteTelemetryRecord(envDict.TelemetryFilePath, record)).Start();
            }
        }
    }

    public class EventTelemetryRecord {
        // schema
        public Dictionary<string, string> meta { get; private set; }

        public string handlerId { get; set; }

        // which event?
        public string type { get; set; }
        public Dictionary<string, object> args { get; set; }
        public string status { get; set; }

        // when?
        public string timestamp { get; set; }
        // by who?
        public string host_user { get; set; }
        public string username { get; set; }
        // on what?
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


        public EventTelemetryRecord() {
            meta = new Dictionary<string, string> {
                { "schema", "2.0"},
            };

            var env = new EnvDictionary();
            if (env.TelemetryUTCTimeStamps)
                timestamp = CommonUtils.GetISOTimeStampNow();
            else
                timestamp = CommonUtils.GetISOTimeStampLocalNow();
        }
    }

    public class EventTelemetry : IEventTypeHandler {
        static Logger logger = LogManager.GetCurrentClassLogger();

        public string HandlerId;

        public EventTelemetry(string handlerId) {
            if (handlerId == null)
                handlerId = Guid.NewGuid().ToString();
            HandlerId = handlerId;
        }

        public static void SetHostInfo(object sender, ref EventTelemetryRecord record) {
            // figure out who is the sender
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

            // set the host info based on the sender type
            record.host_user = UserEnv.GetLoggedInUserName();
            record.username = string.Empty;
            record.revit = string.Empty;
            record.revitbuild = string.Empty;

            if (uictrlapp != null) {
                record.revit = uictrlapp.ControlledApplication.VersionNumber;
                record.revitbuild = uictrlapp.ControlledApplication.VersionBuild;
            }
            else if (uiapp != null && uiapp.Application != null) {
                record.username = uiapp.Application.Username;
                record.revit = uiapp.Application.VersionNumber;
                record.revitbuild = uiapp.Application.VersionBuild;
            }
            else if (ctrlapp != null) {
                record.revit = ctrlapp.VersionNumber;
                record.revitbuild = ctrlapp.VersionBuild;
            }
            else if (app != null) {
                record.username = app.Username;
                record.revit = app.VersionNumber;
                record.revitbuild = app.VersionBuild;
            }
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
            SetHostInfo(sender, ref eventTelemetryRecord);
            // set pyrevit info
            eventTelemetryRecord.handlerId = HandlerId;
            // event general info
            eventTelemetryRecord.cancellable = ((RevitAPIEventArgs)args).Cancellable;
            eventTelemetryRecord.cancelled = ((RevitAPIEventArgs)args).IsCancelled();

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
                if ((flags & (new BigInteger(1) << (int)eventType)) > 0)
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
                    { "as_master_file", e.IsSavingAsMasterFile },
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
                    { "as_master_file", e.IsSavingAsMasterFile },
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
    }
}
