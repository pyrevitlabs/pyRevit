using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO;
using System.Linq;

using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Serves <c>capture</c>: a PNG of a view, so an agent can check what it built.
    /// </summary>
    /// <remarks>
    /// Two modes:
    /// <list type="bullet">
    /// <item><c>export</c> renders a view through <see cref="Document.ExportImage"/>. It works for any
    /// view, open or not, and doesn't depend on the Revit window.</item>
    /// <item><c>screen</c> copies the active view's window from the screen: exactly what the user
    /// sees, including selection and temporary hide/isolate, and blank if Revit is minimized or
    /// covered.</item>
    /// </list>
    /// The <c>3d</c> view is a temporary isometric view created inside a transaction group that is
    /// always rolled back.
    /// Invariant: capturing never leaves a change in the model.
    /// </remarks>
    internal static class AgentCapture {
        private const int DefaultWidth = 1280;
        private const int MinWidth = 320;
        private const int MaxWidth = 2400;

        public sealed class Request {
            public string View;
            public string Mode;
            public int Width;
        }

        public static Request Parse(JObject parameters) {
            var mode = (parameters.Value<string>("mode") ?? "export").ToLowerInvariant();
            if (mode != "export" && mode != "screen")
                throw new AgentException("invalid_params", "'mode' must be export or screen.");

            var width = parameters.Value<int?>("width") ?? DefaultWidth;
            return new Request {
                View = string.IsNullOrWhiteSpace(parameters.Value<string>("view")) ? "active" : parameters.Value<string>("view").Trim(),
                Mode = mode,
                Width = Math.Max(MinWidth, Math.Min(MaxWidth, width)),
            };
        }

        public static JToken Capture(UIApplication app, Request request) {
            var uidoc = app.ActiveUIDocument
                ?? throw new AgentException("no_active_document", "Revit has no active document.");
            var doc = uidoc.Document;
            if (doc.IsModifiable)
                throw new AgentException("revit_busy", "Another transaction is open in the active document.");

            var directory = Path.Combine(AgentPaths.RootDir, "captures");
            Directory.CreateDirectory(directory);
            var baseName = DateTime.Now.ToString("yyyyMMdd-HHmmss") + "-" + Guid.NewGuid().ToString("N").Substring(0, 6);

            string path;
            View captured;
            if (request.Mode == "screen") {
                captured = ResolveView(doc, uidoc, request.View);
                path = CaptureScreen(uidoc, captured, Path.Combine(directory, baseName + ".png"));
            }
            else if (string.Equals(request.View, "3d", StringComparison.OrdinalIgnoreCase)) {
                captured = null;
                path = ExportTemporary3D(doc, directory, baseName, request.Width);
            }
            else {
                captured = ResolveView(doc, uidoc, request.View);
                path = ExportView(doc, captured, directory, baseName, request.Width);
            }

            ScaleDown(path, request.Width, out var width, out var height);
            return new JObject {
                ["mode"] = request.Mode,
                ["view"] = captured == null
                    ? new JObject { ["name"] = "temporary isometric 3D view", ["type"] = "ThreeD" }
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

        private static string ExportTemporary3D(Document doc, string directory, string baseName, int width) {
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
                        transaction.Commit();
                    }
                    return ExportView(doc, view, directory, baseName, width);
                }
                finally {
                    if (group.HasStarted() && !group.HasEnded())
                        group.RollBack();
                }
            }
        }

        private static string CaptureScreen(UIDocument uidoc, View view, string path) {
            var uiView = uidoc.GetOpenUIViews().FirstOrDefault(open => open.ViewId == view.Id)
                ?? throw new AgentException("view_not_open", $"View '{view.Name}' is not open in Revit; use mode 'export' or open the view.");

            uidoc.RefreshActiveView();
            var rectangle = uiView.GetWindowRectangle();
            var width = rectangle.Right - rectangle.Left;
            var height = rectangle.Bottom - rectangle.Top;
            if (width <= 0 || height <= 0)
                throw new AgentException("capture_failed", "The view window has no visible area; is Revit minimized?");

            using (var bitmap = new Bitmap(width, height, PixelFormat.Format24bppRgb))
            using (var graphics = Graphics.FromImage(bitmap)) {
                graphics.CopyFromScreen(rectangle.Left, rectangle.Top, 0, 0, new Size(width, height));
                bitmap.Save(path, ImageFormat.Png);
            }
            return path;
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
