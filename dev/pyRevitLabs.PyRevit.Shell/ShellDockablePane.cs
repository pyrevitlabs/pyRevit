using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using Autodesk.Revit.UI;
using Autodesk.Revit.UI.Events;

namespace PyRevitLabs.PyRevit.Shell {
    internal static class ShellDockablePaneRegistration {
        internal const string PaneGuid = "8e2a1f4b-3c57-4d9a-b6e8-7f1a2c3d4e5b";
        const string PaneTitle = "pyRevit Python Shell";

        static ShellDockablePaneProvider _provider;

        internal static bool Register(
            UIApplication uiapp,
            IList<string> searchPaths,
            bool useEditor
        ) {
            if (uiapp == null)
                throw new ArgumentNullException(nameof(uiapp));

            var paneId = new DockablePaneId(new Guid(PaneGuid));
            if (DockablePane.PaneIsRegistered(paneId))
                return false;

            // Revit persists pane visibility, but the shell must remain opt-in at startup.
            EventHandler<IdlingEventArgs> hideOnFirstIdling = null;
            hideOnFirstIdling = (sender, args) => {
                uiapp.Idling -= hideOnFirstIdling;
                try {
                    uiapp.GetDockablePane(paneId).Hide();
                }
                catch {
                    // The pane can be unavailable while Revit restores its workspace.
                }
            };
            uiapp.Idling += hideOnFirstIdling;

            try {
                _provider = new ShellDockablePaneProvider(
                    uiapp,
                    paneId,
                    searchPaths,
                    useEditor
                );
                uiapp.RegisterDockablePane(paneId, PaneTitle, _provider);
                return true;
            }
            catch {
                uiapp.Idling -= hideOnFirstIdling;
                _provider = null;
                throw;
            }
        }
    }

    internal sealed class ShellDockablePaneProvider : IDockablePaneProvider {
        readonly ShellDockablePane _pane;

        internal ShellDockablePaneProvider(
            UIApplication uiapp,
            DockablePaneId paneId,
            IList<string> searchPaths,
            bool useEditor
        ) {
            _pane = new ShellDockablePane(uiapp, paneId, searchPaths, useEditor);
        }

        public void SetupDockablePane(DockablePaneProviderData data) {
            data.FrameworkElement = _pane;
            data.VisibleByDefault = false;
        }
    }

    internal sealed class ShellDockablePane : Page {
        readonly UIApplication _uiapp;
        readonly DockablePaneId _paneId;
        readonly IList<string> _searchPaths;
        readonly bool _useEditor;
        readonly Grid _contentHost;

        internal ShellDockablePane(
            UIApplication uiapp,
            DockablePaneId paneId,
            IList<string> searchPaths,
            bool useEditor
        ) {
            _uiapp = uiapp;
            _paneId = paneId;
            _searchPaths = searchPaths == null
                ? new List<string>()
                : new List<string>(searchPaths);
            _useEditor = useEditor;
            _contentHost = new Grid();
            Content = _contentHost;
            Background = RevitThemeDetector.IsDarkTheme(uiapp)
                ? new SolidColorBrush(Color.FromRgb(0x1F, 0x2D, 0x3D))
                : Brushes.White;

            // Console creation needs a valid Revit API context and is deferred until shown.
            _uiapp.Idling += BuildOnIdling;
        }

        void BuildOnIdling(object sender, IdlingEventArgs args) {
            try {
                if (!_uiapp.GetDockablePane(_paneId).IsShown())
                    return;
            }
            catch {
                return;
            }

            _uiapp.Idling -= BuildOnIdling;
            try {
                var shell = _useEditor
                    ? ShellLauncher.CreateConfiguredEditor(_uiapp, _searchPaths)
                    : ShellLauncher.CreateConfiguredConsole(_uiapp, _searchPaths);
                _contentHost.Children.Add(shell);
            }
            catch (Exception error) {
                _contentHost.Children.Add(new TextBlock {
                    Text = error.ToString(),
                    TextWrapping = TextWrapping.Wrap,
                    Margin = new Thickness(8)
                });
            }
        }
    }
}
