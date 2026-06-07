// Copyright (c) 2010 Joe Moorhouse

using ICSharpCode.AvalonEdit.CodeCompletion;
using ICSharpCode.AvalonEdit.Document;
using ICSharpCode.AvalonEdit.Editing;
using Microsoft.Scripting.Hosting.Shell;
using System;

namespace PythonConsoleControl
{
    /// <summary>
    /// Implements AvalonEdit ICompletionData interface to provide the entries in the completion drop down.
    /// </summary>
    public class PythonCompletionData : ICompletionData
    {
        private CommandLine commandLine;

        public PythonCompletionData(string text, string stub, CommandLine commandLine, bool isInstance)
        {
            this.Text = text;
            this.Stub = stub;
            this.commandLine = commandLine;
            this.IsInstance = isInstance;
        }

        public System.Windows.Media.ImageSource Image
        {
            get { return null; }
        }

        public string Text { get; private set; }

        public string Stub { get; private set; }

        public bool IsInstance { get; private set; }

        // Use this property if you want to show a fancy UIElement in the drop down list.
        public object Content
        {
            get { return this.Text; }
        }

        public object Description
        {
            get
            {
                // Do nothing: description now updated externally and asynchronously.
                return "Not available";
            }
        }

        public double Priority { get { return 0; } }

        public void Complete(TextArea textArea, ISegment completionSegment, EventArgs insertionRequestEventArgs)
        {
            textArea.Document.Replace(completionSegment, this.Text);
        }
    }
}