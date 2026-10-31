using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;

using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Serves <c>capture</c>: a PNG of a view, so an agent can check what it built.
    /// </summary>
    /// <remarks>
    /// Three modes:
    /// <list type="bullet">
    /// <item><c>export</c> renders a view through <see cref="Document.ExportImage"/>. It works for any
    /// view, open or not, and doesn't depend on the Revit window.</item>
    /// <item><c>viewport</c> renders an open view through the same export, cropped to the region
    /// its window shows right now, so the image matches the user's zoom and pan without reading
    /// the screen. The crop happens in a transaction group that is always rolled back. It shows
    /// no selection highlight.</item>
    /// <item><c>screen</c> copies the active view's window from the screen: exactly what the user
    /// sees, including selection and temporary hide/isolate. It fails with <c>view_obscured</c>
    /// when another application's window covers the view, so it never returns that
    /// application's pixels. Revit's own floating windows over the view are captured as seen.</item>
    /// </list>
    /// The <c>3d</c> view is a temporary view created inside a transaction group that is
    /// always rolled back. It shows model categories only. By default it is isometric, looks from
    /// <c>direction</c>, and has a section box around the requested elements or, by default, the
    /// whole model, so the image frames the building instead of level and grid extents.
    /// <c>eye</c> and <c>target</c> make it a perspective view from that camera instead, without a
    /// section box. <c>section</c> makes it a temporary section or elevation (horizontal normal) or
    /// a plan cut at the origin's height (normal straight down), framed on the same elements.
    /// <c>detail_level</c> and <c>display_style</c> apply to the temporary view and, for named
    /// views in <c>export</c> and <c>viewport</c> modes, to the view for the capture only: a
    /// view template that controls them is detached inside the rolled-back group.
    /// Invariant: capturing never leaves a change in the model.
    /// </remarks>
    internal static class AgentCapture {
        private const int DefaultWidth = 1280;
        private const int MinWidth = 320;
        private const int MaxWidth = 2400;

        private const double SectionBoxPadding = 2.0;
        private const double DirectionTolerance = 1e-3;
        private const double MinSectionDepth = 1.0;
        private const int DwmaCloaked = 14;
        private const int DwmaExtendedFrameBounds = 9;

        private delegate bool EnumWindowsProc(IntPtr window, IntPtr parameter);

        [DllImport("user32.dll")]
        private static extern bool EnumWindows(EnumWindowsProc callback, IntPtr parameter);

        [DllImport("user32.dll")]
        private static extern bool IsWindowVisible(IntPtr window);

        [DllImport("user32.dll")]
        private static extern bool IsIconic(IntPtr window);

        [DllImport("dwmapi.dll")]
        private static extern int DwmGetWindowAttribute(IntPtr window, int attribute, out int value, int size);

        [DllImport("dwmapi.dll")]
        private static extern int DwmGetWindowAttribute(IntPtr window, int attribute, out NativeRect value, int size);

        [DllImport("user32.dll")]
        private static extern uint GetWindowThreadProcessId(IntPtr window, out uint processId);

        [StructLayout(LayoutKind.Sequential)]
        private struct NativeRect {
            public int Left;
            public int Top;
            public int Right;
            public int Bottom;
        }

        [DllImport("user32.dll")]
        private static extern bool GetWindowRect(IntPtr window, out NativeRect rect);

        [DllImport("user32.dll")]
        private static extern IntPtr SetThreadDpiAwarenessContext(IntPtr dpiContext);

        private static readonly Dictionary<string, XYZ> Directions = new Dictionary<string, XYZ>(StringComparer.OrdinalIgnoreCase) {
            ["southeast"] = new XYZ(-1, 1, -1),
            ["southwest"] = new XYZ(1, 1, -1),
            ["northeast"] = new XYZ(-1, -1, -1),
            ["northwest"] = new XYZ(1, -1, -1),
            ["south"] = new XYZ(0, 1, -0.6),
            ["north"] = new XYZ(0, -1, -0.6),
            ["east"] = new XYZ(-1, 0, -0.6),
            ["west"] = new XYZ(1, 0, -0.6),
            ["top"] = new XYZ(0, 0.0001, -1),
        };

        private static readonly Dictionary<string, ViewDetailLevel> DetailLevels = new Dictionary<string, ViewDetailLevel> {
            ["coarse"] = ViewDetailLevel.Coarse,
            ["medium"] = ViewDetailLevel.Medium,
            ["fine"] = ViewDetailLevel.Fine,
        };

        private static readonly Dictionary<string, DisplayStyle> DisplayStyles = new Dictionary<string, DisplayStyle> {
            ["wireframe"] = DisplayStyle.Wireframe,
            ["hidden_line"] = DisplayStyle.HLR,
            ["shaded"] = DisplayStyle.Shading,
            ["shaded_edges"] = DisplayStyle.ShadingWithEdges,
        };

        public sealed class SectionPlane {
            public XYZ Origin;
            public XYZ Normal;
            public double? Depth;

            public bool IsPlan => Math.Abs(Normal.X) < DirectionTolerance && Math.Abs(Normal.Y) < DirectionTolerance;
        }

        public sealed class Request {
            public string View;
            public string Mode;
            public int Width;
            public string Direction;
            public List<ElementId> Elements;
            public string DetailLevel;
            public string DisplayStyle;
            public XYZ Eye;
            public XYZ Target;
            public SectionPlane Section;

            public bool OverridesDisplay => DetailLevel != null || DisplayStyle != null;
        }

        public static Request Parse(JObject parameters) {
            var mode = (parameters.Value<string>("mode") ?? "export").ToLowerInvariant();
            if (mode != "export" && mode != "viewport" && mode != "screen")
                throw new AgentException("invalid_params", "'mode' must be export, viewport or screen.");

            var width = parameters.Value<int?>("width") ?? DefaultWidth;
            var direction = parameters.Value<string>("direction") ?? "southeast";
            if (!Directions.ContainsKey(direction))
                throw new AgentException("invalid_params", "'direction' must be one of: " + string.Join(", ", Directions.Keys) + ".");
            var request = new Request {
                View = string.IsNullOrWhiteSpace(parameters.Value<string>("view")) ? "active" : parameters.Value<string>("view").Trim(),
                Mode = mode,
                Width = Math.Max(MinWidth, Math.Min(MaxWidth, width)),
                Direction = direction,
                Elements = (parameters["elements"] as JArray)?.Select(id => AgentIds.FromValue(id.Value<long>())).ToList(),
                DetailLevel = ParseChoice(parameters, "detail_level", DetailLevels.Keys),
                DisplayStyle = ParseChoice(parameters, "display_style", DisplayStyles.Keys),
                Eye = ParsePoint(parameters["eye"], "eye"),
                Target = ParsePoint(parameters["target"], "target"),
                Section = ParseSection(parameters["section"]),
            };
            ValidateCombination(request);
            return request;
        }

        private static void ValidateCombination(Request request) {
            if ((request.Eye == null) != (request.Target == null))
                throw new AgentException("invalid_params", "'eye' and 'target' must be given together.");
            if (request.Eye != null && request.Eye.DistanceTo(request.Target) < DirectionTolerance)
                throw new AgentException("invalid_params", "'eye' and 'target' must be different points.");
            if (request.Eye != null && request.Section != null)
                throw new AgentException("invalid_params", "'section' and 'eye'/'target' can't be combined; each defines the camera.");
            if ((request.Eye != null || request.Section != null) && !string.Equals(request.View, "3d", StringComparison.OrdinalIgnoreCase))
                throw new AgentException("invalid_params", "'eye', 'target' and 'section' need view '3d'.");
            if ((request.Eye != null || request.Section != null) && request.Mode != "export")
                throw new AgentException("invalid_params", "'eye', 'target' and 'section' need mode 'export'.");
            if (request.OverridesDisplay && request.Mode == "screen")
                throw new AgentException("invalid_params", "'detail_level' and 'display_style' don't apply to mode 'screen', which copies the window as it is.");
        }

        private static string ParseChoice(JObject parameters, string name, IEnumerable<string> choices) {
            var token = parameters[name];
            if (token == null || token.Type == JTokenType.Null)
                return null;
            if (token.Type != JTokenType.String)
                throw new AgentException("invalid_params", $"'{name}' must be a string.");
            var value = token.Value<string>();
            if (string.IsNullOrWhiteSpace(value))
                return null;
            var normalized = value.Trim().ToLowerInvariant();
            if (!choices.Contains(normalized))
                throw new AgentException("invalid_params", $"'{name}' must be one of: {string.Join(", ", choices)}.");
            return normalized;
        }

        private static XYZ ParsePoint(JToken token, string name) {
            if (token == null || token.Type == JTokenType.Null)
                return null;
            var coordinates = token as JArray;
            if (coordinates == null || coordinates.Count != 3 || !coordinates.All(IsFiniteNumber))
                throw new AgentException("invalid_params", $"'{name}' must be [x, y, z] in feet.");
            return new XYZ(coordinates[0].Value<double>(), coordinates[1].Value<double>(), coordinates[2].Value<double>());
        }

        private static bool IsFiniteNumber(JToken token) {
            if (token.Type != JTokenType.Float && token.Type != JTokenType.Integer)
                return false;
            var number = token.Value<double>();
            return !double.IsNaN(number) && !double.IsInfinity(number);
        }

        private static SectionPlane ParseSection(JToken token) {
            if (token == null || token.Type == JTokenType.Null)
                return null;
            var plane = token as JObject
                ?? throw new AgentException("invalid_params", "'section' must be an object with 'origin', 'normal' and optional 'depth'.");
            var origin = ParsePoint(plane["origin"], "section.origin")
                ?? throw new AgentException("invalid_params", "'section.origin' is required.");
            var normal = ParsePoint(plane["normal"], "section.normal")
                ?? throw new AgentException("invalid_params", "'section.normal' is required.");
            if (normal.IsZeroLength())
                throw new AgentException("invalid_params", "'section.normal' must not be a zero vector.");
            normal = normal.Normalize();

            double? depth = null;
            var depthToken = plane["depth"];
            if (depthToken != null && depthToken.Type != JTokenType.Null) {
                if (!IsFiniteNumber(depthToken) || depthToken.Value<double>() <= 0)
                    throw new AgentException("invalid_params", "'section.depth' must be a number greater than zero.");
                depth = depthToken.Value<double>();
            }

            var isHorizontal = Math.Abs(normal.Z) < DirectionTolerance;
            var isPlanDown = Math.Abs(normal.X) < DirectionTolerance && Math.Abs(normal.Y) < DirectionTolerance && normal.Z < 0;
            if (!isHorizontal && !isPlanDown)
                throw new AgentException("invalid_params",
                    "'section.normal' must be horizontal (section or elevation looking along it) or [0, 0, -1] (plan looking down).");
            var snapped = isHorizontal ? new XYZ(normal.X, normal.Y, 0).Normalize() : XYZ.BasisZ.Negate();
            return new SectionPlane { Origin = origin, Normal = snapped, Depth = depth };
        }

        public static JToken Capture(UIApplication app, Request request) {
            var uidoc = app.ActiveUIDocument
                ?? throw new AgentException("no_active_document", "Revit has no active document.");
            var doc = uidoc.Document;
            if (doc.IsModifiable)
                throw AgentException.NotRun("Another transaction is open in the active document.");

            var directory = AgentPaths.CapturesDir;
            Directory.CreateDirectory(directory);
            var baseName = DateTime.Now.ToString("yyyyMMdd-HHmmss") + "-" + Guid.NewGuid().ToString("N").Substring(0, 6);

            string path;
            View captured;
            if (request.Mode == "screen") {
                captured = ResolveView(doc, uidoc, request.View);
                path = CaptureScreen(uidoc, captured, Path.Combine(directory, baseName + ".png"));
            }
            else if (request.Mode == "viewport") {
                captured = ResolveView(doc, uidoc, request.View);
                path = ExportViewport(uidoc, captured, directory, baseName, request);
            }
            else if (string.Equals(request.View, "3d", StringComparison.OrdinalIgnoreCase)) {
                captured = null;
                path = ExportTemporary(doc, directory, baseName, request);
            }
            else {
                captured = ResolveView(doc, uidoc, request.View);
                path = ExportWithDisplay(doc, captured, directory, baseName, request);
            }

            ScaleDown(path, request.Width, out var width, out var height);
            var result = new JObject {
                ["mode"] = request.Mode,
                ["view"] = captured == null
                    ? DescribeTemporary(request)
                    : new JObject {
                        ["id"] = AgentIds.ToValue(captured.Id),
                        ["name"] = captured.Name,
                        ["type"] = captured.ViewType.ToString(),
                    },
                ["path"] = path,
                ["width"] = width,
                ["height"] = height,
                ["image_base64"] = Convert.ToBase64String(File.ReadAllBytes(path)),
            };
            if (request.DetailLevel != null)
                result["detail_level"] = request.DetailLevel;
            if (request.DisplayStyle != null)
                result["display_style"] = request.DisplayStyle;
            return result;
        }

        private static JObject DescribeTemporary(Request request) {
            if (request.Section != null)
                return new JObject {
                    ["name"] = request.Section.IsPlan ? "temporary plan" : "temporary section",
                    ["type"] = request.Section.IsPlan ? "FloorPlan" : "Section",
                    ["origin"] = PointArray(request.Section.Origin),
                    ["normal"] = PointArray(request.Section.Normal),
                };
            if (request.Eye != null)
                return new JObject {
                    ["name"] = "temporary perspective 3D view",
                    ["type"] = "ThreeD",
                    ["eye"] = PointArray(request.Eye),
                    ["target"] = PointArray(request.Target),
                };
            return new JObject { ["name"] = "temporary isometric 3D view", ["type"] = "ThreeD", ["direction"] = request.Direction };
        }

        private static JArray PointArray(XYZ point) => new JArray(point.X, point.Y, point.Z);

        private static View ResolveView(Document doc, UIDocument uidoc, string selector) {
            if (string.Equals(selector, "active", StringComparison.OrdinalIgnoreCase))
                return uidoc.ActiveView;

            if (long.TryParse(selector, out var idValue)) {
                if (doc.GetElement(AgentIds.FromValue(idValue)) is View byId && !byId.IsTemplate)
                    return byId;
                throw new AgentException("view_not_found", $"No view with id {selector}.");
            }

            var byName = new FilteredElementCollector(doc)
                .OfClass(typeof(View))
                .Cast<View>()
                .Where(view => !view.IsTemplate && string.Equals(view.Name, selector, StringComparison.OrdinalIgnoreCase))
                .ToList();
            if (byName.Count == 0)
                throw new AgentException("view_not_found", $"No view named '{selector}'. Use 'active', '3d', a view name or a view id.");
            return byName[0];
        }

        private static string ExportView(Document doc, View view, string directory, string baseName, int width) {
            if (!view.CanBePrinted)
                throw new AgentException("view_not_supported", $"View '{view.Name}' ({view.ViewType}) can't be exported as an image.");

            var options = new ImageExportOptions {
                ExportRange = ExportRange.SetOfViews,
                FilePath = Path.Combine(directory, baseName),
                HLRandWFViewsFileType = ImageFileType.PNG,
                ShadowViewsFileType = ImageFileType.PNG,
                ImageResolution = ImageResolution.DPI_150,
                ZoomType = ZoomFitType.FitToPage,
                FitDirection = FitDirectionType.Horizontal,
                PixelSize = width,
            };
            options.SetViewsAndSheets(new List<ElementId> { view.Id });
            doc.ExportImage(options);

            return Directory.GetFiles(directory, baseName + "*.png")
                .OrderByDescending(File.GetLastWriteTimeUtc)
                .FirstOrDefault()
                ?? throw new AgentException("capture_failed", $"Revit did not write an image for view '{view.Name}'.");
        }

        private static string ExportWithDisplay(Document doc, View view, string directory, string baseName, Request request) {
            if (!request.OverridesDisplay)
                return ExportView(doc, view, directory, baseName, request.Width);
            if (doc.IsReadOnly)
                throw new AgentException("document_read_only", "'detail_level' and 'display_style' change the view temporarily, which a read-only document doesn't allow.");

            using (var group = new TransactionGroup(doc, "pyRevit Agent capture")) {
                group.Start();
                try {
                    using (var transaction = new Transaction(doc, "pyRevit Agent display override")) {
                        transaction.Start();
                        OverrideDisplay(view, request.DetailLevel, request.DisplayStyle);
                        transaction.Commit();
                    }
                    return ExportView(doc, view, directory, baseName, request.Width);
                }
                catch (Autodesk.Revit.Exceptions.ApplicationException ex) {
                    throw new AgentException("capture_failed", $"View '{view.Name}' could not be shown with the requested display settings: {ex.Message}");
                }
                finally {
                    if (group.HasStarted() && !group.HasEnded())
                        group.RollBack();
                }
            }
        }

        /// <remarks>
        /// A view template that controls the detail level or display style would reject the change,
        /// so the template is detached first. Only valid inside the rolled-back capture group.
        /// </remarks>
        private static void OverrideDisplay(View view, string detailLevel, string displayStyle) {
            if (detailLevel == null && displayStyle == null)
                return;
            if (view is ViewSheet || view is ViewSchedule)
                throw new AgentException("view_not_supported",
                    $"View '{view.Name}' ({view.ViewType}) has no detail level or display style.");
            if (view.ViewTemplateId != ElementId.InvalidElementId)
                view.ViewTemplateId = ElementId.InvalidElementId;
            ApplyDisplay(view, detailLevel, displayStyle);
        }

        private static void ApplyDisplay(View view, string detailLevel, string displayStyle) {
            if (displayStyle != null)
                view.DisplayStyle = DisplayStyles[displayStyle];
            if (detailLevel != null)
                view.DetailLevel = DetailLevels[detailLevel];
        }

        private static string ExportViewport(UIDocument uidoc, View view, string directory, string baseName, Request request) {
            var doc = uidoc.Document;
            if (view is ViewSheet || view is ViewSchedule || (view is View3D view3D && view3D.IsPerspective))
                throw new AgentException("view_not_supported",
                    $"View '{view.Name}' ({view.ViewType}) can't be cropped to its on-screen region; use mode 'export' or 'screen'.");
            if (doc.IsReadOnly)
                throw new AgentException("document_read_only", "Mode 'viewport' crops the view temporarily, which a read-only document doesn't allow.");
            var uiView = uidoc.GetOpenUIViews().FirstOrDefault(open => open.ViewId == view.Id)
                ?? throw new AgentException("view_not_open", $"View '{view.Name}' is not open in Revit; use mode 'export' or open the view.");

            var corners = uiView.GetZoomCorners();
            using (var group = new TransactionGroup(doc, "pyRevit Agent capture")) {
                group.Start();
                try {
                    using (var transaction = new Transaction(doc, "pyRevit Agent crop to viewport")) {
                        transaction.Start();
                        OverrideDisplay(view, request.DetailLevel, request.DisplayStyle);
                        CropToCorners(view, corners[0], corners[1]);
                        transaction.Commit();
                    }
                    return ExportView(doc, view, directory, baseName, request.Width);
                }
                catch (Autodesk.Revit.Exceptions.ApplicationException ex) {
                    throw new AgentException("capture_failed",
                        $"View '{view.Name}' could not be cropped to its on-screen region: {ex.Message} Use mode 'export' or 'screen'.");
                }
                finally {
                    if (group.HasStarted() && !group.HasEnded())
                        group.RollBack();
                }
            }
        }

        /// <remarks>
        /// The zoom corners are model points; the crop box lives in its own coordinate system,
        /// so they are mapped through the inverse of its transform. A scope box or a
        /// non-rectangular crop would override or reject the new box, so both are released
        /// first; the caller's rollback restores them.
        /// </remarks>
        private static void CropToCorners(View view, XYZ first, XYZ second) {
            var scopeBox = view.get_Parameter(BuiltInParameter.VIEWER_VOLUME_OF_INTEREST_CROP);
            if (scopeBox != null && !scopeBox.IsReadOnly && scopeBox.AsElementId() != ElementId.InvalidElementId)
                scopeBox.Set(ElementId.InvalidElementId);
            var shapes = view.GetCropRegionShapeManager();
            if (shapes != null && shapes.ShapeSet)
                shapes.RemoveCropRegionShape();

            var crop = view.CropBox;
            var toCrop = crop.Transform.Inverse;
            var a = toCrop.OfPoint(first);
            var b = toCrop.OfPoint(second);
            view.CropBoxActive = true;
            view.CropBoxVisible = false;
            view.CropBox = new BoundingBoxXYZ {
                Transform = crop.Transform,
                Min = new XYZ(Math.Min(a.X, b.X), Math.Min(a.Y, b.Y), crop.Min.Z),
                Max = new XYZ(Math.Max(a.X, b.X), Math.Max(a.Y, b.Y), crop.Max.Z),
            };
        }

        private static string ExportTemporary(Document doc, string directory, string baseName, Request request) {
            if (doc.IsReadOnly)
                throw new AgentException("document_read_only", "A temporary view can't be created in a read-only document.");

            using (var group = new TransactionGroup(doc, "pyRevit Agent capture")) {
                group.Start();
                try {
                    View view;
                    using (var transaction = new Transaction(doc, "pyRevit Agent capture view")) {
                        transaction.Start();
                        view = CreateTemporary(doc, request);
                        ApplyDisplay(view, request.DetailLevel ?? "medium", request.DisplayStyle ?? "shaded_edges");
                        ShowModelOnly(doc, view);
                        transaction.Commit();
                    }
                    return ExportView(doc, view, directory, baseName, request.Width);
                }
                catch (Autodesk.Revit.Exceptions.ApplicationException ex) {
                    throw new AgentException("capture_failed", $"The temporary view could not be created: {ex.Message}");
                }
                finally {
                    if (group.HasStarted() && !group.HasEnded())
                        group.RollBack();
                }
            }
        }

        private static View CreateTemporary(Document doc, Request request) {
            if (request.Section == null)
                return CreateTemporary3D(doc, request);
            if (request.Section.IsPlan)
                return CreateTemporaryPlan(doc, request);
            return CreateTemporarySection(doc, request);
        }

        private static ViewFamilyType FindViewType(Document doc, ViewFamily family) =>
            new FilteredElementCollector(doc)
                .OfClass(typeof(ViewFamilyType))
                .Cast<ViewFamilyType>()
                .FirstOrDefault(type => type.ViewFamily == family)
            ?? throw new AgentException("view_not_supported", $"The document has no {family} view type.");

        private static View3D CreateTemporary3D(Document doc, Request request) {
            var viewType = FindViewType(doc, ViewFamily.ThreeDimensional);
            if (request.Eye != null) {
                var perspective = View3D.CreatePerspective(doc, viewType.Id);
                perspective.SetOrientation(Orientation(request.Eye, request.Target - request.Eye));
                return perspective;
            }

            var view = View3D.CreateIsometric(doc, viewType.Id);
            var direction = Directions[request.Direction];
            view.SetOrientation(Orientation(direction.Normalize().Negate().Multiply(1000), direction));
            var box = ModelBox(doc, view.Id, request.Elements);
            if (box != null) {
                view.SetSectionBox(box);
                view.IsSectionBoxActive = true;
                HideSectionBox(doc, view);
            }
            return view;
        }

        /// <remarks>
        /// The view looks along <c>Normal</c> from <c>Origin</c>. <c>CreateSection</c> takes the
        /// creation transform's Z axis as the look direction and mirrors it to the viewer-facing
        /// frame Revit reports, so the frame is built with Z along <c>Normal</c> and the visible
        /// slab is Z from 0 (the cut plane) to <c>depth</c>. Passing Z toward the viewer instead
        /// puts the viewer on the far side and the cut plane at the far clip.
        /// </remarks>
        private static ViewSection CreateTemporarySection(Document doc, Request request) {
            var plane = request.Section;
            var transform = Transform.Identity;
            transform.Origin = plane.Origin;
            transform.BasisX = XYZ.BasisZ.CrossProduct(plane.Normal).Normalize();
            transform.BasisY = XYZ.BasisZ;
            transform.BasisZ = plane.Normal;

            var model = ModelBox(doc, null, request.Elements)
                ?? throw new AgentException("capture_failed", "There are no model elements to frame in the section.");
            var toLocal = transform.Inverse;
            var local = Corners(model).Select(toLocal.OfPoint).ToList();
            var depth = plane.Depth ?? Math.Max(MinSectionDepth, local.Max(point => point.Z));
            var box = new BoundingBoxXYZ {
                Transform = transform,
                Min = new XYZ(local.Min(point => point.X), local.Min(point => point.Y), 0),
                Max = new XYZ(local.Max(point => point.X), local.Max(point => point.Y), depth),
            };

            var view = ViewSection.CreateSection(doc, FindViewType(doc, ViewFamily.Section).Id, box);
            view.CropBoxVisible = false;
            return view;
        }

        /// <remarks>
        /// The plan is cut at <c>Origin.Z</c> and looks down for <c>depth</c> feet, on the level
        /// at or below that height (or the lowest level). The view range is expressed relative to
        /// that level, so every clip plane is associated with it.
        /// </remarks>
        private static ViewPlan CreateTemporaryPlan(Document doc, Request request) {
            var plane = request.Section;
            var levels = new FilteredElementCollector(doc).OfClass(typeof(Level)).Cast<Level>().OrderBy(candidate => candidate.ProjectElevation).ToList();
            var level = levels.LastOrDefault(candidate => candidate.ProjectElevation <= plane.Origin.Z + DirectionTolerance)
                ?? levels.FirstOrDefault()
                ?? throw new AgentException("view_not_supported", "The document has no level to host a plan view.");

            var model = ModelBox(doc, null, request.Elements);
            var depth = plane.Depth ?? Math.Max(MinSectionDepth, model == null ? 0 : plane.Origin.Z - model.Min.Z);
            var cutOffset = plane.Origin.Z - level.ProjectElevation;

            var view = ViewPlan.Create(doc, FindViewType(doc, ViewFamily.FloorPlan).Id, level.Id);
            var range = view.GetViewRange();
            foreach (PlanViewPlane viewPlane in Enum.GetValues(typeof(PlanViewPlane)))
                range.SetLevelId(viewPlane, level.Id);
            range.SetOffset(PlanViewPlane.TopClipPlane, cutOffset);
            range.SetOffset(PlanViewPlane.CutPlane, cutOffset);
            range.SetOffset(PlanViewPlane.BottomClipPlane, cutOffset - depth);
            range.SetOffset(PlanViewPlane.ViewDepthPlane, cutOffset - depth);
            view.SetViewRange(range);

            if (model != null) {
                var crop = view.CropBox;
                crop.Min = new XYZ(model.Min.X, model.Min.Y, crop.Min.Z);
                crop.Max = new XYZ(model.Max.X, model.Max.Y, crop.Max.Z);
                view.CropBox = crop;
                view.CropBoxActive = true;
                view.CropBoxVisible = false;
            }
            return view;
        }

        private static IEnumerable<XYZ> Corners(BoundingBoxXYZ box) {
            foreach (var x in new[] { box.Min.X, box.Max.X })
                foreach (var y in new[] { box.Min.Y, box.Max.Y })
                    foreach (var z in new[] { box.Min.Z, box.Max.Z })
                        yield return new XYZ(x, y, z);
        }

        private static void ShowModelOnly(Document doc, View view) {
            foreach (Category category in doc.Settings.Categories) {
                if (category.CategoryType != CategoryType.Model && view.CanCategoryBeHidden(category.Id))
                    view.SetCategoryHidden(category.Id, true);
            }
        }

        private static void HideSectionBox(Document doc, View view) {
            var sectionBoxes = Category.GetCategory(doc, BuiltInCategory.OST_SectionBox);
            if (sectionBoxes != null && view.CanCategoryBeHidden(sectionBoxes.Id))
                view.SetCategoryHidden(sectionBoxes.Id, true);
        }

        private static ViewOrientation3D Orientation(XYZ eye, XYZ direction) {
            var forward = direction.Normalize();
            var right = forward.CrossProduct(XYZ.BasisZ);
            if (right.IsZeroLength())
                right = XYZ.BasisX;
            var up = right.Normalize().CrossProduct(forward).Normalize();
            return new ViewOrientation3D(eye, up, forward);
        }

        /// <remarks>
        /// With no <paramref name="viewId"/> the whole document is scanned, which a view that
        /// doesn't exist yet needs; otherwise only what that view shows counts. The document scan
        /// skips view-specific elements such as detail lines in drafting views, whose coordinates
        /// are not model coordinates and would stretch the frame away from the model.
        /// </remarks>
        private static BoundingBoxXYZ ModelBox(Document doc, ElementId viewId, List<ElementId> ids) {
            IEnumerable<Element> elements = ids != null && ids.Count > 0
                ? ids.Select(doc.GetElement).Where(element => element != null)
                : (viewId == null
                        ? new FilteredElementCollector(doc).WhereElementIsViewIndependent()
                        : new FilteredElementCollector(doc, viewId))
                    .WhereElementIsNotElementType()
                    .Where(element => element.Category != null
                                      && element.Category.CategoryType == CategoryType.Model
                                      && !(element is Level));

            double minX = double.MaxValue, minY = double.MaxValue, minZ = double.MaxValue;
            double maxX = double.MinValue, maxY = double.MinValue, maxZ = double.MinValue;
            var any = false;
            foreach (var element in elements) {
                var box = element.get_BoundingBox(null);
                if (box == null)
                    continue;
                any = true;
                minX = Math.Min(minX, box.Min.X);
                minY = Math.Min(minY, box.Min.Y);
                minZ = Math.Min(minZ, box.Min.Z);
                maxX = Math.Max(maxX, box.Max.X);
                maxY = Math.Max(maxY, box.Max.Y);
                maxZ = Math.Max(maxZ, box.Max.Z);
            }
            if (!any)
                return null;
            return new BoundingBoxXYZ {
                Min = new XYZ(minX - SectionBoxPadding, minY - SectionBoxPadding, minZ - SectionBoxPadding),
                Max = new XYZ(maxX + SectionBoxPadding, maxY + SectionBoxPadding, maxZ + SectionBoxPadding),
            };
        }

        private static string CaptureScreen(UIDocument uidoc, View view, string path) {
            var uiView = uidoc.GetOpenUIViews().FirstOrDefault(open => open.ViewId == view.Id)
                ?? throw new AgentException("view_not_open", $"View '{view.Name}' is not open in Revit; use mode 'export' or open the view.");

            uidoc.RefreshActiveView();
            var rectangle = uiView.GetWindowRectangle();
            if (rectangle.Right <= rectangle.Left || rectangle.Bottom <= rectangle.Top)
                throw new AgentException("capture_failed", "The view window has no visible area; is Revit minimized?");

            using (var screen = PhysicalScreen.Enter(uidoc.Application.MainWindowHandle)) {
                var left = screen.X(rectangle.Left);
                var top = screen.Y(rectangle.Top);
                var right = screen.X(rectangle.Right);
                var bottom = screen.Y(rectangle.Bottom);
                if (IsCoveredByOtherProcess(uidoc.Application.MainWindowHandle, left, top, right, bottom))
                    throw new AgentException("view_obscured",
                        $"Another application's window covers view '{view.Name}', so a screen capture would show it "
                        + "instead of the model; use mode 'export', or ask the user to bring Revit to the front.");

                using (var bitmap = new Bitmap(right - left, bottom - top, PixelFormat.Format24bppRgb))
                using (var graphics = Graphics.FromImage(bitmap)) {
                    graphics.CopyFromScreen(left, top, 0, 0, new Size(right - left, bottom - top));
                    bitmap.Save(path, ImageFormat.Png);
                }
            }
            return path;
        }

        /// <summary>
        /// Switches the calling thread to per-monitor DPI awareness and maps Revit's window
        /// coordinates to physical screen pixels until disposed.
        /// </summary>
        /// <remarks>
        /// Revit is system-DPI aware, so on a monitor scaled differently from the primary one
        /// Windows stretches its window and the Revit API reports coordinates in the stretched,
        /// logical space. Screen copies and <c>WindowFromPoint</c> need physical pixels, or they
        /// read the wrong part of the screen. The mapping is the affine one between the main
        /// window's rectangle measured in both modes, so it holds while Revit sits on one monitor.
        /// Invariant: the thread's previous DPI awareness is restored on dispose; Revit's main
        /// thread must not keep per-monitor awareness after the capture.
        /// On Windows builds without per-thread DPI awareness, coordinates pass through unchanged.
        /// </remarks>
        private sealed class PhysicalScreen : IDisposable {
            private static readonly IntPtr PerMonitorAwareV2 = new IntPtr(-4);

            private readonly IntPtr previousContext;
            private readonly NativeRect logical;
            private readonly NativeRect physical;

            private PhysicalScreen(IntPtr previousContext, NativeRect logical, NativeRect physical) {
                this.previousContext = previousContext;
                this.logical = logical;
                this.physical = physical;
            }

            public static PhysicalScreen Enter(IntPtr mainWindow) {
                GetWindowRect(mainWindow, out var logical);
                IntPtr previous;
                try {
                    previous = SetThreadDpiAwarenessContext(PerMonitorAwareV2);
                }
                catch (EntryPointNotFoundException) {
                    previous = IntPtr.Zero;
                }
                if (previous == IntPtr.Zero)
                    return new PhysicalScreen(IntPtr.Zero, logical, logical);

                GetWindowRect(mainWindow, out var physical);
                return new PhysicalScreen(previous, logical, physical);
            }

            public int X(int logicalX) =>
                Map(logicalX, logical.Left, logical.Right, physical.Left, physical.Right);

            public int Y(int logicalY) =>
                Map(logicalY, logical.Top, logical.Bottom, physical.Top, physical.Bottom);

            public void Dispose() {
                if (previousContext != IntPtr.Zero)
                    SetThreadDpiAwarenessContext(previousContext);
            }

            private static int Map(int value, int logicalStart, int logicalEnd, int physicalStart, int physicalEnd) {
                var logicalSpan = logicalEnd - logicalStart;
                if (logicalSpan <= 0)
                    return value;
                var scale = (physicalEnd - physicalStart) / (double)logicalSpan;
                return physicalStart + (int)Math.Round((value - logicalStart) * scale);
            }
        }

        /// <summary>
        /// Walks the top-level windows from the top of the z-order down to Revit's main window
        /// and reports whether a visible window of another process overlaps any part of the
        /// rectangle. Windows below Revit's main window are hidden by it.
        /// </summary>
        private static bool IsCoveredByOtherProcess(IntPtr mainWindow, int left, int top, int right, int bottom) {
            var revitProcessId = (uint)System.Diagnostics.Process.GetCurrentProcess().Id;
            var covered = false;
            EnumWindows((window, _) => {
                if (window == mainWindow)
                    return false;
                GetWindowThreadProcessId(window, out var owner);
                if (owner == revitProcessId || !IsWindowVisible(window) || IsIconic(window))
                    return true;
                int cloaked;
                if (DwmGetWindowAttribute(window, DwmaCloaked, out cloaked, sizeof(int)) == 0 && cloaked != 0)
                    return true;
                NativeRect bounds;
                if (DwmGetWindowAttribute(window, DwmaExtendedFrameBounds, out bounds, Marshal.SizeOf(typeof(NativeRect))) != 0
                    && !GetWindowRect(window, out bounds))
                    return true;
                if (bounds.Left < right && bounds.Right > left && bounds.Top < bottom && bounds.Bottom > top) {
                    covered = true;
                    return false;
                }
                return true;
            }, IntPtr.Zero);
            return covered;
        }

        private static void ScaleDown(string path, int maxWidth, out int width, out int height) {
            using (var original = Image.FromFile(path)) {
                width = original.Width;
                height = original.Height;
                if (original.Width <= maxWidth)
                    return;

                width = maxWidth;
                height = (int)Math.Round(original.Height * (maxWidth / (double)original.Width));
                using (var scaled = new Bitmap(width, height, PixelFormat.Format24bppRgb))
                using (var graphics = Graphics.FromImage(scaled)) {
                    graphics.InterpolationMode = InterpolationMode.HighQualityBicubic;
                    graphics.DrawImage(original, 0, 0, width, height);
                    var scaledPath = path + ".scaled.png";
                    scaled.Save(scaledPath, ImageFormat.Png);
                    original.Dispose();
                    File.Delete(path);
                    File.Move(scaledPath, path);
                }
            }
        }
    }
}
