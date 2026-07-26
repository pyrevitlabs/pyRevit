// Copyright (c) 2010 Joe Moorhouse

using System;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using Microsoft.Scripting.Hosting.Shell;
using System.Windows.Input;
using Microsoft.Scripting;
using Microsoft.Scripting.Hosting;
using System.Diagnostics;
using System.Windows;
using System.Windows.Threading;
using ICSharpCode.AvalonEdit.Editing;
using ICSharpCode.AvalonEdit.Document;
using Style = Microsoft.Scripting.Hosting.Shell.Style;

namespace PythonConsoleControl
{
    public delegate void ConsoleInitializedEventHandler(object sender, EventArgs e);

    /// <summary>
    /// Custom IronPython console. The command dispacher runs on a separate UI thread from the REPL
    /// and also from the WPF control.
    /// </summary>
    public class PythonConsole : IConsole, IDisposable
    {

        Action<Action> commandDispatcher;
        public Action<Action> GetCommandDispatcherSafe()
        {
            if (commandDispatcher == null)
            {
                try
                {
                    var languageContext = Microsoft.Scripting.Hosting.Providers.HostingHelpers.GetLanguageContext(commandLine.ScriptScope.Engine);
                    var pythonContext = (IronPython.Runtime.PythonContext)languageContext;
                    commandDispatcher = pythonContext.GetSetCommandDispatcher(null);
                    pythonContext.GetSetCommandDispatcher(commandDispatcher);
                }
                catch (Exception ex)
                {
                    Debug.WriteLine("Failed to get dispatcher: " + ex.Message);
                    commandDispatcher = action => action(); // fallback dispatcher
                }
            }
            return commandDispatcher;
        }

        bool allowFullAutocompletion = true;
        public bool AllowFullAutocompletion
        {
            get { return allowFullAutocompletion; }
            set { allowFullAutocompletion = value; }
        }

        bool disableAutocompletionForCallables = true;
        public bool DisableAutocompletionForCallables
        {
            get { return disableAutocompletionForCallables; }
            set
            {
                if (textEditor.CompletionProvider != null) textEditor.CompletionProvider.ExcludeCallables = value;
                disableAutocompletionForCallables = value;
            }
        }

        bool allowCtrlSpaceAutocompletion = true;
        public bool AllowCtrlSpaceAutocompletion
        {
            get { return allowCtrlSpaceAutocompletion; }
            set { allowCtrlSpaceAutocompletion = value; }
        }

        PythonTextEditor textEditor;
        int lineReceivedEventIndex = 0; // The index into the waitHandles array where the lineReceivedEvent is stored.
        ManualResetEvent lineReceivedEvent = new ManualResetEvent(false);
        ManualResetEvent disposedEvent = new ManualResetEvent(false);
        AutoResetEvent statementsExecutionRequestedEvent = new AutoResetEvent(false);
        WaitHandle[] waitHandles;
        int promptLength = 4;
        List<string> previousLines = new List<string>();
        CommandLine commandLine;
        CommandLineHistory commandLineHistory = new CommandLineHistory();

        volatile bool executing = false;

        // This is the thread upon which all commands execute unless the dipatcher is overridden.
        Thread dispatcherThread;
        public Dispatcher dispatcher;

        string scriptText = String.Empty;
        bool consoleInitialized = false;
        string prompt;

        public event ConsoleInitializedEventHandler ConsoleInitialized;

        public ScriptScope ScriptScope
        {
            get { return commandLine.ScriptScope; }
        }

        public PythonConsole(PythonTextEditor textEditor, CommandLine commandLine)
        {
            waitHandles = new WaitHandle[] { lineReceivedEvent, disposedEvent };

            this.commandLine = commandLine;
            this.textEditor = textEditor;
            textEditor.CompletionProvider = new PythonConsoleCompletionDataProvider(commandLine) { ExcludeCallables = disableAutocompletionForCallables };
            textEditor.PreviewKeyDown += textEditor_PreviewKeyDown;
            textEditor.TextEntering += textEditor_TextEntering;
            dispatcherThread = new Thread(new ThreadStart(DispatcherThreadStartingPoint));
            dispatcherThread.SetApartmentState(ApartmentState.STA);
            dispatcherThread.IsBackground = true;
            dispatcherThread.Start();

            // Only required when running outside REP loop.
            prompt = ">>> ";

            // Set commands:
            this.textEditor.textArea.Dispatcher.Invoke(new Action(delegate()
            {
                CommandBinding pasteBinding = null;
                CommandBinding copyBinding = null;
                CommandBinding cutBinding = null;
                CommandBinding undoBinding = null;
                CommandBinding deleteBinding = null;
                foreach (CommandBinding commandBinding in (this.textEditor.textArea.CommandBindings))
                {
                    if (commandBinding.Command == ApplicationCommands.Paste) pasteBinding = commandBinding;
                    if (commandBinding.Command == ApplicationCommands.Copy) copyBinding = commandBinding;
                    if (commandBinding.Command == ApplicationCommands.Cut) cutBinding = commandBinding;
                    if (commandBinding.Command == ApplicationCommands.Undo) undoBinding = commandBinding;
                    if (commandBinding.Command == ApplicationCommands.Delete) deleteBinding = commandBinding;
                }
                // Remove current bindings completely from control. These are static so modifying them will cause other
                // controls' behaviour to change too.
                if (pasteBinding != null) this.textEditor.textArea.CommandBindings.Remove(pasteBinding);
                if (copyBinding != null) this.textEditor.textArea.CommandBindings.Remove(copyBinding);
                if (cutBinding != null) this.textEditor.textArea.CommandBindings.Remove(cutBinding);
                if (undoBinding != null) this.textEditor.textArea.CommandBindings.Remove(undoBinding);
                if (deleteBinding != null) this.textEditor.textArea.CommandBindings.Remove(deleteBinding);
                this.textEditor.textArea.CommandBindings.Add(new CommandBinding(ApplicationCommands.Paste, OnPaste, CanPaste));
                this.textEditor.textArea.CommandBindings.Add(new CommandBinding(ApplicationCommands.Copy, OnCopy, PythonEditingCommandHandler.CanCutOrCopy));
                this.textEditor.textArea.CommandBindings.Add(new CommandBinding(ApplicationCommands.Cut, PythonEditingCommandHandler.OnCut, CanCut));
                this.textEditor.textArea.CommandBindings.Add(new CommandBinding(ApplicationCommands.Undo, OnUndo, CanUndo));
                this.textEditor.textArea.CommandBindings.Add(new CommandBinding(ApplicationCommands.Delete, PythonEditingCommandHandler.OnDelete(ApplicationCommands.NotACommand), CanDeleteCommand));

            }));
            // Set dispatcher to run on a UI thread independent of both the Control UI thread and thread running the REPL.
            WhenConsoleInitialized(delegate
            {
                SetCommandDispatcher(DispatchCommand);
            });
        }

        public Action<Action> GetCommandDispatcher()
        {
            var languageContext = Microsoft.Scripting.Hosting.Providers.HostingHelpers.GetLanguageContext(commandLine.ScriptScope.Engine);
            var pythonContext = (IronPython.Runtime.PythonContext)languageContext;
            var result = pythonContext.GetSetCommandDispatcher(null);
            pythonContext.GetSetCommandDispatcher(result);
            return result;
        }

        public void SetCommandDispatcher(Action<Action> newDispatcher)
        {
            var languageContext = Microsoft.Scripting.Hosting.Providers.HostingHelpers.GetLanguageContext(commandLine.ScriptScope.Engine);
            var pythonContext = (IronPython.Runtime.PythonContext)languageContext;
            pythonContext.GetSetCommandDispatcher(newDispatcher);
        }

        protected void DispatchCommand(Delegate command)
        {
            if (command != null)
            {
                // Slightly involved form to enable keyboard interrupt to work.
                executing = true;
                var operation = dispatcher.BeginInvoke(DispatcherPriority.Normal, command);
                while (executing)
                {
                    if (operation.Status != DispatcherOperationStatus.Completed)
                        operation.Wait(TimeSpan.FromSeconds(1));
                    if (operation.Status == DispatcherOperationStatus.Completed)
                        executing = false;
                }
            }
        }

        /// <summary>
        /// Perform action only after the console was initialized.
        /// </summary>
        public void WhenConsoleInitialized(Action action)
        {
            if (consoleInitialized)
            {
                action();
            }
            else
            {
                ConsoleInitialized += (sender, args) => action();
            }
        }

        private void DispatcherThreadStartingPoint()
        {
            dispatcher = new Window().Dispatcher;
            while (true)
            {
                try
                {
                    System.Windows.Threading.Dispatcher.Run();
                }
                catch (ThreadAbortException tae)
                {
                    if (tae.ExceptionState is Microsoft.Scripting.KeyboardInterruptException)
                    {
                        Thread.ResetAbort();
                        executing = false;
                    }
                }
            }
        }

        public void SetDispatcher(Dispatcher dispatcher)
        {
            this.dispatcher = dispatcher;
        }

        public void Dispose()
        {
            disposedEvent.Set();
            textEditor.PreviewKeyDown -= textEditor_PreviewKeyDown;
            textEditor.TextEntering -= textEditor_TextEntering;
        }

        public TextWriter Output
        {
            get { return null; }
            set { }
        }

        public TextWriter ErrorOutput
        {
            get { return null; }
            set { }
        }

        #region CommandHandling
        protected void CanPaste(object target, CanExecuteRoutedEventArgs args)
        {
            if (IsInReadOnlyRegion)
            {
                args.CanExecute = false;
            }
            else
                args.CanExecute = true;
        }

        protected void CanCut(object target, CanExecuteRoutedEventArgs args)
        {
            if (!CanDelete)
            {
                args.CanExecute = false;
            }
            else
                PythonEditingCommandHandler.CanCutOrCopy(target, args);
        }

        protected void CanDeleteCommand(object target, CanExecuteRoutedEventArgs args)
        {
            if (!CanDelete)
            {
                args.CanExecute = false;
            }
            else
                PythonEditingCommandHandler.CanDelete(target, args);
        }

        protected void CanUndo(object target, CanExecuteRoutedEventArgs args)
        {
            args.CanExecute = false;
        }

        protected void OnPaste(object target, ExecutedRoutedEventArgs args)
        {
            if (target != textEditor.textArea) return;
            TextArea textArea = textEditor.textArea;
            if (textArea != null && textArea.Document != null)
            {
                Debug.WriteLine(Clipboard.GetText(TextDataFormat.Html));

                // convert text back to correct newlines for this document
                string newLine = TextUtilities.GetNewLineFromDocument(textArea.Document, textArea.Caret.Line);
                string text = TextUtilities.NormalizeNewLines(Clipboard.GetText(), newLine);
                string[] commands = text.Split(new String[] { newLine }, StringSplitOptions.None);
                string scriptText = "";
                if (commands.Length > 1)
                {
                    text = newLine;
                    foreach (string command in commands)
                    {
                        text += "... " + command + newLine;
                        scriptText += command.Replace("\t", "   ") + newLine;
                    }
                }

                if (!string.IsNullOrEmpty(text))
                {
                    bool fullLine = textArea.Options.CutCopyWholeLine && Clipboard.ContainsData(LineSelectedType);
                    bool rectangular = Clipboard.ContainsData(RectangleSelection.RectangularSelectionDataType);
                    if (fullLine)
                    {
                        DocumentLine currentLine = textArea.Document.GetLineByNumber(textArea.Caret.Line);
                        if (textArea.ReadOnlySectionProvider.CanInsert(currentLine.Offset))
                        {
                            textArea.Document.Insert(currentLine.Offset, text);
                        }
                    }
                    else if (rectangular && textArea.Selection.IsEmpty)
                    {
                        if (!RectangleSelection.PerformRectangularPaste(textArea, textArea.Caret.Position, text, false))
                            textEditor.Write(text, false, false);
                    }
                    else
                    {
                        textEditor.Write(text, false, false);
                    }
                }
                textArea.Caret.BringCaretToView();
                args.Handled = true;

                if (commands.Length > 1)
                {
                    lock (this.scriptText)
                    {
                        this.scriptText = scriptText;
                    }
                    dispatcher.BeginInvoke(new Action(delegate() { ExecuteStatements(); }));
                }
            }
        }

        protected void OnCopy(object target, ExecutedRoutedEventArgs args)
        {
            if (target != textEditor.textArea) return;
            if (textEditor.SelectionLength == 0 && executing)
            {
                // Send the 'Ctrl-C' abort
                //if (!IsInReadOnlyRegion)
                //{
                MoveToHomePosition();
                //textEditor.Column = GetLastTextEditorLine().Length + 1;
                //textEditor.Write(Environment.NewLine);
                //}
                dispatcherThread.Abort(new Microsoft.Scripting.KeyboardInterruptException(""));
                args.Handled = true;
            }
            else PythonEditingCommandHandler.OnCopy(target, args);
        }

        const string LineSelectedType = "MSDEVLineSelect";  // This is the type VS 2003 and 2005 use for flagging a whole line copy

        protected void OnUndo(object target, ExecutedRoutedEventArgs args)
        {
        }
        #endregion

        /// <summary>
        /// Run externally provided statements in the Console Engine.
        /// </summary>
        /// <param name="statements"></param>
        public void RunStatements(string statements)
        {
            MoveToHomePosition();
            lock (this.scriptText)
            {
                this.scriptText = statements;
            }
            dispatcher.BeginInvoke(new Action(delegate() { ExecuteStatements(); }));
        }

        /// <summary>
        /// Run on the statement execution thread.
        /// </summary>
        void ExecuteStatements()
        {
            lock (scriptText)
            {
                textEditor.Write("\r\n");
                ScriptSource scriptSource = commandLine.ScriptScope.Engine.CreateScriptSourceFromString(scriptText, SourceCodeKind.Statements);
                string error = "";
                try
                {
                    executing = true;
                    var errors = new ErrorReporter();
                    var command = scriptSource.Compile(errors);
                    if (command == null)
                    {
                        // compilation failed
                        error = "Syntax Error: " + string.Join("\nSyntax Error: ", errors.Errors) + "\n";
                    }
                    else
                    {
                        Exception capturedEx = null;
                        var dispatcher = GetCommandDispatcherSafe();

                        ManualResetEventSlim done = new ManualResetEventSlim();

                        dispatcher(() =>
                        {
                            try
                            {
                                scriptSource.Execute(commandLine.ScriptScope);
                            }
                            catch (Exception ex)
                            {
                                capturedEx = ex;
                            }
                            finally
                            {
                                done.Set();
                            }
                        });

                        done.Wait();

                        if (capturedEx != null)
                        {
                            var eo = commandLine.ScriptScope.Engine.GetService<ExceptionOperations>();
                            error = eo.FormatException(capturedEx) + Environment.NewLine;
                        }
                    }
                }
                catch (ThreadAbortException tae)
                {
                    if (tae.ExceptionState is Microsoft.Scripting.KeyboardInterruptException) Thread.ResetAbort();
                    error = "KeyboardInterrupt" + System.Environment.NewLine;
                }
                catch (Microsoft.Scripting.SyntaxErrorException exception)
                {
                    ExceptionOperations eo;
                    eo = commandLine.ScriptScope.Engine.GetService<ExceptionOperations>();
                    error = eo.FormatException(exception);
                }
                catch (Exception exception)
                {
                    ExceptionOperations eo;
                    eo = commandLine.ScriptScope.Engine.GetService<ExceptionOperations>();
                    error = eo.FormatException(exception) + System.Environment.NewLine;
                }
                executing = false;
                if (error != "") textEditor.Write(error);
                textEditor.Write(prompt);
            }
        }

        /// <summary>
        /// Returns the next line typed in by the console user. If no line is available this method
        /// will block.
        /// </summary>
        public string ReadLine(int autoIndentSize)
        {
            string indent = String.Empty;
            if (autoIndentSize > 0)
            {
                indent = String.Empty.PadLeft(autoIndentSize);
                Write(indent, Style.Prompt);
            }

            string line = ReadLineFromTextEditor();
            if (line != null)
            {
                return indent + line;
            }
            return null;
        }

        /// <summary>
        /// Writes text to the console.
        /// </summary>
        public void Write(string text, Style style)
        {
            textEditor.Write(text);
            if (style == Style.Prompt)
            {
                promptLength = text.Length;
                if (!consoleInitialized)
                {
                    consoleInitialized = true;
                    if (ConsoleInitialized != null) ConsoleInitialized(this, EventArgs.Empty);
                }
            }
        }

        /// <summary>
        /// Writes text followed by a newline to the console.
        /// </summary>
        public void WriteLine(string text, Style style)
        {
            Write(text + Environment.NewLine, style);
        }

        /// <summary>
        /// Writes an empty line to the console.
        /// </summary>
        public void WriteLine()
        {
            Write(Environment.NewLine, Style.Out);
        }

        /// <summary>
        /// Indicates whether there is a line already read by the console and waiting to be processed.
        /// </summary>
        public bool IsLineAvailable
        {
            get
            {
                lock (previousLines)
                {
                    return previousLines.Count > 0;
                }
            }
        }

        /// <summary>
        /// Gets the text that is yet to be processed from the console. This is the text that is being
        /// typed in by the user who has not yet pressed the enter key.
        /// </summary>
        public string GetCurrentLine()
        {
            string fullLine = GetLastTextEditorLine();
            return fullLine.Substring(promptLength);
        }

        /// <summary>
        /// Gets the lines that have not been returned by the ReadLine method. This does not
        /// include the current line.
        /// </summary>
        public string[] GetUnreadLines()
        {
            return previousLines.ToArray();
        }

        string GetLastTextEditorLine()
        {
            return textEditor.GetLine(textEditor.TotalLines - 1);
        }

        string ReadLineFromTextEditor()
        {
            int result = WaitHandle.WaitAny(waitHandles);
            if (result == lineReceivedEventIndex)
            {
                lock (previousLines)
                {
                    string line = previousLines[0];
                    previousLines.RemoveAt(0);
                    if (previousLines.Count == 0)
                    {
                        lineReceivedEvent.Reset();
                    }
                    return line;
                }
            }
            return null;
        }

        /// <summary>
        /// Processes characters entered into the text editor by the user.
        /// </summary>
        void textEditor_PreviewKeyDown(object sender, KeyEventArgs e)
        {
            switch (e.Key)
            {
                case Key.Delete:
                    if (!CanDelete) e.Handled = true;
                    return;
                case Key.Tab:
                    if (IsInReadOnlyRegion) e.Handled = true;
                    return;
                case Key.Back:
                    if (!CanBackspace) e.Handled = true;
                    return;
                case Key.Home:
                    MoveToHomePosition();
                    e.Handled = true;
                    return;
                case Key.Down:
                    if (!IsInReadOnlyRegion) MoveToNextCommandLine();
                    e.Handled = true;
                    return;
                case Key.Up:
                    if (!IsInReadOnlyRegion) MoveToPreviousCommandLine();
                    e.Handled = true;
                    return;
            }
        }

        /// <summary>
        /// Processes characters entering into the text editor by the user.
        /// </summary>
        void textEditor_TextEntering(object sender, TextCompositionEventArgs e)
        {
            if (e.Text.Length > 0)
            {
                if (!char.IsLetterOrDigit(e.Text[0]) || e.Text[0] == '_') // Underscore is a fairly common character in Revit API names.
                {
                    // Whenever a non-letter is typed while the completion window is open,
                    // insert the currently selected element.
                    textEditor.RequestCompletioninsertion(e);
                }
            }

            if (IsInReadOnlyRegion)
            {
                e.Handled = true;
            }
            else
            {
                if (e.Text[0] == '\n')
                {
                    OnEnterKeyPressed();
                }

                if (e.Text[0] == '.' && allowFullAutocompletion)
                {
                    textEditor.ShowCompletionWindow();
                }

                if ((e.Text[0] == ' ') && (Keyboard.Modifiers == ModifierKeys.Control))
                {
                    e.Handled = true;
                    if (allowCtrlSpaceAutocompletion) textEditor.ShowCompletionWindow();
                }
            }
        }

        /// <summary>
        /// Move cursor to the end of the line before retrieving the line.
        /// </summary>
        void OnEnterKeyPressed()
        {
            textEditor.StopCompletion();
            if (textEditor.WriteInProgress) return;
            lock (previousLines)
            {
                // Move cursor to the end of the line.
                textEditor.Column = GetLastTextEditorLine().Length + 1;

                // Append line.
                string currentLine = GetCurrentLine();
                previousLines.Add(currentLine);
                commandLineHistory.Add(currentLine);

                lineReceivedEvent.Set();
            }
        }

        /// <summary>
        /// Returns true if the cursor is in a readonly text editor region.
        /// </summary>
        bool IsInReadOnlyRegion
        {
            get { return IsCurrentLineReadOnly || IsInPrompt; }
        }

        /// <summary>
        /// Only the last line in the text editor is not read only.
        /// </summary>
        bool IsCurrentLineReadOnly
        {
            get { return textEditor.Line < textEditor.TotalLines; }
        }

        /// <summary>
        /// Determines whether the current cursor position is in a prompt.
        /// </summary>
        bool IsInPrompt
        {
            get { return textEditor.Column - promptLength - 1 < 0; }
        }

        /// <summary>
        /// Returns true if the user can delete at the current cursor position.
        /// </summary>
        bool CanDelete
        {
            get
            {
                if (textEditor.SelectionLength > 0) return SelectionIsDeletable;
                else return !IsInReadOnlyRegion;
            }
        }

        /// <summary>
        /// Returns true if the user can backspace at the current cursor position.
        /// </summary>
        bool CanBackspace
        {
            get
            {
                if (textEditor.SelectionLength > 0) return SelectionIsDeletable;
                else
                {
                    int cursorIndex = textEditor.Column - promptLength - 1;
                    return !IsCurrentLineReadOnly && (cursorIndex > 0 || (cursorIndex == 0 && textEditor.SelectionLength > 0));
                }
            }
        }

        bool SelectionIsDeletable
        {
            get
            {
                return (!textEditor.SelectionIsMultiline
                    && !IsCurrentLineReadOnly
                    && (textEditor.SelectionStartColumn - promptLength - 1 >= 0)
                    && (textEditor.SelectionEndColumn - promptLength - 1 >= 0));
            }
        }

        /// <summary>
        /// The home position is at the start of the line after the prompt.
        /// </summary>
        void MoveToHomePosition()
        {
            textEditor.Line = textEditor.TotalLines;
            textEditor.Column = promptLength + 1;
        }

        /// <summary>
        /// Shows the previous command line in the command line history.
        /// </summary>
        void MoveToPreviousCommandLine()
        {
            if (commandLineHistory.MovePrevious())
            {
                ReplaceCurrentLineTextAfterPrompt(commandLineHistory.Current);
            }
        }

        /// <summary>
        /// Shows the next command line in the command line history.
        /// </summary>
        void MoveToNextCommandLine()
        {
            textEditor.Line = textEditor.TotalLines;
            if (commandLineHistory.MoveNext())
            {
                ReplaceCurrentLineTextAfterPrompt(commandLineHistory.Current);
            }
        }

        /// <summary>
        /// Replaces the current line text after the prompt with the specified text.
        /// </summary>
        void ReplaceCurrentLineTextAfterPrompt(string text)
        {
            string currentLine = GetCurrentLine();
            textEditor.Replace(promptLength, currentLine.Length, text);

            // Put cursor at end.
            textEditor.Column = promptLength + text.Length + 1;
        }
    }

    public class ErrorReporter : ErrorListener
    {
        public List<String> Errors = new List<string>();

        public override void ErrorReported(ScriptSource source, string message, SourceSpan span, int errorCode, Severity severity)
        {
            Errors.Add(string.Format("{0} (line {1})", message, span.Start.Line));
        }

        public int Count
        {
            get { return Errors.Count; }
        }
    }
}
