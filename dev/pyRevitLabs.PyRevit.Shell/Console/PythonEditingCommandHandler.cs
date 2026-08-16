// Copyright (c) 2010 Joe Moorhouse

using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Input;
using System.Reflection;

using ICSharpCode.AvalonEdit;
using ICSharpCode.AvalonEdit.Document;
using ICSharpCode.AvalonEdit.Highlighting;
using ICSharpCode.AvalonEdit.Editing;

namespace PythonConsoleControl
{
    /// <summary>
    /// Handles commands that do not require the Python engine.
    /// </summary>
    class PythonEditingCommandHandler
    {
        PythonTextEditor textEditor;
        TextArea textArea;

        public PythonEditingCommandHandler(PythonTextEditor textEditor)
        {
            this.textEditor = textEditor;
            this.textArea = textEditor.textArea;
        }

        internal static void CanCutOrCopy(object target, CanExecuteRoutedEventArgs args)
        {
            TextArea textArea = GetTextArea(target);
            if (textArea != null && textArea.Document != null)
            {
                args.CanExecute = textArea.Options.CutCopyWholeLine || !textArea.Selection.IsEmpty;
                args.Handled = true;
            }
        }

        internal static TextArea GetTextArea(object target)
        {
            return target as TextArea;
        }

        internal static void OnCopy(object target, ExecutedRoutedEventArgs args)
        {
            TextArea textArea = GetTextArea(target);
            if (textArea != null && textArea.Document != null)
            {
                if (textArea.Selection.IsEmpty && textArea.Options.CutCopyWholeLine)
                {
                    DocumentLine currentLine = textArea.Document.GetLineByNumber(textArea.Caret.Line);
                    CopyWholeLine(textArea, currentLine);
                }
                else
                {
                    CopySelectedText(textArea);
                }
                args.Handled = true;
            }
        }

        internal static void OnCut(object target, ExecutedRoutedEventArgs args)
        {
            TextArea textArea = GetTextArea(target);
            if (textArea != null && textArea.Document != null)
            {
                if (textArea.Selection.IsEmpty && textArea.Options.CutCopyWholeLine)
                {
                    DocumentLine currentLine = textArea.Document.GetLineByNumber(textArea.Caret.Line);
                    CopyWholeLine(textArea, currentLine);
                    textArea.Document.Remove(currentLine.Offset, currentLine.TotalLength);
                }
                else
                {
                    CopySelectedText(textArea);
                    textArea.Selection.ReplaceSelectionWithText(string.Empty);
                }
                textArea.Caret.BringCaretToView();
                args.Handled = true;
            }
        }

        internal static void CopySelectedText(TextArea textArea)
        {
            var data = textArea.Selection.CreateDataObject(textArea);

            try
            {
                Clipboard.SetDataObject(data, true);
            }
            catch (ExternalException)
            {
                // Clipboard ownership can change between the availability check and the write.
                return;
            }

            string text = textArea.Selection.GetText();
            text = TextUtilities.NormalizeNewLines(text, Environment.NewLine);
        }

        internal static void CopyWholeLine(TextArea textArea, DocumentLine line)
        {
            ISegment wholeLine = new VerySimpleSegment(line.Offset, line.TotalLength);
            string text = textArea.Document.GetText(wholeLine);
            text = TextUtilities.NormalizeNewLines(text, Environment.NewLine);
            DataObject data = new DataObject(text);

            IHighlighter highlighter = textArea.GetService(typeof(IHighlighter)) as IHighlighter;
            HtmlClipboard.SetHtml(data, HtmlClipboard.CreateHtmlFragment(textArea.Document, highlighter, wholeLine, new HtmlOptions(textArea.Options)));

            MemoryStream lineSelected = new MemoryStream(1);
            lineSelected.WriteByte(1);
            data.SetData(LineSelectedType, lineSelected, false);

            try
            {
                Clipboard.SetDataObject(data, true);
            }
            catch (ExternalException)
            {
                // Clipboard ownership can change between the availability check and the write.
                return;
            }
        }

        internal static ExecutedRoutedEventHandler OnDelete(RoutedUICommand selectingCommand)
        {
            return (target, args) =>
            {
                TextArea textArea = GetTextArea(target);
                if (textArea != null && textArea.Document != null)
                {
                    // Keep selection and deletion in one undo transaction.
                    using (textArea.Document.RunUpdate())
                    {
                        Type textAreaType = textArea.GetType();
                        MethodInfo method;
                        if (textArea.Selection.IsEmpty)
                        {
                            TextViewPosition oldCaretPosition = textArea.Caret.Position;
                            selectingCommand.Execute(args.Parameter, textArea);
                            bool hasSomethingDeletable = false;
                            foreach (ISegment s in textArea.Selection.Segments)
                            {
                                method = textAreaType.GetMethod("GetDeletableSegments", BindingFlags.Instance | BindingFlags.NonPublic);
                                if ((int)method.Invoke(textArea, new Object[]{s}) > 0)
                                {
                                    hasSomethingDeletable = true;
                                    break;
                                }
                            }
                            if (!hasSomethingDeletable)
                            {
                                // Preserve the caret at read-only boundaries.
                                textArea.Caret.Position = oldCaretPosition;
                            }
                        }
                        method = textAreaType.GetMethod("RemoveSelectedText", BindingFlags.Instance | BindingFlags.NonPublic);
                        method.Invoke(textArea, new Object[]{});
                    }
                    textArea.Caret.BringCaretToView();
                    args.Handled = true;
                }
            };
        }

        internal static void CanDelete(object target, CanExecuteRoutedEventArgs args)
        {
            TextArea textArea = GetTextArea(target);
            if (textArea != null && textArea.Document != null)
            {
                args.CanExecute = !textArea.Selection.IsEmpty;
                args.Handled = true;
            }
        }

        const string LineSelectedType = "MSDEVLineSelect";  // This is the type VS 2003 and 2005 use for flagging a whole line copy

        struct VerySimpleSegment : ISegment
	    {
		    public readonly int Offset, Length;

		    int ISegment.Offset {
			    get { return Offset; }
		    }

		    int ISegment.Length {
			    get { return Length; }
		    }

		    public int EndOffset {
			    get {
				    return Offset + Length;
			    }
		    }

            public VerySimpleSegment(int offset, int length)
		    {
			    this.Offset = offset;
			    this.Length = length;
		    }
        }
    }
}
