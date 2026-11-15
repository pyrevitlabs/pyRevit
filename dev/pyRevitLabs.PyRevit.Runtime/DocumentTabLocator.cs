using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Windows.Controls;
using System.Windows.Interop;
using System.Windows.Media;

using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using UIFramework;
using Xceed.Wpf.AvalonDock.Controls;
using Xceed.Wpf.AvalonDock.Layout;

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>Matches document tabs by native MFC document identity, never by display title.</summary>
    internal static class DocumentTabLocator {
        internal static Visual GetWindowRoot(UIApplication application) {
            var handle = IntPtr.Zero;
            try { handle = application.MainWindowHandle; }
            catch { }
            return handle == IntPtr.Zero ? null : HwndSource.FromHwnd(handle)?.RootVisual;
        }

        internal static long GetAPIDocumentId(Document document) {
            var method = document.GetType().GetMethod("getMFCDoc", BindingFlags.Instance | BindingFlags.NonPublic);
            var nativeDocument = method.Invoke(document, Array.Empty<object>());
            var pointerMethod = nativeDocument.GetType().GetMethod("GetPointerValue", BindingFlags.Instance | BindingFlags.NonPublic);
            return ((IntPtr)pointerMethod.Invoke(nativeDocument, Array.Empty<object>())).ToInt64();
        }

        internal static long GetTabDocumentId(TabItem tab) {
            return ((MFCMDIFrameHost)((MFCMDIChildFrameControl)((LayoutDocument)tab.Content).Content).Content).document.ToInt64();
        }

        internal static IEnumerable<TabItem> GetDocumentTabs(LayoutDocumentPaneGroupControl group) {
            return group == null ? Enumerable.Empty<TabItem>() : group.FindVisualChildren<TabItem>();
        }

        internal static IEnumerable<TabItem> FindTabs(UIApplication application, Document document) {
            var root = GetWindowRoot(application) as MainWindow;
            if (root == null)
                return Enumerable.Empty<TabItem>();
            var key = GetAPIDocumentId(document);
            var group = MainWindow.FindFirstChild<LayoutDocumentPaneGroupControl>(root);
            return GetDocumentTabs(group).Where(tab => GetTabDocumentId(tab) == key).ToArray();
        }
    }
}
