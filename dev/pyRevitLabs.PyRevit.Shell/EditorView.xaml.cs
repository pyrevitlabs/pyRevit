using System;
using System.IO;
using System.Xml;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using ICSharpCode.AvalonEdit;
using ICSharpCode.AvalonEdit.Highlighting;
using ICSharpCode.AvalonEdit.Highlighting.Xshd;
using Microsoft.Win32;
using PythonConsoleControl;

namespace PyRevitLabs.PyRevit.Shell {
    /// <summary>
    /// Code editor (AvalonEdit) paired with the interactive IronPython console. The editor's
    /// "Run" sends the current selection, or the whole document, to the console, which already
    /// executes every statement in a valid Revit API context (set up by the shell launcher).
    /// </summary>
    public partial class EditorView : UserControl {
        // The highlighting themes ship as embedded resources from the ported console control;
        // the editor registers its own copies so it never clashes with the console's registrations.
        const string LightHighlightingResource = "PythonConsoleControl.Resources.Python.xshd";
        const string DarkHighlightingResource = "PythonConsoleControl.Resources.Python-Dark.xshd";
        const string LightHighlightingName = "Python Editor Highlighting";
        const string DarkHighlightingName = "Python Editor Dark Highlighting";

        string _currentFileName;
        bool _isFirstFocus = true;

        public EditorView() {
            InitializeComponent();
            textEditor.Text = "# Write Python here and press F5 (or click Run) to execute in the console below.";
        }

        /// <summary>Console control, exposed so the launcher can wire the engine and dispatch.</summary>
        public IronPythonConsoleControl ConsoleControl => consoleControl;

        /// <summary>AvalonEdit text editor, exposed for advanced hosting scenarios.</summary>
        public TextEditor TextEditor => textEditor;

        /// <summary>Current file path, or null when the buffer has never been saved.</summary>
        public string CurrentFileName => _currentFileName;

        public void NewFileClick(object sender, RoutedEventArgs e) {
            _currentFileName = null;
            textEditor.Text = string.Empty;
        }

        public void OpenFileClick(object sender, RoutedEventArgs e) {
            var dlg = new OpenFileDialog {
                CheckFileExists = true,
                Filter = "Python Files|*.py|All Files|*.*",
                DefaultExt = ".py"
            };
            if (dlg.ShowDialog() ?? false) {
                _currentFileName = dlg.FileName;
                textEditor.Load(_currentFileName);
            }
        }

        public void SaveFileClick(object sender, RoutedEventArgs e) => SaveFile();

        public void SaveAsFileClick(object sender, RoutedEventArgs e) {
            _currentFileName = null;
            SaveFile();
        }

        void SaveFile() {
            if (_currentFileName == null) {
                var dlg = new SaveFileDialog {
                    Filter = "Python Files|*.py",
                    DefaultExt = "py",
                    AddExtension = true
                };
                if (dlg.ShowDialog() ?? false)
                    _currentFileName = dlg.FileName;
                else
                    return;
            }
            textEditor.Save(_currentFileName);
        }

        public void RunClick(object sender, RoutedEventArgs e) => RunEditorStatements();

        void RunEditorStatements() {
            string statements = textEditor.TextArea.Selection.Length > 0
                ? textEditor.TextArea.Selection.GetText()
                : textEditor.Document.Text;
            RunStatements(statements);
        }

        /// <summary>Run arbitrary statements in the interactive console.</summary>
        public void RunStatements(string statements) {
            consoleControl.Pad.Console.RunStatements(statements);
        }

        void TextEditor_PreviewKeyDown(object sender, KeyEventArgs e) {
            if (e.Key == Key.F5) {
                RunEditorStatements();
                e.Handled = true;
            }
            else if (e.Key == Key.S && Keyboard.Modifiers == ModifierKeys.Control) {
                if (Keyboard.Modifiers == (ModifierKeys.Control | ModifierKeys.Shift))
                    SaveAsFileClick(sender, e);
                else
                    SaveFile();
                e.Handled = true;
            }
            else if (e.Key == Key.O && Keyboard.Modifiers == ModifierKeys.Control) {
                OpenFileClick(sender, e);
                e.Handled = true;
            }
            else if (e.Key == Key.N && Keyboard.Modifiers == ModifierKeys.Control) {
                NewFileClick(sender, e);
                e.Handled = true;
            }
        }

        // Drop the startup hint the first time the editor gains focus, so the user starts from a
        // clean buffer without having to manually delete it.
        void TextEditor_GotFocus(object sender, RoutedEventArgs e) {
            if (_isFirstFocus && string.IsNullOrEmpty(_currentFileName)) {
                textEditor.Text = string.Empty;
                _isFirstFocus = false;
            }
        }

        /// <summary>
        /// Theme the editor surface and the console together so they match the active Revit UI
        /// theme. Reuses the syntax-highlighting definitions already embedded in this assembly.
        /// </summary>
        public void ApplyTheme(bool useDarkTheme) {
            ShellTheme.Apply(this, useDarkTheme);
            ThemeEditor(useDarkTheme);
            consoleControl.ApplyTheme(useDarkTheme);
        }

        // The stock ToolBar template reserves space for an overflow dropdown that renders as a
        // system-colored spot on the themed bar; the shell never overflows, so remove it.
        void ToolBar_Loaded(object sender, RoutedEventArgs e) {
            var toolBar = (ToolBar)sender;
            if (toolBar.Template.FindName("OverflowGrid", toolBar) is FrameworkElement overflowGrid)
                overflowGrid.Visibility = Visibility.Collapsed;
            if (toolBar.Template.FindName("MainPanelBorder", toolBar) is FrameworkElement mainPanelBorder)
                mainPanelBorder.Margin = new Thickness(0);
        }

        void ThemeEditor(bool useDarkTheme) {
            textEditor.Background = useDarkTheme
                ? new SolidColorBrush(Color.FromRgb(0x1F, 0x2D, 0x3D)) // Revit dark blue-gray
                : new SolidColorBrush(Colors.White);
            textEditor.Foreground = useDarkTheme
                ? new SolidColorBrush(Color.FromRgb(0xD4, 0xD4, 0xD4))
                : new SolidColorBrush(Colors.Black);
            textEditor.LineNumbersForeground = useDarkTheme
                ? new SolidColorBrush(Color.FromRgb(0x85, 0x85, 0x85))
                : new SolidColorBrush(Color.FromRgb(0x99, 0x99, 0x99));

            var highlighting = GetEditorHighlighting(useDarkTheme);
            if (highlighting != null)
                textEditor.SyntaxHighlighting = highlighting;
        }

        static IHighlightingDefinition GetEditorHighlighting(bool useDarkTheme) {
            string name = useDarkTheme ? DarkHighlightingName : LightHighlightingName;
            var existing = HighlightingManager.Instance.GetDefinition(name);
            if (existing != null)
                return existing;

            string resource = useDarkTheme ? DarkHighlightingResource : LightHighlightingResource;
            using (var stream = typeof(EditorView).Assembly.GetManifestResourceStream(resource)) {
                if (stream == null)
                    return null;
                using (var reader = new XmlTextReader(stream)) {
                    var definition = HighlightingLoader.Load(reader, HighlightingManager.Instance);
                    // Register without file extensions to avoid colliding with the console's
                    // own ".py" registration; the editor sets SyntaxHighlighting directly.
                    HighlightingManager.Instance.RegisterHighlighting(name, new string[0], definition);
                    return definition;
                }
            }
        }
    }
}
