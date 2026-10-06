using System;
using System.Diagnostics;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media;
using PythonConsoleControl;

namespace PyRevitLabs.PyRevit.Shell {
    /// <summary>
    /// Host window for the interactive console.
    /// </summary>
    public partial class InteractiveShellWindow : Window, IShellWindow {
        public InteractiveShellWindow() {
            InitializeComponent();
        }

        public IronPythonConsoleControl ConsoleControl {
            get { return consoleControl; }
        }

        /// <summary>
        /// Applies the active Revit theme to the console and window.
        /// </summary>
        public void ApplyTheme(bool useDarkTheme) {
            ShellTheme.Apply(this, useDarkTheme);
            consoleControl.ApplyTheme(useDarkTheme);
            Background = useDarkTheme
                ? new SolidColorBrush(Color.FromRgb(0x1F, 0x2D, 0x3D))
                : new SolidColorBrush(Colors.White);
        }

        /// <summary>
        /// Keep the shell floating above the Revit window without blocking it.
        /// </summary>
        public void SetRevitAsWindowOwner() {
            var revitHandle = Process.GetCurrentProcess().MainWindowHandle;
            if (revitHandle != IntPtr.Zero)
                new WindowInteropHelper(this).Owner = revitHandle;
        }
    }
}
