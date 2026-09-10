using System;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using PyRevitLabs.UI.Client;
using PyRevitLabs.UI.Protocol;
using pyRevitLabs.Emojis;

namespace PyRevitLabs.PyRevit.Runtime {
    public partial class ScriptConsole {
        private readonly bool _isolatedUi = UiHostClientContext.IsEnabled;
        private bool _isolatedWindowCreated;
        private bool _isolatedVisible;
        private bool _isolatedRegistered;
        private string _isolatedInitialHtml = string.Empty;
        private readonly StringBuilder _isolatedFrozenHtml = new StringBuilder();
        private double _isolatedWidth = 900;
        private double _isolatedHeight = 600;
        private double _isolatedLeft = 100;
        private double _isolatedTop = 100;

        private static UiOutputClient IsolatedOutput => UiHostClientContext.Output;
        private static void Wait(Task task) => task.GetAwaiter().GetResult();
        private static T Wait<T>(Task<T> task) => task.GetAwaiter().GetResult();

        public bool IsIsolatedUi => _isolatedUi;
        public bool IsOutputVisible => _isolatedUi ? _isolatedVisible : IsVisible;

        private bool InitializeIsolatedComponent() {
            if (!_isolatedUi)
                return false;

            Width = _isolatedWidth;
            Height = _isolatedHeight;
            MinWidth = 700;
            MinHeight = TitleBarHeight;
            ShowInTaskbar = false;
            if (!UiHostClientContext.IsAvailable)
                throw new InvalidOperationException("Isolated UI is enabled but the UI host is not available.");
            UiHostClientContext.EventReceived += IsolatedUiEventReceived;
            SetupDefaultPage();
            return true;
        }
        private void EnsureIsolatedWindow() {
            if (!_isolatedUi || _isolatedWindowCreated)
                return;

            Wait(IsolatedOutput.CreateWindowAsync(
                OutputUniqueId,
                OutputTitle,
                _isolatedInitialHtml,
                _isolatedWidth,
                _isolatedHeight,
                _isolatedLeft,
                _isolatedTop));
            _isolatedWindowCreated = true;
            _isolatedVisible = true;
            RegisterIsolatedWindow();
        }

        private void RegisterIsolatedWindow() {
            if (_isolatedRegistered)
                return;
            ScriptConsoleManager.AppendToOutputWindowList(this);
            _isolatedRegistered = true;
            ApplyCloseOthersConfig();
        }

        private void UnregisterIsolatedWindow() {
            if (!_isolatedRegistered)
                return;
            ScriptConsoleManager.RemoveFromOutputList(this);
            _isolatedRegistered = false;
        }

        public void ShowOutput() {
            if (!_isolatedUi) {
                Show();
                return;
            }
            EnsureIsolatedWindow();
            Wait(IsolatedOutput.SetVisibilityAsync(OutputUniqueId, true));
            _isolatedVisible = true;
        }
        public void HideOutput() {
            if (!_isolatedUi) {
                Hide();
                return;
            }
            if (!_isolatedWindowCreated)
                return;
            Wait(IsolatedOutput.SetVisibilityAsync(OutputUniqueId, false));
            _isolatedVisible = false;
        }

        public new void Close() {
            CloseOutput();
        }

        public void CloseOutput() {
            if (!_isolatedUi) {
                base.Close();
                return;
            }
            if (_isolatedWindowCreated) {
                try {
                    Wait(IsolatedOutput.CloseAsync(OutputUniqueId));
                }
                catch {
                }
            }
            _isolatedWindowCreated = false;
            _isolatedVisible = false;
            ClosedByUser = true;
            UnregisterIsolatedWindow();
            UiHostClientContext.EventReceived -= IsolatedUiEventReceived;
        }

        private void IsolatedUiEventReceived(object sender, UiHostEventArgs e) {
            if (!_isolatedUi || e.WindowId != OutputUniqueId)
                return;

            Dispatcher.BeginInvoke(new Action(() => {
                if (e.Method == UiMethods.Output.Closed) {
                    _isolatedWindowCreated = false;
                    _isolatedVisible = false;
                    ClosedByUser = true;
                    UnregisterIsolatedWindow();
                }
                else if (e.Method == UiMethods.Output.Navigate && !string.IsNullOrEmpty(e.Value)) {
                    ScriptConsoleUtils.ProcessUrl(_uiApp, e.Value, this);
                }
            }));
        }
        private void SetupIsolatedDefaultPage(string styleSheetFilePath) {
            var dochead = string.Format(
                ScriptConsoleConfigs.DOCTYPE + ScriptConsoleConfigs.DOCHead,
                AppVersion,
                "WebView2",
                styleSheetFilePath);
            _isolatedInitialHtml = string.Format("{0}<html><body></body></html>", dochead);
        }

        private string ComposeEntryHtml(string contents, string htmlElementType) {
            contents = ScriptConsoleConfigs.EscapeForHtml(contents);
            contents = ScriptConsoleConfigs.FromCustomHtmlTags(contents);
            contents = ScriptConsoleConfigs.EscapeForOutput(contents);
            contents = Emojis.Emojize(contents);
            return string.Format("<{0}>{1}</{0}>", htmlElementType, contents);
        }

        private void AppendIsolatedText(string outputText, string htmlElementType, bool record) {
            if (record)
                _lastLine = outputText;
            var html = ComposeEntryHtml(outputText, htmlElementType);
            if (_frozen) {
                _isolatedFrozenHtml.Append(html);
                return;
            }
            EnsureIsolatedWindow();
            Wait(IsolatedOutput.AppendHtmlAsync(OutputUniqueId, html));
        }

        private string GetIsolatedHtml() {
            if (!_isolatedWindowCreated)
                return _isolatedInitialHtml;
            return Wait(IsolatedOutput.GetHtmlAsync(OutputUniqueId));
        }
        public void SetOutputSize(double width, double height) {
            if (!_isolatedUi) {
                Width = width;
                Height = height;
                return;
            }
            if (width > 0) _isolatedWidth = width;
            if (height > 0) _isolatedHeight = height;
            if (_isolatedWindowCreated)
                Wait(IsolatedOutput.SetBoundsAsync(
                    OutputUniqueId, _isolatedWidth, _isolatedHeight, _isolatedLeft, _isolatedTop));
        }

        public double GetOutputWidth() => _isolatedUi ? _isolatedWidth : Width;
        public double GetOutputHeight() => _isolatedUi ? _isolatedHeight : Height;

        public void CenterOutput() {
            if (!_isolatedUi) {
                var workArea = SystemParameters.WorkArea;
                Left = workArea.Left + ((workArea.Width - Width) / 2);
                Top = workArea.Top + ((workArea.Height - Height) / 2);
                return;
            }
            var area = SystemParameters.WorkArea;
            _isolatedLeft = area.Left + ((area.Width - _isolatedWidth) / 2);
            _isolatedTop = area.Top + ((area.Height - _isolatedHeight) / 2);
            if (_isolatedWindowCreated)
                Wait(IsolatedOutput.SetBoundsAsync(
                    OutputUniqueId, _isolatedWidth, _isolatedHeight, _isolatedLeft, _isolatedTop));
        }

        public void NavigateOutput(string url) {
            if (!_isolatedUi) {
                renderer?.Navigate(url, false);
                return;
            }
            EnsureIsolatedWindow();
            Wait(IsolatedOutput.NavigateAsync(OutputUniqueId, url));
        }

        private string ReadIsolatedInput() {
            EnsureIsolatedWindow();
            var lastLine = GetLastLine().ToLowerInvariant();
            var mode = lastLine.Contains("select") && lastLine.Contains("file") ? "file" : "text";
            return Wait(IsolatedOutput.ReadInputAsync(OutputUniqueId, mode));
        }
    }
}
