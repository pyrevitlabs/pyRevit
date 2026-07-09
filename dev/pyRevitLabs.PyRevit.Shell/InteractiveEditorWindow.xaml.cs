using System.Diagnostics;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media;
using PythonConsoleControl;

namespace PyRevitLabs.PyRevit.Shell {
    /// <summary>
    /// Modeless/modal host window for the interactive Python editor + REPL. Mirrors
    /// <see cref="InteractiveShellWindow"/> but embeds <see cref="EditorView"/> instead of the
    /// bare console control.
    /// </summary>
    public partial class InteractiveEditorWindow : Window, IShellWindow {
        public InteractiveEditorWindow() {
            InitializeComponent();
        }

        public IronPythonConsoleControl ConsoleControl => editorView.ConsoleControl;

        /// <summary>
        /// Apply the editor + console theme and match the window background to it, so the editor
        /// blends with the active Revit UI theme instead of always rendering dark.
        /// </summary>
        public void ApplyTheme(bool useDarkTheme) {
            ShellTheme.Apply(this, useDarkTheme);
            editorView.ApplyTheme(useDarkTheme);
            Background = useDarkTheme
                ? new SolidColorBrush(Color.FromRgb(0x1F, 0x2D, 0x3D)) // Revit dark blue-gray
                : new SolidColorBrush(Colors.White);
        }

        /// <summary>
        /// Keep the editor floating above the Revit window without blocking it.
        /// Uses the process main window handle so it stays version-agnostic.
        /// </summary>
        public void SetRevitAsWindowOwner() {
            var revitHandle = Process.GetCurrentProcess().MainWindowHandle;
            if (revitHandle != System.IntPtr.Zero)
                new WindowInteropHelper(this).Owner = revitHandle;
        }
    }
}
