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
    /// Hosts and themes the interactive console.
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

            _pad.Control.TextArea.TextView.Redraw();
        }

        private Brush GetForegroundBrush(bool useDarkTheme)
        {
            Brush foregroundBrush = TryFindResource("ThemeConsoleForeground") as Brush;
            if (foregroundBrush == null)
            {
                foregroundBrush = useDarkTheme
                    ? new SolidColorBrush(Color.FromRgb(0xD4, 0xD4, 0xD4))
                    : new SolidColorBrush(Colors.Black);
            }
            return foregroundBrush;
        }

        private void ApplyThemeResources(bool useDarkTheme)
        {
            TextEditor editor = _pad.Control;

            Brush backgroundBrush = TryFindResource("ThemeConsoleBackground") as Brush;

            // Standalone hosts do not provide Revit theme resources.
            if (backgroundBrush == null)
            {
                backgroundBrush = useDarkTheme
                    ? new SolidColorBrush(Color.FromRgb(0x1F, 0x2D, 0x3D))
                    : new SolidColorBrush(Colors.White);
            }

            _pad.SetBackground(backgroundBrush);
            _pad.SetForeground(_currentForeground);

            // Completion popups are created on demand, so record the theme for the next one.
            _pad.SetCompletionTheme(useDarkTheme);

            if (editor.ShowLineNumbers)
            {
                var lineNumbersForeground = useDarkTheme
                    ? new SolidColorBrush(Color.FromRgb(0x85, 0x85, 0x85))
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

            for (int i = lineTransformers.Count - 1; i >= 0; i--)
            {
                if (lineTransformers[i] is HighlightingColorizer)
                {
                    lineTransformers.RemoveAt(i);
                }
            }

            var newColorizer = new PythonConsoleHighlightingColorizer(highlightingDefinition, editor.Document)
            {
                OutputForeground = _currentForeground
            };
            lineTransformers.Add(newColorizer);

            editor.TextArea.TextView.Redraw();
        }

        public PythonConsolePad Pad
        {
            get { return _pad; }
        }
    }
}
