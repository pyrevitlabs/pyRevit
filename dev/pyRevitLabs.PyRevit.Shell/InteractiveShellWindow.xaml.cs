using System;
using System.Diagnostics;
using System.Windows;
using System.Windows.Interop;
using PythonConsoleControl;

namespace PyRevitLabs.PyRevit.Shell {
    /// <summary>
    /// Modeless host window for the interactive IronPython REPL.
    /// </summary>
    public partial class InteractiveShellWindow : Window {
        public InteractiveShellWindow() {
            InitializeComponent();
            // Match pyRevit's dark console styling (ported RPS dark syntax theme)
            consoleControl.ApplyTheme(useDarkTheme: true);
        }

        public IronPythonConsoleControl ConsoleControl {
            get { return consoleControl; }
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
