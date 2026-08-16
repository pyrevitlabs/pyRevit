using System.Diagnostics;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media;
using PythonConsoleControl;

namespace PyRevitLabs.PyRevit.Shell {
    /// <summary>
    /// Host window for the interactive editor and console.
    /// </summary>
    public partial class InteractiveEditorWindow : Window, IShellWindow {
        public InteractiveEditorWindow() {
            InitializeComponent();
        }

        public IronPythonConsoleControl ConsoleControl => editorView.ConsoleControl;

        /// <summary>
        /// Blends the editor and console with the active Revit UI theme.
        /// </summary>
        public void ApplyTheme(bool useDarkTheme) {
            ShellTheme.Apply(this, useDarkTheme);
            editorView.ApplyTheme(useDarkTheme);
            Background = useDarkTheme
                ? new SolidColorBrush(Color.FromRgb(0x1F, 0x2D, 0x3D))
                : new SolidColorBrush(Colors.White);
        }

        /// <summary>
        /// Keep the editor floating above the Revit window without blocking it.
        /// </summary>
        public void SetRevitAsWindowOwner() {
            var revitHandle = Process.GetCurrentProcess().MainWindowHandle;
            if (revitHandle != System.IntPtr.Zero)
                new WindowInteropHelper(this).Owner = revitHandle;
        }
    }
}
