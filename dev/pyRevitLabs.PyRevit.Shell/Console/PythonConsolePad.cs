// Copyright (c) 2010 Joe Moorhouse

using ICSharpCode.AvalonEdit;
using System.Windows.Media;

namespace PythonConsoleControl
{
    public class PythonConsolePad
    {
        PythonTextEditor pythonTextEditor;
        TextEditor textEditor;
        PythonConsoleHost host;

        public PythonConsolePad()
        {
            textEditor = new TextEditor();
            pythonTextEditor = new PythonTextEditor(textEditor);
            host = new PythonConsoleHost(pythonTextEditor);
            host.Run();
            textEditor.FontFamily = new FontFamily("Consolas");
            textEditor.FontSize = 12;
        }

        public TextEditor Control
        {
            get { return textEditor; }
        }

        public PythonConsoleHost Host
        {
            get { return host; }
        }

        public PythonConsole Console
        {
            get { return host.Console; }
        }

        /// <summary>
        /// Selects the theme used for completion popups created from now on.
        /// </summary>
        public void SetCompletionTheme(bool useDarkTheme)
        {
            pythonTextEditor.UseDarkCompletionTheme = useDarkTheme;
        }

        /// <summary>
        /// Sets the foreground color for the console text.
        /// </summary>
        public void SetForeground(Brush foreground)
        {
            textEditor.Foreground = foreground;
            textEditor.TextArea.Foreground = foreground;
            // Force the TextView to use the new foreground
            textEditor.TextArea.TextView.LinkTextForegroundBrush = foreground;
        }

        /// <summary>
        /// Sets the background color for the console.
        /// </summary>
        public void SetBackground(Brush background)
        {
            textEditor.Background = background;
        }

        public void Dispose()
        {
            host.Dispose();
        }
    }
}
