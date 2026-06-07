// Copyright (c) 2010 Joe Moorhouse

using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Input;
using System.Windows.Threading;
using ICSharpCode.AvalonEdit.Document;
using ICSharpCode.AvalonEdit.Editing;
using ICSharpCode.AvalonEdit.Rendering;
using ICSharpCode.AvalonEdit.CodeCompletion;
using System.Reflection;

namespace PythonConsoleControl
{
    public delegate void DescriptionUpdateDelegate(string description);
    
    /// <summary>
    /// The code completion window.
    /// </summary>
    public class PythonConsoleCompletionWindow : CompletionWindowBase
    {
        readonly CompletionList completionList = new CompletionList();
        ToolTip toolTip = new ToolTip();
        DispatcherTimer updateDescription;
        TimeSpan updateDescriptionInterval;
        PythonTextEditor textEditor;
        PythonConsoleCompletionDataProvider completionDataProvider;

        /// <summary>
        /// Gets the completion list used in this completion window.
        /// </summary>
        public CompletionList CompletionList
        {
            get { return completionList; }
        }

        /// <summary>
        /// Creates a new code completion window.
        /// </summary>
        public PythonConsoleCompletionWindow(TextArea textArea, PythonTextEditor textEditor)
            : base(textArea)
        {
            // keep height automatic
            this.completionDataProvider = textEditor.CompletionProvider;
            this.textEditor = textEditor;
            this.CloseAutomatically = true;
            this.SizeToContent = SizeToContent.Height;
            this.MaxHeight = 300;
            this.Width = 175;
            this.Content = completionList;
            // prevent user from resizing window to 0x0
            this.MinHeight = 15;
            this.MinWidth = 30;

            toolTip.PlacementTarget = this;
            toolTip.Placement = PlacementMode.Right;
            toolTip.Closed += toolTip_Closed;

            completionList.InsertionRequested += completionList_InsertionRequested;
            completionList.SelectionChanged += completionList_SelectionChanged;
            AttachEvents();

            updateDescription = new DispatcherTimer();
            updateDescription.Tick += new EventHandler(completionList_UpdateDescription);
            updateDescriptionInterval = TimeSpan.FromSeconds(0.3);

            EventInfo eventInfo = typeof(TextView).GetEvent("ScrollOffsetChanged");
            Delegate methodDelegate = Delegate.CreateDelegate(eventInfo.EventHandlerType, (this as CompletionWindowBase), "TextViewScrollOffsetChanged");
            eventInfo.RemoveEventHandler(this.TextArea.TextView, methodDelegate);
        }

        #region ToolTip handling
        void toolTip_Closed(object sender, RoutedEventArgs e)
        {
            // Clear content after tooltip is closed.
            // We cannot clear is immediately when setting IsOpen=false
            // because the tooltip uses an animation for closing.
            if (toolTip != null)
                toolTip.Content = null;
        }

        void completionList_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            var item = completionList.SelectedItem;
            if (item == null)
            {
                updateDescription.Stop();
                return;
            }
            else
            {
                updateDescription.Interval = updateDescriptionInterval;
                updateDescription.Start();
            }
        }

        void completionList_UpdateDescription(Object sender, EventArgs e)
        {
            updateDescription.Stop();
            textEditor.UpdateCompletionDescription();
        }

        /// <summary>
        /// Update the description of the current item. This is typically called from a separate thread from the main UI thread.
        /// </summary>
        internal void UpdateCurrentItemDescription()
        {
            if (textEditor.StopCompletion())
            {
                updateDescription.Interval = updateDescriptionInterval;
                updateDescription.Start();
                return;
            }
            string stub = "";
            string item = "";
            bool isInstance = false;
            textEditor.textEditor.Dispatcher.Invoke(new Action(delegate()
            {
                PythonCompletionData data = (completionList.SelectedItem as PythonCompletionData);
                if (data == null || toolTip == null)
                    return;
                stub = data.Stub;
                item = data.Text;
                isInstance = data.IsInstance;
            }));
            // Send to the completion thread to generate the description, providing callback.
            completionDataProvider.GenerateDescription(stub, item, completionList_WriteDescription, isInstance);
        }

        void completionList_WriteDescription(string description)
        {
            textEditor.textEditor.Dispatcher.Invoke(new Action(delegate() {
                if (toolTip != null)
                {
                    if (description != null)
                    {
                        toolTip.Content = description;
                        toolTip.IsOpen = true;
                    }
                    else
                    {
                        toolTip.IsOpen = false;
                    }
                }
            }));
        }

        #endregion

        void completionList_InsertionRequested(object sender, EventArgs e)
        {
            Close();
            // The window must close before Complete() is called.
            // If the Complete callback pushes stacked input handlers, we don't want to pop those when the CC window closes.
            var item = completionList.SelectedItem;
            if (item != null)
                item.Complete(this.TextArea, new AnchorSegment(this.TextArea.Document, this.StartOffset, this.EndOffset - this.StartOffset), e);
        }

        void AttachEvents()
        {
            this.TextArea.Caret.PositionChanged += CaretPositionChanged;
            this.TextArea.MouseWheel += textArea_MouseWheel;
            this.TextArea.PreviewTextInput += textArea_PreviewTextInput;
        }

        /// <inheritdoc/>
        protected override void DetachEvents()
        {
            this.TextArea.Caret.PositionChanged -= CaretPositionChanged;
            this.TextArea.MouseWheel -= textArea_MouseWheel;
            this.TextArea.PreviewTextInput -= textArea_PreviewTextInput;
            base.DetachEvents();
        }

        /// <inheritdoc/>
        protected override void OnClosed(EventArgs e)
        {
            base.OnClosed(e);
            if (toolTip != null)
            {
                toolTip.IsOpen = false;
                toolTip = null;
            }
        }

        /// <inheritdoc/>
        protected override void OnKeyDown(KeyEventArgs e)
        {
            base.OnKeyDown(e);
            if (!e.Handled)
            {
                completionList.HandleKey(e);
            }
        }

        void textArea_PreviewTextInput(object sender, TextCompositionEventArgs e)
        {
            e.Handled = RaiseEventPair(this, PreviewTextInputEvent, TextInputEvent,
                                       new TextCompositionEventArgs(e.Device, e.TextComposition));
        }

        void textArea_MouseWheel(object sender, MouseWheelEventArgs e)
        {
            e.Handled = RaiseEventPair(GetScrollEventTarget(),
                                       PreviewMouseWheelEvent, MouseWheelEvent,
                                       new MouseWheelEventArgs(e.MouseDevice, e.Timestamp, e.Delta));
        }

        UIElement GetScrollEventTarget()
        {
            if (completionList == null)
                return this;
            return completionList.ScrollViewer ?? completionList.ListBox ?? (UIElement)completionList;
        }

        /// <summary>
        /// Gets/Sets whether the completion window should close automatically.
        /// The default value is true.
        /// </summary>
        public bool CloseAutomatically { get; set; }

        /// <inheritdoc/>
        protected override bool CloseOnFocusLost
        {
            get { return this.CloseAutomatically; }
        }

        /// <summary>
        /// When this flag is set, code completion closes if the caret moves to the
        /// beginning of the allowed range. This is useful in Ctrl+Space and "complete when typing",
        /// but not in dot-completion.
        /// Has no effect if CloseAutomatically is false.
        /// </summary>
        public bool CloseWhenCaretAtBeginning { get; set; }

        void CaretPositionChanged(object sender, EventArgs e)
        {
            int offset = this.TextArea.Caret.Offset;
            if (offset == this.StartOffset)
            {
                if (CloseAutomatically && CloseWhenCaretAtBeginning)
                {
                    Close();
                }
                else
                {
                    completionList.SelectItem(string.Empty);
                }
                return;
            }
            if (offset < this.StartOffset || offset > this.EndOffset)
            {
                if (CloseAutomatically)
                {
                    Close();
                }
            }
            else
            {
                TextDocument document = this.TextArea.Document;
                if (document != null)
                {
                    completionList.SelectItem(document.GetText(this.StartOffset, offset - this.StartOffset));
                }
            }
        }
    }
}
