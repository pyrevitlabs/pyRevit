using System;
using System.Collections.Generic;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Xml;
using ICSharpCode.AvalonEdit;
using ICSharpCode.AvalonEdit.Highlighting;
using ICSharpCode.AvalonEdit.Rendering;

namespace PythonConsoleControl
{
    /// <summary>
    /// Interaction logic for PythonConsoleControl.xaml
    /// </summary>
    public partial class IronPythonConsoleControl : UserControl
    {
        private const string LightHighlightingName = "Python Console Highlighting";
        private const string DarkHighlightingName = "Python Console Dark Highlighting";
        private const string LightHighlightingResource = "PythonConsoleControl.Resources.Python.xshd";
        private const string DarkHighlightingResource = "PythonConsoleControl.Resources.Python-Dark.xshd";

        private readonly PythonConsolePad _pad;
        private Brush _currentForeground;

        /// <summary>
        /// Perform the action on an already instantiated PythonConsoleHost.
        /// </summary>
        public void WithConsoleHost(Action<PythonConsoleHost> action)
        {
            _pad.Host.WhenConsoleCreated(action);
        }

        public IronPythonConsoleControl()
        {
            InitializeComponent();
            _pad = new PythonConsolePad();
            Grid.Children.Add(_pad.Control);
            ApplyTheme(false);
        }

        public void ApplyTheme(bool useDarkTheme)
        {
            _currentForeground = GetForegroundBrush(useDarkTheme);
            ApplyThemeResources(useDarkTheme);
            var highlightingDefinition = GetHighlightingDefinition(
                useDarkTheme ? DarkHighlightingResource : LightHighlightingResource,
                useDarkTheme ? DarkHighlightingName : LightHighlightingName);
            ApplyHighlighting(highlightingDefinition);

            // Force redraw of the text view
            _pad.Control.TextArea.TextView.Redraw();
        }

        private Brush GetForegroundBrush(bool useDarkTheme)
        {
            Brush foregroundBrush = TryFindResource("ThemeConsoleForeground") as Brush;
            if (foregroundBrush == null)
            {
                foregroundBrush = useDarkTheme
                    ? new SolidColorBrush(Color.FromRgb(0xD4, 0xD4, 0xD4))  // #D4D4D4
                    : new SolidColorBrush(Colors.Black);
            }
            return foregroundBrush;
        }

        private void ApplyThemeResources(bool useDarkTheme)
        {
            TextEditor editor = _pad.Control;

            // Try to find resources from the visual tree (parent window)
            Brush backgroundBrush = TryFindResource("ThemeConsoleBackground") as Brush;

            // If not found in resources, use hardcoded values based on theme
            // Revit dark theme uses blue-gray colors
            if (backgroundBrush == null)
            {
                backgroundBrush = useDarkTheme
                    ? new SolidColorBrush(Color.FromRgb(0x1F, 0x2D, 0x3D))  // #1F2D3D - Revit dark blue-gray
                    : new SolidColorBrush(Colors.White);
            }

            // Apply background and foreground
            _pad.SetBackground(backgroundBrush);
            _pad.SetForeground(_currentForeground);

            // Completion popups are created on demand, so record the theme for the next one.
            _pad.SetCompletionTheme(useDarkTheme);

            // Also set the line number margin colors if showing line numbers
            if (editor.ShowLineNumbers)
            {
                var lineNumbersForeground = useDarkTheme
                    ? new SolidColorBrush(Color.FromRgb(0x85, 0x85, 0x85))  // #858585
                    : new SolidColorBrush(Color.FromRgb(0x99, 0x99, 0x99));
                editor.LineNumbersForeground = lineNumbersForeground;
            }
        }

        private static IHighlightingDefinition GetHighlightingDefinition(string resourceName, string highlightingName)
        {
            IHighlightingDefinition existingHighlighting = HighlightingManager.Instance.GetDefinition(highlightingName);
            if (existingHighlighting != null)
            {
                return existingHighlighting;
            }

            using (Stream resourceStream = typeof(IronPythonConsoleControl).Assembly.GetManifestResourceStream(resourceName))
            {
                if (resourceStream == null)
                {
                    throw new InvalidOperationException($"Could not find embedded resource: {resourceName}");
                }

                using (XmlReader xmlReader = new XmlTextReader(resourceStream))
                {
                    var highlightingDefinition = ICSharpCode.AvalonEdit.Highlighting.Xshd.
                        HighlightingLoader.Load(xmlReader, HighlightingManager.Instance);
                    HighlightingManager.Instance.RegisterHighlighting(highlightingName, new string[] { ".py" }, highlightingDefinition);
                    return highlightingDefinition;
                }
            }
        }

        private void ApplyHighlighting(IHighlightingDefinition highlightingDefinition)
        {
            TextEditor editor = _pad.Control;
            editor.SyntaxHighlighting = highlightingDefinition;

            IList<IVisualLineTransformer> lineTransformers = editor.TextArea.TextView.LineTransformers;

            // First, remove any existing HighlightingColorizer (including our custom one)
            for (int i = lineTransformers.Count - 1; i >= 0; i--)
            {
                if (lineTransformers[i] is HighlightingColorizer)
                {
                    lineTransformers.RemoveAt(i);
                }
            }

            // Add our custom colorizer with the output foreground
            var newColorizer = new PythonConsoleHighlightingColorizer(highlightingDefinition, editor.Document)
            {
                OutputForeground = _currentForeground
            };
            lineTransformers.Add(newColorizer);

            // Force redraw to apply new colors
            editor.TextArea.TextView.Redraw();
        }

        public PythonConsolePad Pad
        {
            get { return _pad; }
        }
    }
}
