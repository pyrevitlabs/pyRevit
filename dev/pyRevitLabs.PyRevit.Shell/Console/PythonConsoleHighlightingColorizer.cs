// Copyright (c) 2010 Joe Moorhouse

using System;
using System.Windows.Media;
using ICSharpCode.AvalonEdit.Document;
using ICSharpCode.AvalonEdit.Highlighting;
using ICSharpCode.AvalonEdit.Rendering;

namespace PythonConsoleControl
{
    /// <summary>
    /// Custom colorizer for the Python console that handles both input lines (with syntax highlighting)
    /// and output lines (with a configurable foreground color).
    /// </summary>
    public class PythonConsoleHighlightingColorizer : HighlightingColorizer
    {
        private readonly TextDocument _document;
        private Brush _outputForeground;

        /// <summary>
        /// Gets or sets the foreground brush for output lines (lines not starting with >>> or ...).
        /// </summary>
        public Brush OutputForeground
        {
            get => _outputForeground;
            set => _outputForeground = value;
        }

        /// <summary>
        /// Creates a new PythonConsoleHighlightingColorizer instance.
        /// </summary>
        /// <param name="highlightingDefinition">The highlighting definition to use for input lines.</param>
        /// <param name="document">The text document.</param>
        public PythonConsoleHighlightingColorizer(IHighlightingDefinition highlightingDefinition, TextDocument document)
            : base(highlightingDefinition)
        {
            _document = document ?? throw new ArgumentNullException(nameof(document));
        }

        /// <inheritdoc/>
        protected override void ColorizeLine(DocumentLine line)
        {
            if (line.Length == 0)
                return;

            string lineString = _document.GetText(line);

            // Check if this is an input line (starts with >>> or ...)
            bool isInputLine = lineString.Length >= 3 &&
                (lineString.StartsWith(">>>") || lineString.StartsWith("..."));

            if (isInputLine)
            {
                // Apply syntax highlighting to input lines
                IHighlighter highlighter = CurrentContext.TextView.Services.GetService(typeof(IHighlighter)) as IHighlighter;
                if (highlighter != null)
                {
                    HighlightedLine hl = highlighter.HighlightLine(line.LineNumber);
                    foreach (HighlightedSection section in hl.Sections)
                    {
                        ChangeLinePart(section.Offset, section.Offset + section.Length,
                            visualLineElement => ApplyColorToElement(visualLineElement, section.Color));
                    }
                }
            }
            else
            {
                // Apply foreground color to output lines (errors, results, banner text, etc.)
                if (_outputForeground != null)
                {
                    ChangeLinePart(line.Offset, line.EndOffset,
                        visualLineElement => visualLineElement.TextRunProperties.SetForegroundBrush(_outputForeground));
                }
            }
        }
    }
}
