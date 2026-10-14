// Copyright (c) 2010 Joe Moorhouse

using System;
using System.Collections.Generic;
using System.Text;
using ICSharpCode.AvalonEdit;
using ICSharpCode.AvalonEdit.Editing;
using ICSharpCode.AvalonEdit.Document;
using ICSharpCode.AvalonEdit.CodeCompletion;
using System.Windows;
using System.Windows.Threading;
using System.Windows.Input;
using System.Threading;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Windows.Interop;

namespace PythonConsoleControl
{
    /// <summary>
    /// Adapts AvalonEdit for console input, output, and completion.
    /// </summary>
    public class PythonTextEditor : IDisposable
    {
        internal TextEditor textEditor;
        internal TextArea textArea;
        StringBuilder writeBuffer = new StringBuilder();
        volatile bool writeInProgress = false;
        PythonConsoleCompletionWindow completionWindow = null;
        int completionEventIndex = 0;
        int descriptionEventIndex = 1;
        WaitHandle[] completionWaitHandles;
        AutoResetEvent completionRequestedEvent = new AutoResetEvent(false);
        AutoResetEvent descriptionRequestedEvent = new AutoResetEvent(false);
        Thread completionThread;
        PythonConsoleCompletionDataProvider completionProvider = null;
        Action<Action> completionDispatcher = new Action<Action>((command) => command());
        readonly PythonExecution completionExecution = new PythonExecution();
        readonly ManualResetEvent disposedEvent = new ManualResetEvent(false);
        volatile bool disposed;

        public PythonTextEditor(TextEditor textEditor)
        {
            this.textEditor = textEditor;
            this.textArea = textEditor.TextArea;
            completionWaitHandles = new WaitHandle[] { completionRequestedEvent, descriptionRequestedEvent, disposedEvent };
            completionThread = new Thread(new ThreadStart(Completion));
            completionThread.Priority = ThreadPriority.Lowest;
            completionThread.IsBackground = true;
            completionThread.Start();
        }

        /// <summary>
        /// Set the dispatcher to use to force code completion to happen on a specific thread
        /// if necessary.
        /// </summary>
        public void SetCompletionDispatcher(Action<Action> newDispatcher)
        {
            completionDispatcher = command => completionExecution.Run(
                completionProvider.Engine, command, newDispatcher, IsCompletionStopKeyPressed);
        }


        [DllImport("user32.dll")]
        static extern short GetAsyncKeyState(int virtualKey);

        [DllImport("user32.dll")]
        static extern IntPtr GetForegroundWindow();

        [DllImport("user32.dll")]
        static extern IntPtr GetAncestor(IntPtr window, uint flags);

        bool HasForegroundInput()
        {
            if (!textArea.Dispatcher.CheckAccess() || !textArea.IsKeyboardFocusWithin) return false;
            var source = PresentationSource.FromVisual(textArea) as HwndSource;
            return source != null && GetAncestor(source.Handle, 2) == GetAncestor(GetForegroundWindow(), 2);
        }

        internal bool IsInterruptKeyPressed()
        {
            return HasForegroundInput() && SelectionLength == 0
                && (GetAsyncKeyState(0x11) & 0x8000) != 0
                && (GetAsyncKeyState(0x43) & 0x8000) != 0;
        }

        bool IsCompletionStopKeyPressed()
        {
            return HasForegroundInput() && (GetAsyncKeyState(0x0D) & 0x8000) != 0;
        }

        public void Dispose()
        {
            if (disposed) return;
            disposed = true;
            completionExecution.Dispose();
            disposedEvent.Set();
            completionWindow?.Close();
        }

        internal void WaitForExit()
        {
            completionThread.Join();
            completionRequestedEvent.Dispose();
            descriptionRequestedEvent.Dispose();
            disposedEvent.Dispose();
        }
        /// <summary>
        /// Whether completion popups should render with the dark theme. Set by the host control
        /// when its theme is applied; read each time a completion window is created.
        /// </summary>
        public bool UseDarkCompletionTheme { get; set; }

        public bool WriteInProgress
        {
            get { return writeInProgress; }
        }

        public ICollection<CommandBinding> CommandBindings
        {
            get { return (this.textArea.ActiveInputHandler as TextAreaDefaultInputHandler).CommandBindings; }
        }

        public void Write(string text)
        {
            Write(text, false, true);
        }

        public void Write(string text, bool allowSynchronous, bool moveToEnd)
        {
            if (disposed) return;
            text = text.Replace("\r\r\n", "\r\n");
            text = text.Replace("\r\n", "\n");
            text = text.Replace("\0", "");

            if (allowSynchronous)
            {
                if (moveToEnd)
                {
                    MoveToEnd();
                }
                PerformTextInput(text);
                return;
            }
            lock (writeBuffer)
            {
                writeBuffer.Append(text);
            }
            if (!writeInProgress)
            {
                writeInProgress = true;
                ThreadPool.QueueUserWorkItem(new WaitCallback(CheckAndOutputWriteBuffer), moveToEnd);
            }
        }

        private void CheckAndOutputWriteBuffer(Object stateInfo)
        {
            bool moveToEnd = (bool)stateInfo;
            using var writeCompletedEvent = new AutoResetEvent(false);
            Action action = new Action(delegate()
            {
                try
                {
                    if (disposed) return;
                    string toWrite;
                    lock (writeBuffer)
                    {
                        toWrite = writeBuffer.ToString();
                        writeBuffer.Remove(0, writeBuffer.Length);
                    }
                    if (moveToEnd) MoveToEnd();
                    PerformTextInput(toWrite);
                }
                finally { writeCompletedEvent.Set(); }
            });
            while (!disposed)
            {
                textArea.Dispatcher.BeginInvoke(action, DispatcherPriority.Normal);
                writeCompletedEvent.WaitOne();
                lock (writeBuffer)
                {
                    if (writeBuffer.Length == 0)
                    {
                        writeInProgress = false;
                        break;
                    }
                }
            }
        }

        private void MoveToEnd()
        {
            int lineCount = textArea.Document.LineCount;
            if (textArea.Caret.Line != lineCount) textArea.Caret.Line = textArea.Document.LineCount;
            int column = textArea.Document.Lines[lineCount - 1].Length + 1;
            if (textArea.Caret.Column != column) textArea.Caret.Column = column;
        }

        private void PerformTextInput(string text)
        {
            if (text == "\n" || text == "\r\n")
            {
                string newLine = TextUtilities.GetNewLineFromDocument(textArea.Document, textArea.Caret.Line);
                using (textArea.Document.RunUpdate())
                {
                    textArea.Selection.ReplaceSelectionWithText(newLine);
                }
            }
            else
                textArea.Selection.ReplaceSelectionWithText(text);
            textArea.Caret.BringCaretToView();
        }

        public int Column
        {
            get { return textArea.Caret.Column; }
            set { textArea.Caret.Column = value; }
        }

        /// <summary>
        /// Gets the current cursor line.
        /// </summary>
        public int Line
        {
            get { return textArea.Caret.Line; }
            set { textArea.Caret.Line = value; }
        }

        /// <summary>
        /// Gets the total number of lines in the text editor.
        /// </summary>
        public int TotalLines
        {
            get { return textArea.Document.LineCount; }
        }

        public delegate string StringAction();
        /// <summary>
        /// Gets the text for the specified line.
        /// </summary>
        public string GetLine(int index)
        {
            return (string)textArea.Dispatcher.Invoke(new StringAction(delegate()
            {
                DocumentLine line = textArea.Document.Lines[index];
                return textArea.Document.GetText(line);
            }));
        }

        /// <summary>
        /// Replaces the text at the specified index on the current line with the specified text.
        /// </summary>
        public void Replace(int index, int length, string text)
        {
            int currentLine = textArea.Document.LineCount - 1;
            int startOffset = textArea.Document.Lines[currentLine].Offset;
            textArea.Document.Replace(startOffset + index, length, text);
        }

        public event TextCompositionEventHandler TextEntering
        {
            add { textArea.TextEntering += value; }
            remove { textArea.TextEntering -= value; }
        }

        public event TextCompositionEventHandler TextEntered
        {
            add { textArea.TextEntered += value; }
            remove { textArea.TextEntered -= value; }
        }

        public event KeyEventHandler PreviewKeyDown
        {
            add { textArea.PreviewKeyDown += value; }
            remove { textArea.PreviewKeyDown -= value; }
        }

        public int SelectionStart
        {
            get
            {
                return textArea.Selection.SurroundingSegment.Offset;
            }
        }

        public int SelectionLength
        {
            get
            {
                return textArea.Selection.Length;
            }
        }

        public bool SelectionIsMultiline
        {
            get
            {
                return textArea.Selection.IsMultiline;
            }
        }

        public int SelectionStartColumn
        {
            get
            {
                int startOffset = textArea.Selection.SurroundingSegment.Offset;
                return startOffset - textArea.Document.GetLineByOffset(startOffset).Offset + 1;
            }
        }

        public int SelectionEndColumn
        {
            get
            {
                int endOffset = textArea.Selection.SurroundingSegment.EndOffset;
                return endOffset - textArea.Document.GetLineByOffset(endOffset).Offset + 1;
            }
        }

        public PythonConsoleCompletionDataProvider CompletionProvider
        {
            get { return completionProvider; }
            set { completionProvider = value; }
        }

        public Thread CompletionThread
        {
            get { return completionThread; }
        }

        public bool StopCompletion()
        {
            if (completionExecution.IsRunning)
            {
                completionExecution.Interrupt();
                return true;
            }
            return false;
        }

        public PythonConsoleCompletionWindow CompletionWindow
        {
            get { return completionWindow; }
        }

        public void ShowCompletionWindow()
        {
            completionRequestedEvent.Set();
        }

        public void UpdateCompletionDescription()
        {
            descriptionRequestedEvent.Set();
        }

        /// <summary>
        /// Perform completion actions on the background completion thread.
        /// </summary>
        void Completion()
        {
            while (true)
            {
                int action = WaitHandle.WaitAny(completionWaitHandles);
                if (completionWaitHandles[action] == disposedEvent) return;
                try
                {
                if (action == completionEventIndex && completionProvider != null) BackgroundShowCompletionWindow();
                if (action == descriptionEventIndex && completionProvider != null && completionWindow != null) BackgroundUpdateCompletionDescription();
                }
                catch (Microsoft.Scripting.KeyboardInterruptException) { }
                catch (OperationCanceledException) { }
            }
        }

        /// <summary>
        /// Obtain completions (this runs in its own thread)
        /// </summary>
        internal void BackgroundShowCompletionWindow()
        {
            string itemForCompletion = "";
            textArea.Dispatcher.Invoke(new Action(delegate()
            {
                if (disposed) return;
                DocumentLine line = textArea.Document.Lines[textArea.Caret.Line - 1];
                itemForCompletion = textArea.Document.GetText(line.Offset, textArea.Caret.Column - 1);
            }));
            if (disposed) return;


            completionDispatcher.Invoke(new Action(delegate()
            {
                try
                {
                    var completionInfo = completionProvider.GenerateCompletionData(itemForCompletion);

                    if (completionInfo != null && !disposed)
                    {
                        ICompletionData[] completions = completionInfo.Item1;
                        string objectName = completionInfo.Item2;
                        string memberName = completionInfo.Item3;

                        if (completions.Length > 0) textArea.Dispatcher.BeginInvoke(new Action(delegate()
                        {
                            if (disposed) return;
                            completionWindow = new PythonConsoleCompletionWindow(textArea, this);
                            completionWindow.ApplyTheme(UseDarkCompletionTheme);
                            IList<ICompletionData> data = completionWindow.CompletionList.CompletionData;
                            foreach (ICompletionData completion in completions)
                            {
                                data.Add(completion);
                            }
                            completionWindow.Show();
                            completionWindow.Closed += delegate
                            {
                                completionWindow = null;
                            };

                            completionWindow.StartOffset -= memberName.Length;
                            completionWindow.CompletionList.SelectItem(textArea.Document.GetText(completionWindow.StartOffset, memberName.Length));
                        }));
                    }
                }
                catch (Microsoft.Scripting.KeyboardInterruptException) { throw; }
                catch (Exception exception)
                {
                    MessageBox.Show(exception.ToString(), "Error");
                }

            }));
        }

        internal void BackgroundUpdateCompletionDescription()
        {
            completionDispatcher.Invoke(new Action(delegate()
            {
                try
                {
                    completionWindow.UpdateCurrentItemDescription();
                }
                catch (Microsoft.Scripting.KeyboardInterruptException) { throw; }
                catch (Exception exception)
                {
                    MessageBox.Show(exception.ToString(), "Error");
                }

            }));
        }

        public void RequestCompletioninsertion(TextCompositionEventArgs e)
        {
            if (completionWindow != null) completionWindow.CompletionList.RequestInsertion(e);
            StopCompletion();
        }

    }
}
