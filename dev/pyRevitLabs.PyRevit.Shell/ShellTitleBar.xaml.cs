using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;

namespace PyRevitLabs.PyRevit.Shell {
    /// <summary>
    /// Title bar for borderless shell windows.
    /// </summary>
    public partial class ShellTitleBar : UserControl {
        Window _window;

        public ShellTitleBar() {
            InitializeComponent();
            Loaded += OnLoaded;
            Unloaded += OnUnloaded;
        }

        void OnLoaded(object sender, RoutedEventArgs e) {
            DetachWindow();
            _window = Window.GetWindow(this);
            if (_window != null) {
                _window.StateChanged += OnWindowStateChanged;
                UpdateMaximizeButton();
            }
        }

        void OnUnloaded(object sender, RoutedEventArgs e) => DetachWindow();

        void DetachWindow() {
            if (_window != null) {
                _window.StateChanged -= OnWindowStateChanged;
                _window = null;
            }
        }

        void OnWindowStateChanged(object sender, EventArgs e) => UpdateMaximizeButton();

        void UpdateMaximizeButton() {
            bool maximized = _window.WindowState == WindowState.Maximized;
            maximizeButton.Content = maximized ? "" : "";
            maximizeButton.ToolTip = maximized ? "Restore" : "Maximize";
        }

        void TitleBar_MouseLeftButtonDown(object sender, MouseButtonEventArgs e) {
            if (_window == null)
                return;
            if (e.ClickCount == 2) {
                ToggleMaximize();
                return;
            }
            _window.DragMove();
        }

        void ToggleMaximize() {
            _window.WindowState = _window.WindowState == WindowState.Maximized
                ? WindowState.Normal
                : WindowState.Maximized;
        }

        void MinimizeClick(object sender, RoutedEventArgs e) {
            if (_window != null)
                _window.WindowState = WindowState.Minimized;
        }

        void MaximizeClick(object sender, RoutedEventArgs e) {
            if (_window != null)
                ToggleMaximize();
        }

        void CloseClick(object sender, RoutedEventArgs e) {
            if (_window != null)
                _window.Close();
        }
    }
}
