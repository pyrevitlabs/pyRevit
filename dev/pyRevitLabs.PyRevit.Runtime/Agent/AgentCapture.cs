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
    /// The <c>3d</c> view is a temporary isometric view created inside a transaction group that is
    /// always rolled back. It shows model categories only, looks from <c>direction</c>, and has a
    /// section box around the requested elements or, by default, the whole model, so the image
    /// frames the building instead of level and grid extents.
    /// Invariant: capturing never leaves a change in the model.
    /// </remarks>
    internal static class AgentCapture {
        private const int DefaultWidth = 1280;
        private const int MinWidth = 320;
        private const int MaxWidth = 2400;

        private const double SectionBoxPadding = 2.0;
        private const int CoverageProbeInset = 4;

        [StructLayout(LayoutKind.Sequential)]
        private struct NativePoint {
            public int X;
            public int Y;
        }

        [DllImport("user32.dll")]
        private static extern IntPtr WindowFromPoint(NativePoint point);

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

        public sealed class Request {
            public string View;
            public string Mode;
            public int Width;
            public string Direction;
            public List<ElementId> Elements;
        }

        public static Request Parse(JObject parameters) {
            var mode = (parameters.Value<string>("mode") ?? "export").ToLowerInvariant();
            if (mode != "export" && mode != "viewport" && mode != "screen")
                throw new AgentException("invalid_params", "'mode' must be export, viewport or screen.");

            var width = parameters.Value<int?>("width") ?? DefaultWidth;
            var direction = parameters.Value<string>("direction") ?? "southeast";
            if (!Directions.ContainsKey(direction))
                throw new AgentException("invalid_params", "'direction' must be one of: " + string.Join(", ", Directions.Keys) + ".");
            return new Request {
                View = string.IsNullOrWhiteSpace(parameters.Value<string>("view")) ? "active" : parameters.Value<string>("view").Trim(),
                Mode = mode,
                Width = Math.Max(MinWidth, Math.Min(MaxWidth, width)),
                Direction = direction,
                Elements = (parameters["elements"] as JArray)?.Select(id => AgentIds.FromValue(id.Value<long>())).ToList(),
            };
        }

        public static JToken Capture(UIApplication app, Request request) {
            var uidoc = app.ActiveUIDocument
                ?? throw new AgentException("no_active_document", "Revit has no active document.");
            var doc = uidoc.Document;
            if (doc.IsModifiable)
                throw new AgentException("revit_busy", "Another transaction is open in the active document.");

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
                path = ExportViewport(uidoc, captured, directory, baseName, request.Width);
            }
            else if (string.Equals(request.View, "3d", StringComparison.OrdinalIgnoreCase)) {
                captured = null;
                path = ExportTemporary3D(doc, directory, baseName, request);
            }
            else {
                captured = ResolveView(doc, uidoc, request.View);
                path = ExportView(doc, captured, directory, baseName, request.Width);
            }

            ScaleDown(path, request.Width, out var width, out var height);
            return new JObject {
                ["mode"] = request.Mode,
                ["view"] = captured == null
                    ? new JObject { ["name"] = "temporary isometric 3D view", ["type"] = "ThreeD", ["direction"] = request.Direction }
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
        }

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

        private static string ExportViewport(UIDocument uidoc, View view, string directory, string baseName, int width) {
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
                        CropToCorners(view, corners[0], corners[1]);
                        transaction.Commit();
                    }
                    return ExportView(doc, view, directory, baseName, width);
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

        private static string ExportTemporary3D(Document doc, string directory, string baseName, Request request) {
            if (doc.IsReadOnly)
                throw new AgentException("document_read_only", "A temporary 3D view can't be created in a read-only document.");

            var viewType = new FilteredElementCollector(doc)
                .OfClass(typeof(ViewFamilyType))
                .Cast<ViewFamilyType>()
                .FirstOrDefault(type => type.ViewFamily == ViewFamily.ThreeDimensional)
                ?? throw new AgentException("view_not_supported", "The document has no 3D view type.");

            using (var group = new TransactionGroup(doc, "pyRevit Agent capture")) {
                group.Start();
                try {
                    View3D view;
                    using (var transaction = new Transaction(doc, "pyRevit Agent capture view")) {
                        transaction.Start();
                        view = View3D.CreateIsometric(doc, viewType.Id);
                        view.DisplayStyle = DisplayStyle.ShadingWithEdges;
                        view.DetailLevel = ViewDetailLevel.Medium;
                        ShowModelOnly(doc, view);
                        view.SetOrientation(Orientation(Directions[request.Direction]));
                        var box = ModelBox(doc, view, request.Elements);
                        if (box != null) {
                            view.SetSectionBox(box);
                            view.IsSectionBoxActive = true;
                            HideSectionBox(doc, view);
                        }
                        transaction.Commit();
                    }
                    return ExportView(doc, view, directory, baseName, request.Width);
                }
                finally {
                    if (group.HasStarted() && !group.HasEnded())
                        group.RollBack();
                }
            }
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

        private static ViewOrientation3D Orientation(XYZ direction) {
            var forward = direction.Normalize();
            var right = forward.CrossProduct(XYZ.BasisZ);
            if (right.IsZeroLength())
                right = XYZ.BasisX;
            var up = right.Normalize().CrossProduct(forward).Normalize();
            return new ViewOrientation3D(forward.Negate().Multiply(1000), up, forward);
        }

        private static BoundingBoxXYZ ModelBox(Document doc, View view, List<ElementId> ids) {
            IEnumerable<Element> elements = ids != null && ids.Count > 0
                ? ids.Select(doc.GetElement).Where(element => element != null)
                : new FilteredElementCollector(doc, view.Id)
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
                if (IsCoveredByOtherProcess(left, top, right, bottom))
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

        private static bool IsCoveredByOtherProcess(int left, int top, int right, int bottom) {
            var revitProcessId = (uint)System.Diagnostics.Process.GetCurrentProcess().Id;
            var centerX = (left + right) / 2;
            var centerY = (top + bottom) / 2;
            var probes = new[] {
                new NativePoint { X = centerX, Y = centerY },
                new NativePoint { X = left + CoverageProbeInset, Y = top + CoverageProbeInset },
                new NativePoint { X = right - CoverageProbeInset, Y = top + CoverageProbeInset },
                new NativePoint { X = left + CoverageProbeInset, Y = bottom - CoverageProbeInset },
                new NativePoint { X = right - CoverageProbeInset, Y = bottom - CoverageProbeInset },
            };
            return probes.Any(probe => {
                GetWindowThreadProcessId(WindowFromPoint(probe), out var owner);
                return owner != revitProcessId;
            });
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
