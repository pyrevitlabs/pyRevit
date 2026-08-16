// Copyright (c) 2010 Joe Moorhouse

using ICSharpCode.AvalonEdit.CodeCompletion;
using ICSharpCode.AvalonEdit.Document;
using ICSharpCode.AvalonEdit.Editing;
using Microsoft.Scripting.Hosting.Shell;
using System;

namespace PythonConsoleControl
{
    /// <summary>
    /// Represents an item in the completion list.
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

        public object Content
        {
            get { return this.Text; }
        }

        public object Description
        {
            get
            {
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
