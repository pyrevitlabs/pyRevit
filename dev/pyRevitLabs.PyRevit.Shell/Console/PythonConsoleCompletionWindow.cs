// Copyright (c) 2010 Joe Moorhouse

using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Input;
using System.Windows.Media;
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
            this.completionDataProvider = textEditor.CompletionProvider;
            this.textEditor = textEditor;
            this.CloseAutomatically = true;
            this.SizeToContent = SizeToContent.Height;
            this.MaxHeight = 300;
            this.Width = 175;
            this.Content = completionList;
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

        /// <summary>
        /// Applies dark-theme colors to the completion list and description tooltip.
        /// </summary>
        public void ApplyTheme(bool useDarkTheme)
        {
            if (!useDarkTheme)
                return;

            var background = new SolidColorBrush(Color.FromRgb(0x25, 0x25, 0x26));
            var foreground = new SolidColorBrush(Color.FromRgb(0xD4, 0xD4, 0xD4));
            var border = new SolidColorBrush(Color.FromRgb(0x3F, 0x3F, 0x46));
            var selection = new SolidColorBrush(Color.FromRgb(0x09, 0x4A, 0x77));

            this.Background = background;
            this.Foreground = foreground;
            this.BorderBrush = border;

            completionList.Background = background;
            completionList.Foreground = foreground;

            // The list's ListBox is created when the CompletionList template is applied, which may
            // not have happened yet; style it now if present, otherwise once it loads.
            if (completionList.ListBox != null)
                StyleListBox(completionList.ListBox, background, foreground, border, selection);
            else
                completionList.Loaded += (s, e) =>
                {
                    if (completionList.ListBox != null)
                        StyleListBox(completionList.ListBox, background, foreground, border, selection);
                };

            toolTip.Background = background;
            toolTip.Foreground = foreground;
            toolTip.BorderBrush = border;
        }

        static void StyleListBox(ListBox listBox, Brush background, Brush foreground, Brush border, Brush selection)
        {
            listBox.Background = background;
            listBox.Foreground = foreground;
            listBox.BorderBrush = border;
            // Override the system selection brushes so the highlighted item stays readable on a
            // dark background instead of using the default light-blue selection.
            listBox.Resources[SystemColors.HighlightBrushKey] = selection;
            listBox.Resources[SystemColors.HighlightTextBrushKey] = foreground;
            listBox.Resources[SystemColors.InactiveSelectionHighlightBrushKey] = selection;
            listBox.Resources[SystemColors.InactiveSelectionHighlightTextBrushKey] = foreground;
        }

        #region ToolTip handling
        void toolTip_Closed(object sender, RoutedEventArgs e)
        {
            // Clearing earlier interrupts the tooltip's close animation.
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
            // Close first so completion-installed input handlers remain on the stack.
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
