using System;
using System.Diagnostics;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media;
using PythonConsoleControl;

namespace PyRevitLabs.PyRevit.Shell {
    /// <summary>
    /// Modeless host window for the interactive IronPython REPL.
    /// </summary>
    public partial class InteractiveShellWindow : Window, IShellWindow {
        public InteractiveShellWindow() {
            InitializeComponent();
            // The console control defaults to the light theme in its own constructor; the
            // launcher re-applies the matching Revit theme via ApplyTheme once it has resolved
            // the active UITheme (see ShellLauncher).
        }

        public IronPythonConsoleControl ConsoleControl {
            get { return consoleControl; }
        }

        /// <summary>
        /// Apply the console theme and match the window chrome background to it, so the shell
        /// blends with the active Revit UI theme instead of always rendering dark.
        /// </summary>
        public void ApplyTheme(bool useDarkTheme) {
            ShellTheme.Apply(this, useDarkTheme);
            consoleControl.ApplyTheme(useDarkTheme);
            Background = useDarkTheme
                ? new SolidColorBrush(Color.FromRgb(0x1F, 0x2D, 0x3D)) // Revit dark blue-gray
                : new SolidColorBrush(Colors.White);
        }

        /// <summary>
        /// Keep the shell floating above the Revit window without blocking it.
        /// Uses the process main window handle so it stays version-agnostic.
        /// </summary>
        public void SetRevitAsWindowOwner() {
            var revitHandle = Process.GetCurrentProcess().MainWindowHandle;
            if (revitHandle != IntPtr.Zero)
                new WindowInteropHelper(this).Owner = revitHandle;
        }
    }
}
