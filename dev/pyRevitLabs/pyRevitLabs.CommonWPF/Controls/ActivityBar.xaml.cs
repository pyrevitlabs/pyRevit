using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;

namespace pyRevitLabs.CommonWPF.Controls {
    /// <summary>
    /// Interaction logic for ActivityBar.xaml
    /// </summary>
    public partial class ActivityBar : UserControl {
        private bool _isExpanded = false;
        private bool _manualActive = false;
        private uint _taskCounter = 0;

        public ActivityBar() {
            InitializeComponent();

            // set console to compressed line height
            console.UpdateLayout();
            Paragraph p = console.Document.Blocks.FirstBlock as Paragraph;
            p.LineHeight = 1;
        }

        public void ConsoleClear() => console.Document.Blocks.Clear();

        public void ClearErrors() {
            indicateStuff.Visibility = Visibility.Collapsed;
            indicateMessage.Text = "";
            progressBarGrid.Height = 8;
        }

        public void IndicateMessage(string logEntry, SolidColorBrush brush) {
            if (!_isExpanded) {
                indicateStuff.Visibility = Visibility.Visible;
                indicateBlock.Fill = brush;
                logEntry = logEntry.Replace(Environment.NewLine, "\n");
                try {
                    indicateMessage.Text = logEntry.Substring(0, logEntry.IndexOf("\n"));
                }
                catch {
                    indicateMessage.Text = logEntry;
                }
                progressBarGrid.Height = 20;
            }
        }

        private void _consoleLog(string logEntry, SolidColorBrush indicate = null) {
            if (indicate != null) {
                TextRange tr = new TextRange(console.Document.ContentEnd, console.Document.ContentEnd);
                tr.Text = logEntry + "\n";
                tr.ApplyPropertyValue(TextElement.ForegroundProperty, indicate);
                IndicateMessage(logEntry, indicate);
            }
            else {
                console.AppendText(logEntry + "\n");
            }

            console.ScrollToEnd();
        }

        public void ConsoleLog(string logEntry) { _consoleLog(logEntry); }

        public void ConsoleLogOK(string logEntry) { _consoleLog(logEntry, indicate: Brushes.Green); }

        public void ConsoleLogInfo(string logEntry) { _consoleLog(logEntry, indicate: Brushes.Transparent); }

        public void ConsoleLogError(string logEntry) { _consoleLog(logEntry, indicate: Brushes.Red); }

        public void ConsoleLogWarning(string logEntry) { _consoleLog(logEntry, indicate: Brushes.Orange); }

        public bool IsActive {
            get {
                return _taskCounter > 0 || _manualActive;
            }
            set {
                _manualActive = (bool)value;
                RefreshProgressState();
            }
        }

        public void RefreshProgressState() {
            // set the warning and error blocks to transparent so the 
            // indeterminate progress bar is visible through
            if (IsActive) {
                taskProgress.IsIndeterminate = true;
                indicateStuff.Opacity = 0.5;
            }
            else {
                taskProgress.IsIndeterminate = false;
                indicateStuff.Opacity = 1.0;
            }
        }

        public void UpdateProgressBar(float curValue, float maxValue) {
            taskProgress.IsIndeterminate = false;
            taskProgress.Maximum = maxValue;
            taskProgress.Value = curValue;
        }

        public void ResetProgressBar() {
            taskProgress.IsIndeterminate = false;
            taskProgress.Maximum = 0;
            taskProgress.Value = 0;
        }

        public async Task<TResult> RunTask<TResult>(string taskName, Func<TResult> function) {
            _taskCounter++;
            RefreshProgressState();

            //ConsoleLog(String.Format("☐ {0} Task Started.", taskName));
            var task = await Task<TResult>.Run(function);

            _taskCounter--;
            RefreshProgressState();

            ConsoleLog(String.Format("✓ {0} Task Completed.", taskName));
            return task;
        }

        public async Task RunTask(string taskName, Action function) {
            _taskCounter++;
            RefreshProgressState();

            //ConsoleLog(String.Format("☐ {0} Task Started.", taskName));
            await Task.Run(function);

            _taskCounter--;
            RefreshProgressState();

            ConsoleLog(String.Format("✓ {0} Task Completed.", taskName));
        }

        private void actionBar_Click(object sender, MouseButtonEventArgs e) {
            if (hiddenPanel.Visibility == Visibility.Visible) {
                hiddenPanel.Visibility = Visibility.Collapsed;
                _isExpanded = false;
            }
            else {
                hiddenPanel.Visibility = Visibility.Visible;
                _isExpanded = true;
            }

            console.UpdateLayout();
            console.ScrollToEnd();
            ClearErrors();
        }

        private void clearConsoleButton_Click(object sender, RoutedEventArgs e) => ConsoleClear();

        private void copyConsoleButton_Click(object sender, RoutedEventArgs e) {
            console.SelectAll();
            console.Copy();
        }

        private void clearErrorsConsoleButton_Click(object sender, RoutedEventArgs e) => ClearErrors();

        private void closeButton_Click(object sender, RoutedEventArgs e) => actionBar_Click(null, null);
    }
}
