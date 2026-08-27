using System;
using System.Windows;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Text;
using System.Windows.Controls;
using System.Windows.Markup;
using System.Windows.Media;
using System.Windows.Threading;
using Autodesk.Revit.UI;
using Microsoft.Web.WebView2.Core;
using System.Text.RegularExpressions;
using System.Diagnostics;

using pyRevitLabs.Common;
using pyRevitLabs.CommonWPF.Controls;
using pyRevitLabs.Emojis;
using pyRevitLabs.PyRevit;

namespace PyRevitLabs.PyRevit.Runtime {
    public struct ScriptConsoleDebugger {
        public string Name;
        public Regex PromptFinder;
        public string DebugContinueKey;
        public string DebugStepOverKey;
        public string DebugStepInKey;
        public string DebugStepOutKey;
        public string DebugStopKey;
        public List<Tuple<Regex, string>> StopFinders;
    }

    public static class ScriptConsoleConfigs {
        public static string DOCTYPE = "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.01 Transitional//EN\" \"http://www.w3.org/TR/html4/loose.dtd\">";
        public static string DOCHead = "<head>" +
                                       "<meta http-equiv=\"content-type\" content=\"text/html; charset=utf-8\" />" +
                                       "<meta name=\"appversion\" content=\"{0}\" />" +
                                       "<meta name=\"rendererversion\" content=\"{1}\" />" +
                                       "<link rel=\"stylesheet\" href=\"{2}\">" +
                                       "</head>";
        public static string DefaultBlock = "<div class=\"entry\"></div>";
        public static string ErrorBlock = "<div class=\"errorentry\"></div>";
        public static string IPYErrorHeader = "<strong>IronPython Traceback:</strong>";
        public static string CPYErrorHeader = "<strong>CPython Traceback:</strong>";
        public static string IRubyErrorHeader = "<strong>IronRuby Traceback:</strong>";
        public static string CLRErrorHeader = "<strong>Script Executor Traceback:</strong>";
        public static string CSharpErrorHeader = "<strong>C# Traceback:</strong>";
        public static string VBErrorHeader = "<strong>VB.NET Traceback:</strong>";
        public static string ProgressBlockId = "pbarcontainer";
        public static string ProgressBarId = "pbar";
        public static string InlineWaitBlockId = "inlnwait";
        public static List<string> InlineWaitSequence = new List<string>(){
            "\u280b Preparing results...",
            "\u2819 Preparing results...",
            "\u2838 Preparing results...",
            "\u28B0 Preparing results...",
            "\u28e0 Preparing results...",
            "\u28c4 Preparing results...",
            "\u2846 Preparing results...",
            "\u2807 Preparing results..."
        };

        public static string ToCustomHtmlTags(string source) {
            return source.Replace("<", "&clt;").Replace(">", "&cgt;");
        }

        public static string FromCustomHtmlTags(string source) {
            return source.Replace("&clt;", "<").Replace("&cgt;", ">");
        }

        public static string EscapeForHtml(string source) {
            return source.Replace("<", "&lt;").Replace(">", "&gt;");
        }

        public static string UnscapeFromHtml(string source) {
            return source.Replace("&lt;", "<").Replace("&gt;", ">");
        }

        public static string EscapeForOutput(string source) {
            // remove end new line
            if (source.EndsWith("\n"))
                source = source.Remove(source.Length - 1);
            return source.Replace("\n", "<br/>").Replace("\t", "&emsp;&emsp;");
        }
    }

    public partial class ScriptConsoleTemplate : pyRevitLabs.CommonWPF.Windows.AppWindow {
        public ScriptConsoleTemplate() {
            // setup window styles
            SetupDynamicResources();
            EnablePyRevitTemplateWindowStyle();
        }

        public void EnablePyRevitTemplateWindowStyle() {
            SizeChanged += ScriptOutput_SizeChanged;

            // setup template styles
            Background = Brushes.White;
            var glowColor = Color.FromArgb(0x66, 0x2c, 0x3e, 0x50);
            // activating glow on the window causes an exception in PresentationFramework on Revit 2019
            // when closing Revit with pyRevit windows open.
            //GlowBrush = new SolidColorBrush() { Color = glowColor };
            //NonActiveGlowBrush = new SolidColorBrush() { Color = glowColor };

            ResetIcon();

            //ResizeBorderThickness = new Thickness(10);
            // added thickness after disabling glow brush due to a bug
            BorderThickness = new Thickness(1);
            WindowStartupLocation = WindowStartupLocation.Manual;
            WindowTransitionsEnabled = false;
            SaveWindowPosition = false;
        }

        private void SetupDynamicResources() {
            Resources.MergedDictionaries.Add(new ResourceDictionary() {
                Source = new Uri("pack://application:,,,/pyRevitLabs.MahAppsMetro;component/Styles/Controls.xaml")
            });

            Resources.MergedDictionaries.Add(new ResourceDictionary() {
                Source = new Uri("pack://application:,,,/pyRevitLabs.MahAppsMetro;component/Styles/Fonts.xaml")
            });

            Resources.MergedDictionaries.Add(new ResourceDictionary() {
                Source = new Uri("pack://application:,,,/pyRevitLabs.MahAppsMetro;component/Styles/Themes/Light.Blue.xaml")
            });

            var accentResDict = Resources;

            var pyrevitHighlightColor = Color.FromArgb(0xFF, 0xf3, 0x9c, 0x12);
            var pyrevitBackground = new SolidColorBrush() { Color = Color.FromArgb(0xFF, 0x2c, 0x3e, 0x50) };
            var pyrevitHighlight = new SolidColorBrush() { Color = pyrevitHighlightColor };
            accentResDict["MahApps.Brushes.Accent"] = pyrevitBackground;
            accentResDict["MahApps.Brushes.WindowTitle"] = pyrevitBackground;

            // overriding colors on the progressbar control
            var progressBarOverlay = Color.FromArgb(0x66, 0xFF, 0xFF, 0xFF);
            accentResDict["MahApps.Brushes.Progress"] = pyrevitHighlight;
            accentResDict["MahApps.Colors.ProgressIndeterminate1"] = progressBarOverlay;
            accentResDict["MahApps.Colors.ProgressIndeterminate2"] = progressBarOverlay;
            accentResDict["MahApps.Colors.ProgressIndeterminate3"] = pyrevitHighlightColor;
            accentResDict["MahApps.Colors.ProgressIndeterminate4"] = pyrevitHighlightColor;
        }

        private void ScriptOutput_SizeChanged(object sender, SizeChangedEventArgs e) {
            Visibility isVisible = Visibility.Visible;
            if (ActualWidth < 400)
                isVisible = Visibility.Collapsed;
            foreach (Button item in RightWindowCommands.Items)
                item.Visibility = isVisible;

            this.TitleForeground = isVisible == Visibility.Visible ? Brushes.White : new SolidColorBrush() { Color = Color.FromArgb(0xFF, 0x2c, 0x3e, 0x50) };
        }

        public void ResetIcon() {
            var iconPath = Path.Combine(
                Path.GetDirectoryName(typeof(ActivityBar).Assembly.Location),
                "pyrevit_outputwindow.png"
                );
            SetIcon(iconPath);
        }
    }

    /// <summary>
    /// Output window hosting a Chromium (WebView2) renderer. Content mutations
    /// are buffered and flushed to the browser in order; DOM reads and other
    /// synchronous operations block via nested message pumps so engine worker
    /// threads can use this window directly.
    /// </summary>
    public partial class ScriptConsole : ScriptConsoleTemplate, IComponentConnector, IDisposable {
        private bool _contentLoaded;
        private bool _debugMode;
        private volatile bool _frozen = false;

        // Guards against re-entrant render pumping. All output windows share the
        // main UI thread dispatcher, so a synchronous render pump triggered by one
        // window can run another window's queued render and recurse until the stack
        // overflows. Skipping a re-entrant call breaks that chain.
        [ThreadStatic]
        private static bool _renderingFrame;
        private string _lastLine = string.Empty;
        private DispatcherTimer _animationTimer;
        private UIApplication _uiApp;
        private ScriptConsoleLowLevelKeyHook _keyHook;

        private readonly ScriptWebView _webView;
        private readonly object _pendingLock = new object();
        private readonly StringBuilder _pendingHtml = new StringBuilder();
        private readonly StringBuilder _frozenPendingHtml = new StringBuilder();
        private volatile bool _flushQueued;
        private volatile bool _documentStarted;
        private volatile bool _outputLossReported;
        private string _frozenBodyHtml;
        private int _inlineWaitIndex = -1;
        private string _initialStyleSheetPath;
        private string _outputHtmlPath;

        private List<ScriptConsoleDebugger> _supportedDebuggers =
            new List<ScriptConsoleDebugger> {
                new ScriptConsoleDebugger() {
                    Name = "Pdb (IronPython|CPython)",
                    PromptFinder = new Regex(@"\(pdb\)"),
                    DebugContinueKey = "c",
                    DebugStepOverKey = "n",
                    DebugStepInKey = "s",
                    DebugStepOutKey = "r",
                    DebugStopKey = "q",
                    StopFinders = new List<Tuple<Regex, string>> {
                        new Tuple<Regex, string> (
                            new Regex(@"bdb.BdbQuit|BdbQuit :"),
                            "Debugger stopped (bdb.BdbQuit exception)"
                        ),
                        new Tuple<Regex, string> (
                            new Regex(@"pdb.Restart|Restart :"),
                            "Debugger stopped. Restart by running the script again (pdb.Restart exception)"
                        )
                    }
                }
        };

        // JS is assembled by concatenation, never string.Format: the snippets
        // are full of literal braces that the composite-format parser rejects.
        private static string BuildInsertEntriesJs(string payloadJson) {
            return "(function(h){var d=document.body;if(!d)return;"
                 + "var nb=d.scrollHeight<=window.innerHeight||window.innerHeight+window.scrollY>=d.scrollHeight-50;"
                 + "d.insertAdjacentHTML('beforeend',h);"
                 + "if(nb)window.scrollTo(0,d.scrollHeight);})(" + payloadJson + ");";
        }

        private static string BuildSetElementDisplayJs(string idJson, string displayJsLiteral) {
            return "(function(id,v){var e=document.getElementById(id);if(e)e.style.display=v;})("
                 + idJson + "," + displayJsLiteral + ");";
        }

        private static string BuildUpdateProgressJs(string widthJson) {
            return "(function(w){"
                 + "var c=document.getElementById('pbarcontainer');"
                 + "if(!c){c=document.createElement('div');c.id='pbarcontainer';c.className='progressindicator';"
                 + "var b=document.createElement('div');b.id='pbar';b.className='progressbar';"
                 + "c.appendChild(b);document.body.appendChild(c);}"
                 + "var p=document.getElementById('pbar');"
                 + "if(p)p.style.width=w;})(" + widthJson + ");";
        }

        private static string BuildInlineWaitJs(string textJson) {
            return "(function(t){var w=document.getElementById('inlnwait');"
                 + "if(!w){w=document.createElement('div');w.id='inlnwait';w.className='inlinewait';"
                 + "document.body.appendChild(w);}"
                 + "w.textContent=t;window.scrollTo(0,document.body.scrollHeight);})(" + textJson + ");";
        }

        private static string BuildInjectHtmlJs(string htmlJson, string targetJson) {
            return "(function(h,target){(target==='head'?document.head:document.body)"
                 + ".insertAdjacentHTML('beforeend',h);})(" + htmlJson + "," + targetJson + ");";
        }

        // Scripts injected through innerHTML never execute in Chromium, so script
        // tags are built with createElement and appended for real execution.
        private static string BuildInjectScriptElementJs(string codeJson, string attrsJson, string targetJson) {
            return "(function(code,attrs,target){var s=document.createElement('script');"
                 + "for(var k in attrs)s.setAttribute(k,attrs[k]);"
                 + "s.textContent=code;(target==='head'?document.head:document.body).appendChild(s);})("
                 + codeJson + "," + attrsJson + "," + targetJson + ");";
        }

        // OutputUniqueId is set in constructor
        // OutputUniqueId is unique for every output window
        public string OutputUniqueId;

        // OutputId is set by the requesting pyRevit command
        // OutputId is the same for all output windows that belong to a single pyRevit command
        public string OutputId;

        // to track if user manually closed the window
        public bool ClosedByUser = false;

        // marks the session-loader output window so that "close other outputs"
        // config does not kill it when a startup script opens its own output.
        public bool IsSessionOutput = false;

        // is window collapsed?
        private double prevHeight = 0;
        public bool IsCollapsed = false;
        public bool IsAutoCollapseActive = false;
        // is window expanded?
        public bool IsExpanded = false;

        // Chromium renderer (WebView2) and its activity/stdin companions
        public ActivityBar activityBar;
        public InputBar stdinBar;

        public ScriptConsole(bool debugMode = false, UIApplication uiApp = null) : base() {
            _debugMode = debugMode;
            _uiApp = uiApp;

            // setup unique id for this output window
            OutputUniqueId = Guid.NewGuid().ToString();

            _webView = new ScriptWebView(Dispatcher.CurrentDispatcher);
            _webView.NavigationStartingRequested += WebView_NavigationStarting;
            _webView.DocumentReady += WebView_DocumentReady;

            InitializeComponent();
        }

        [System.Diagnostics.DebuggerNonUserCodeAttribute()]
        [System.CodeDom.Compiler.GeneratedCodeAttribute("PresentationBuildTasks", "4.0.0.0")]
        public void InitializeComponent() {
            if (_contentLoaded) {
                return;
            }
            _contentLoaded = true;

            this.Loaded += Window_Loaded;
            this.Closing += Window_Closing;
            this.Closed += Window_Closed;

            // record the active stylesheet; the initial page is written and
            // loaded lazily on first renderer use
            SetupDefaultPage();

            #region Window Layout

            Grid baseGrid = new Grid();
            baseGrid.Margin = new Thickness(0, 0, 0, 0);

            // activiy bar
            var activityBarRow = new RowDefinition();
            activityBarRow.Height = GridLength.Auto;
            baseGrid.RowDefinitions.Add(activityBarRow);
            activityBar = new ActivityBar();
            activityBar.Foreground = Brushes.White;
            activityBar.Visibility = Visibility.Collapsed;
            Grid.SetRow(activityBar, 0);

            // Add the WebView2 renderer to the Grid
            var rendererRow = new RowDefinition();
            baseGrid.RowDefinitions.Add(rendererRow);
            Grid.SetRow(_webView.Control, 1);

            // standard input bar
            var stdinRow = new RowDefinition();
            stdinRow.Height = GridLength.Auto;
            baseGrid.RowDefinitions.Add(stdinRow);
            stdinBar = new InputBar();
            stdinBar.Visibility = Visibility.Collapsed;
            Grid.SetRow(stdinBar, 2);

            // set activity bar and renderer
            baseGrid.Children.Add(activityBar);
            baseGrid.Children.Add(_webView.Control);
            baseGrid.Children.Add(stdinBar);
            this.Content = baseGrid;

            #endregion

            #region Titlebar Buttons
            // resize buttons
            var expandToggleButton = new Button() { ToolTip = "Expand/Shrink Window", Focusable = false };
            expandToggleButton.Width = 32;
            expandToggleButton.Content = GetExpandToggleIcon(IsExpanded);
            expandToggleButton.Click += ExpandToggleButton_Click; ;
            LeftWindowCommands.Items.Insert(0, expandToggleButton);

            // TODO: add report button, get email from envvars
            var pinButton = new Button() { ToolTip = "Keep On Top", Focusable = false };
            pinButton.Width = 32;
            pinButton.Content = GetPinIcon(Topmost);
            pinButton.Click += PinButton_Click;
            RightWindowCommands.Items.Insert(0, pinButton);

            var copyButton = new Button() { ToolTip = "Copy All Text", Focusable = false };
            copyButton.Width = 32;
            copyButton.Content =
                MakeButtonPath("M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z");
            copyButton.Click += CopyButton_Click;
            RightWindowCommands.Items.Insert(0, copyButton);

            var saveButton = new Button() { ToolTip = "Save Contents", Focusable = false };
            saveButton.Width = 32;
            saveButton.Content =
                MakeButtonPath("M15,9H5V5H15M12,19A3,3 0 0,1 9,16A3,3 0 0,1 12,13A3,3 0 0,1 15,16A3,3 0 0,1 12,19M17,3H5C3.89,3 3,3.9 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V7L17,3Z");
            saveButton.Click += Save_Contents_Button_Clicked;
            RightWindowCommands.Items.Insert(0, saveButton);

            var printButton = new Button() { ToolTip = "Print Contents", Focusable = false };
            printButton.Width = 32;
            printButton.Content =
                MakeButtonPath("M18,3H6V7H18M19,12A1,1 0 0,1 18,11A1,1 0 0,1 19,10A1,1 0 0,1 20,11A1,1 0 0,1 19,12M16,19H8V14H16M19,8H5A3,3 0 0,0 2,11V17H6V21H18V17H22V11A3,3 0 0,0 19,8Z");
            printButton.Click += PrintButton_Click; ;
            RightWindowCommands.Items.Insert(0, printButton);

            var openButton = new Button() { ToolTip = "Open in Browser", Focusable = false };
            openButton.Width = 32;
            openButton.Content =
                MakeButtonPath("M14,3V5H17.59L7.76,14.83L9.17,16.24L19,6.41V10H21V3M19,19H5V5H12V3H5C3.89,3 3,3.89 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V12H19V19Z");
            openButton.Click += OpenButton_Click;
            RightWindowCommands.Items.Insert(0, openButton);

            #endregion

            this.Width = 900; this.MinWidth = 700;
            this.Height = 600; this.MinHeight = this.TitleBarHeight;
            this.ResizeMode = ResizeMode.CanResize;

            // setup auto-collapse
            this.Activated += ScriptOutput_GotFocus;
            this.Deactivated += ScriptOutput_LostFocus;

            this.OutputTitle = PyRevitLabsConsts.ProductName;
        }

        [System.Diagnostics.DebuggerNonUserCodeAttribute()]
        [System.CodeDom.Compiler.GeneratedCodeAttribute("PresentationBuildTasks", "4.0.0.0")]
        [System.ComponentModel.EditorBrowsableAttribute(System.ComponentModel.EditorBrowsableState.Never)]
        [System.Diagnostics.CodeAnalysis.SuppressMessageAttribute("Microsoft.Design", "CA1033:InterfaceMethodsShouldBeCallableByChildTypes")]
        [System.Diagnostics.CodeAnalysis.SuppressMessageAttribute("Microsoft.Maintainability", "CA1502:AvoidExcessiveComplexity")]
        [System.Diagnostics.CodeAnalysis.SuppressMessageAttribute("Microsoft.Performance", "CA1800:DoNotCastUnnecessarily")]
        void System.Windows.Markup.IComponentConnector.Connect(int connectionId, object target) {
            this._contentLoaded = true;
        }

        /// <summary>
        /// Chromium runtime version of the renderer. Initializes the renderer
        /// when necessary; 0.0 only if initialization is unavailable.
        /// </summary>
        public Version RendererVersion {
            get {
                EnsureDocumentReadyBlocking();
                return Version.TryParse(_webView.BrowserVersion.Split(' ')[0], out var parsed)
                    ? parsed
                    : new Version(0, 0);
            }
        }

        /// <summary>Engine identity of the renderer, e.g. "WebView2/Chromium".</summary>
        public string RendererEngine {
            get { return _webView.RuntimeMissing ? "WebView2 (runtime missing)" : "WebView2/Chromium"; }
        }

        /// <summary>
        /// Full renderer runtime version, e.g. "151.0.4129.107". Initializes
        /// the renderer when necessary; empty only if unavailable.
        /// </summary>
        public string RendererFullVersion {
            get {
                EnsureDocumentReadyBlocking();
                return _webView.BrowserVersion;
            }
        }

        /// <summary>
        /// Evaluate JavaScript in the current output document and return the
        /// result: JSON string results are returned decoded, any other result
        /// (number, boolean, object) is returned as its raw JSON text.
        /// </summary>
        public string RunJavaScript(string javaScript) {
            if (string.IsNullOrEmpty(javaScript))
                return string.Empty;
            EnsureDocumentReadyBlocking();
            var result = _webView.EvalScript(javaScript);
            return DecodeJsonString(result) ?? result;
        }

        private string GetStyleSheetFile() {
            var env = new EnvDictionary();
            return env.ActiveStyleSheet;
        }

        /// <summary>Full current document including the html wrapper.</summary>
        public string GetFullHtml() {
            EnsureDocumentReadyBlocking();
            var html = DecodeJsonString(_webView.EvalScript("document.documentElement.outerHTML"));
            return ScriptConsoleConfigs.DOCTYPE + (html ?? string.Empty);
        }

        internal string GetHeadHtml() {
            EnsureDocumentReadyBlocking();
            return DecodeJsonString(_webView.EvalScript("(document.head ? document.head.innerHTML : '')"))
                ?? string.Empty;
        }

        /// <summary>Navigate the renderer to an absolute url, replacing current content.</summary>
        internal void NavigateInWindow(string url) {
            if (string.IsNullOrEmpty(url))
                return;
            EnsureDocumentReadyBlocking();
            _webView.Navigate(url);
        }

        /// <summary>
        /// Apply output font preferences as a CSS override. Replaces the legacy
        /// WebBrowser control Font property; affects body-level defaults only.
        /// </summary>
        internal void SetFont(string fontFamily, float fontSize) {
            var family = (fontFamily ?? string.Empty).Trim().Replace("'", "\\'");
            var css = string.Format(
                System.Globalization.CultureInfo.InvariantCulture,
                "body {{ font-family: '{0}' !important; font-size: {1}pt !important; }}",
                string.IsNullOrEmpty(family) ? "inherit" : family,
                fontSize > 0 ? fontSize : 10f);
            InjectHtmlElement("head", "style", css, null);
        }

        private void ApplyCloseOthersConfig()
        {
            if (PyRevitConfigs.GetCloseOtherOutputs())
            {
                var mode = PyRevitConfigs.GetCloseOutputMode();
                this.Dispatcher.BeginInvoke(new Action(() =>
                {
                    CloseOtherOutputs(filterByCommandId: mode == OutputCloseMode.CurrentCommand);
                }));
            }
        }

        public void CloseOtherOutputs(bool filterByCommandId = true) {
            try {
                var filterId = filterByCommandId ? this.OutputId : null;
                ScriptConsoleManager.CloseActiveOutputWindows(excludeOutputWindow: this, filterOutputWindowId: filterId);
            }
            catch {
            }
        }

        /// <summary>
        /// Record the stylesheet for this window and reset the document if one
        /// is already loaded. The initial page materializes lazily on first
        /// renderer interaction.
        /// </summary>
        public void SetupDefaultPage(string styleSheetFilePath = null) {
            _initialStyleSheetPath = styleSheetFilePath ?? GetStyleSheetFile();
            if (_documentStarted && _webView.Control.CoreWebView2 != null) {
                SyncFlushBlocking();
                _webView.Navigate(WriteInitialPageFile());
            }
        }

        public void WaitReadyBrowser() {
            EnsureDocumentReadyBlocking();
        }

        /// <summary>Start the renderer without waiting; safe from the print path.</summary>
        internal void WaitReadyBrowserLite() {
            EnsureDocumentReady();
        }

        /// <summary>
        /// Bring the WebView2 core online and load the initial page, blocking
        /// until the document is interactive. Safe from any thread.
        /// </summary>
        internal void EnsureDocumentReady() {
            if (ClosedByUser)
                return;
            // The WebView2 controller can only be created once the window has
            // been shown: the renderer's child HWND does not exist before.
            // Surface the window exactly like the first printed entry would.
            if (!IsVisible) {
                try {
                    Show();
                    Focus();
                }
                catch {
                }
            }
            _webView.EnsureReady(ProvideInitialPageUri);
        }

        private string ProvideInitialPageUri() {
            if (_documentStarted)
                return null;
            _documentStarted = true;
            return WriteInitialPageFile();
        }

        private string WriteInitialPageFile() {
            var cssPath = _initialStyleSheetPath ?? GetStyleSheetFile();
            var cssHref = cssPath ?? string.Empty;
            try {
                cssHref = new Uri(Path.GetFullPath(cssPath)).AbsoluteUri;
            }
            catch {
            }
            var dochead = string.Format(
                ScriptConsoleConfigs.DOCTYPE + ScriptConsoleConfigs.DOCHead,
                AppVersion,
                _webView.BrowserVersion,
                cssHref
                );
            var html = dochead + "<html><body></body></html>";
            _outputHtmlPath = Path.Combine(UserEnv.UserTemp, string.Format("pyrevit-output-{0}.html", OutputUniqueId));
            File.WriteAllText(_outputHtmlPath, html);
            return new Uri(_outputHtmlPath).AbsoluteUri;
        }

        public string OutputTitle {
            get {
                return Title;
            }
            set {
                Title = value;
            }
        }

        public void LockSize() {
            this.ResizeMode = ResizeMode.NoResize;
        }

        public void UnlockSize() {
            this.ResizeMode = ResizeMode.CanResizeWithGrip;
        }

        public void Freeze() {
            if (_frozen)
                return;
            EnsureDocumentReadyBlocking();
            _frozenBodyHtml = DecodeJsonString(_webView.EvalScript("(document.body ? document.body.innerHTML : '')")) ?? string.Empty;
            _frozen = true;
            UpdateInlineWaitAnimation();
        }

        public void Unfreeze() {
            if (!_frozen)
                return;
            EnsureDocumentReadyBlocking();
            string snapshot;
            lock (_pendingLock) {
                if (_frozenPendingHtml.Length > 0) {
                    _frozenBodyHtml += _frozenPendingHtml.ToString();
                    _frozenPendingHtml.Clear();
                }
                snapshot = _frozenBodyHtml ?? string.Empty;
            }
            _webView.EvalScript("document.body.innerHTML = " + ToJsString(snapshot) + ";");
            _frozenBodyHtml = null;
            _frozen = false;
            UpdateInlineWaitAnimation(false);
        }

        public void ScrollToBottom() {
            _webView.PostScript("window.scrollTo(0, document.body.scrollHeight);");
        }

        internal void ForceRenderFrame() {
            if (_renderingFrame)
                return;
            _renderingFrame = true;
            try {
                // A queued flush sits below Render priority in the dispatcher
                // queue and Invoke(Render) will not process it, so drain the
                // buffer synchronously or output never appears when nothing
                // else pumps this dispatcher.
                SyncFlushBlocking();
                if (Dispatcher != null
                        && !Dispatcher.HasShutdownStarted
                        && !Dispatcher.HasShutdownFinished) {
                    Dispatcher.Invoke(() => { }, DispatcherPriority.Render);
                }
            }
            catch {
            }
            finally {
                _renderingFrame = false;
            }
        }

        public void FocusOutput() {
            _webView.Control.Focus();
        }

        /// <summary>
        /// Escape and wrap contents into the given block template
        /// (e.g. <see cref="ScriptConsoleConfigs.DefaultBlock"/>) and return
        /// ready-to-insert html.
        /// </summary>
        public string ComposeEntry(string contents, string HtmlElementType) {
            // order is important
            // "<"      --->    &lt;
            contents = ScriptConsoleConfigs.EscapeForHtml(contents ?? string.Empty);
            // &clt;    --->    ">"
            contents = ScriptConsoleConfigs.FromCustomHtmlTags(contents);
            // "\n"     --->    <br/>
            contents = ScriptConsoleConfigs.EscapeForOutput(contents);
            // :heart:  --->    \uFFFF (emoji unicode)
            contents = Emojis.Emojize(contents);

            return WrapInBlock(contents, HtmlElementType);
        }

        internal static string WrapInBlock(string contents, string blockTemplate) {
            if (string.IsNullOrEmpty(blockTemplate))
                return contents;
            var closeIndex = blockTemplate.LastIndexOf("</", StringComparison.OrdinalIgnoreCase);
            return closeIndex < 0
                ? blockTemplate + contents
                : blockTemplate.Insert(closeIndex, contents);
        }

        public void AppendText(string OutputText, string HtmlElementType, bool record = true) {
            if (record)
                _lastLine = OutputText;

            AppendEntry(ComposeEntry(OutputText, HtmlElementType));
        }

        private void AppendEntry(string entryHtml) {
            if (string.IsNullOrEmpty(entryHtml))
                return;

            lock (_pendingLock) {
                if (_frozen)
                    _frozenPendingHtml.Append(entryHtml);
                else
                    _pendingHtml.Append(entryHtml);
            }

            if (!_frozen)
                QueueFlush();
        }

        /// <summary>
        /// Warning: the callback swallows its exceptions. An exception escaping a
        /// <see cref="Dispatcher.BeginInvoke(Delegate, DispatcherPriority)"/>
        /// callback reaches <c>Dispatcher.UnhandledException</c> and terminates
        /// Revit; output failing to render must never be fatal.
        /// </summary>
        private void QueueFlush() {
            if (_flushQueued || ClosedByUser)
                return;
            _flushQueued = true;
            Dispatcher.BeginInvoke(
                new Action(() => {
                    try {
                        FlushPendingEntries();
                    }
                    catch (Exception ex) {
                        ScriptRendererLog.Error("output flush failed. {0}", ex);
                    }
                }),
                DispatcherPriority.Normal);
        }

        /// <summary>
        /// Post buffered entries into the document, in submission order.
        ///
        /// Important: writes are fire-and-forget. <c>ExecuteScriptAsync</c>
        /// preserves submission order, so a later read still observes these
        /// inserts, and the print path must never pump a nested dispatcher frame —
        /// it runs inside Revit API callbacks during session load.
        ///
        /// Content arriving before the document is ready stays buffered until
        /// <see cref="ScriptWebView.DocumentReady"/>; re-queueing instead would
        /// spin the dispatcher for as long as the core takes to come up. Content
        /// is discarded only once the renderer can never render it.
        /// </summary>
        private void FlushPendingEntries() {
            _flushQueued = false;

            string payload;
            lock (_pendingLock) {
                payload = _pendingHtml.ToString();
                _pendingHtml.Clear();
            }

            if (payload.Length == 0 || ClosedByUser)
                return;

            if (_webView.RuntimeMissing || _webView.InitializationFailed) {
                ReportOutputLossOnce();
                return;
            }

            EnsureDocumentReady();

            if (!_webView.IsDocumentReady) {
                lock (_pendingLock) {
                    _pendingHtml.Insert(0, payload);
                }
                return;
            }

            _webView.PostScript(BuildInsertEntriesJs(ToJsString(payload)));
        }

        /// <summary>
        /// Report discarded output once per window: this is reached on every
        /// subsequent write, and the record itself can reach the console and
        /// schedule another flush.
        /// </summary>
        private void ReportOutputLossOnce() {
            if (_outputLossReported)
                return;
            _outputLossReported = true;
            ScriptRendererLog.Error(
                "discarding output for this window: runtimeMissing={0} initFailed={1}",
                _webView.RuntimeMissing, _webView.InitializationFailed);
        }

        private void WebView_DocumentReady(object sender, EventArgs e) {
            FlushPendingEntries();
        }

        /// <summary>Push all buffered entries into the document, in order.</summary>
        internal void SyncFlushBlocking() {
            bool workPending;
            lock (_pendingLock) {
                workPending = _flushQueued || _pendingHtml.Length > 0;
            }
            if (workPending)
                FlushPendingEntries();
        }

        /// <summary>
        /// Bring the renderer up and block until the document can be read, then
        /// drain buffered content so a following read observes it.
        ///
        /// Warning: for the synchronous API only — DOM reads, freeze, and
        /// injection, which run from user commands and would otherwise silently
        /// drop work posted before the core is up. Never call this from the print
        /// path; see <see cref="ScriptWebView.WaitUntilReady"/>.
        /// </summary>
        internal void EnsureDocumentReadyBlocking() {
            EnsureDocumentReady();
            _webView.WaitUntilReady();
            SyncFlushBlocking();
        }

        /// <summary>
        /// Append one buffered stream payload as a single output entry,
        /// keeping multi-line html constructs intact.
        /// </summary>
        public void AppendHtmlFragment(string OutputText, string HtmlElementType) {
            if (string.IsNullOrEmpty(OutputText))
                return;

            OutputText = OutputText.Replace("\r\n", "\n");
            if (OutputText.Length == 0)
                return;

            AppendText(OutputText, HtmlElementType, record: false);

            // track the latest (possibly incomplete) line so input-prompt detection stays accurate
            _lastLine = OutputText.Substring(OutputText.LastIndexOf('\n') + 1).TrimEnd('\r');
        }

        public void AppendError(string OutputText, ScriptEngineType engineType) {
            Unfreeze();
            string errorHeader = string.Empty;
            switch (engineType) {
                case ScriptEngineType.IronPython:
                    errorHeader = ScriptConsoleConfigs.ToCustomHtmlTags(ScriptConsoleConfigs.IPYErrorHeader);
                    break;
                case ScriptEngineType.CPython:
                    errorHeader = ScriptConsoleConfigs.ToCustomHtmlTags(ScriptConsoleConfigs.CPYErrorHeader);
                    break;
                case ScriptEngineType.CSharp:
                    errorHeader = ScriptConsoleConfigs.ToCustomHtmlTags(ScriptConsoleConfigs.CSharpErrorHeader);
                    break;
                case ScriptEngineType.Invoke:
                    break;
                case ScriptEngineType.VisualBasic:
                    errorHeader = ScriptConsoleConfigs.ToCustomHtmlTags(ScriptConsoleConfigs.VBErrorHeader);
                    break;
                case ScriptEngineType.IronRuby:
                    errorHeader = ScriptConsoleConfigs.ToCustomHtmlTags(ScriptConsoleConfigs.IRubyErrorHeader);
                    break;
                case ScriptEngineType.DynamoBIM:
                    break;
                case ScriptEngineType.Grasshopper:
                    break;
                case ScriptEngineType.Content:
                    break;
            }
            // add new line to header
            if (errorHeader != string.Empty)
                errorHeader += "\n";

            // if this is a know debugger stop error
            // make a nice report
            foreach (var dbgr in _supportedDebuggers) {
                foreach(var stopFinder in dbgr.StopFinders) {
                    if (stopFinder.Item1.IsMatch(OutputText)) {
                        AppendText(
                            errorHeader + stopFinder.Item2,
                            ScriptConsoleConfigs.ErrorBlock
                            );
                        return;
                    }
                }
            }

            // otherwise report the error
            AppendText(
                errorHeader + OutputText,
                ScriptConsoleConfigs.ErrorBlock
                );
        }

        public string GetLastLine() {
            return _lastLine;
        }

        public string GetInput() {
            // checkout the last line and configure the input control
            string lastLine = GetLastLine().ToLower();
            // determine debugger
            bool dbgMode = false;
            foreach (var dbgr in _supportedDebuggers) {
                if (dbgr.PromptFinder.IsMatch(lastLine)) {
                    stdinBar.EnableDebug(
                        dbgCont: dbgr.DebugContinueKey,
                        dbgStepOver: dbgr.DebugStepOverKey,
                        dbgStepIn: dbgr.DebugStepInKey,
                        dbgStepOut: dbgr.DebugStepOutKey,
                        dbgStop: dbgr.DebugStopKey
                        );
                    dbgMode = true;
                }
            }

            // if no debugger, find other patterns
            if (!dbgMode &&
                    new string[] { "select", "file" }.All(x => lastLine.Contains(x)))
                stdinBar.EnableFilePicker();

            // ask for input
            Activate(); Focus();

            stdinBar.Show();
            // printing an empty line will cause the page to scroll to
            // bottom again and not be covered by the input control
            AppendText("", ScriptConsoleConfigs.DefaultBlock, record: false);
            string inputText = stdinBar.ReadInput();
            stdinBar.Hide();

            // return input
            return inputText;
        }

        private void WebView_NavigationStarting(object sender, CoreWebView2NavigationStartingEventArgs e) {
            var inputUrl = e.Uri ?? string.Empty;
            if (inputUrl.StartsWith("about:", StringComparison.InvariantCultureIgnoreCase))
                return;

            if (inputUrl.StartsWith("http") && !inputUrl.StartsWith("http://localhost")) {
                OpenUrlExternally(inputUrl);
            }
            else if (inputUrl.StartsWith("revit")) {
                e.Cancel = true;
                ScriptConsoleUtils.ProcessUrl(_uiApp, inputUrl, this);
                return;
            }
            else if (inputUrl.StartsWith("file")) {
                return;
            }

            e.Cancel = true;
        }

        private static void OpenUrlExternally(string url) {
            try {
                Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
            }
            catch {
            }
        }

        public void SetElementVisibility(bool visibility, string elementId) {
            EnsureDocumentReady();
            _webView.PostScript(BuildSetElementDisplayJs(
                ToJsString(elementId),
                visibility ? "''" : "'none'"));
        }

        public void SetProgressBarVisibility(bool visibility) {
            if (this.TaskbarItemInfo != null)
                // taskbar progress object
                this.TaskbarItemInfo.ProgressState = visibility ? System.Windows.Shell.TaskbarItemProgressState.Normal : System.Windows.Shell.TaskbarItemProgressState.None;

            EnsureDocumentReady();
            _webView.PostScript(BuildSetElementDisplayJs(
                ToJsString(ScriptConsoleConfigs.ProgressBlockId),
                visibility ? "''" : "'none'"));
        }

        public void SetActivityBarVisibility(bool visibility) {
            activityBar.Visibility = visibility ? Visibility.Visible : Visibility.Collapsed;
        }

        public void UpdateTaskBarProgress(float curValue, float maxValue) {
            if (this.TaskbarItemInfo == null) {
                // taskbar progress object
                var taskbarinfo = new System.Windows.Shell.TaskbarItemInfo();
                taskbarinfo.ProgressState = System.Windows.Shell.TaskbarItemProgressState.Normal;
                this.TaskbarItemInfo = taskbarinfo;
            }

            this.TaskbarItemInfo.ProgressValue = curValue / maxValue;
        }

        public void UpdateTaskBarProgress(bool indeterminate) {
            if (this.TaskbarItemInfo == null) {
                // taskbar progress object
                var taskbarinfo = new System.Windows.Shell.TaskbarItemInfo();
                taskbarinfo.ProgressState = System.Windows.Shell.TaskbarItemProgressState.Indeterminate;
                this.TaskbarItemInfo = taskbarinfo;
            }
        }

        public void UpdateActivityBar(float curValue, float maxValue) {
            if (this.ClosedByUser) {
                return;
            }

            UpdateTaskBarProgress(curValue, maxValue);
            activityBar.UpdateProgressBar(curValue, maxValue);
            SetActivityBarVisibility(true);
        }

        public void UpdateActivityBar(bool indeterminate) {
            if (this.ClosedByUser) {
                return;
            }

            UpdateTaskBarProgress(indeterminate);
            activityBar.IsActive = indeterminate;
            SetActivityBarVisibility(indeterminate);
        }

        public void UpdateProgressBar(float curValue, float maxValue) {
            if (this.ClosedByUser) {
                return;
            }

            UpdateTaskBarProgress(curValue, maxValue);

            EnsureDocumentReady();
            if (!this.IsVisible) {
                try {
                    this.Show();
                    this.Focus();
                }
                catch {
                    return;
                }
            }

            SetProgressBarVisibility(true);

            var widthStyleProperty = string.Format(System.Globalization.CultureInfo.InvariantCulture, "{0}%", Math.Max(0, Math.Min(100, (curValue / maxValue) * 100)));
            _webView.PostScript(BuildUpdateProgressJs(ToJsString(widthStyleProperty)));
        }

        public void UpdateInlineWaitAnimation(bool state = true) {
            if (state) {
                _animationTimer = new DispatcherTimer();
                _animationTimer.Tick += (sender, e) => {
                    UpdateInlineWait();
                };
                _animationTimer.Interval = new TimeSpan(0, 0, 0, 0, 100);
                _animationTimer.Start();
            }
            else if (_animationTimer != null) {
                _animationTimer.Stop();
                _animationTimer = null;
            }
        }

        public void UpdateInlineWait() {
            if (this.ClosedByUser) {
                return;
            }

            EnsureDocumentReady();
            if (!this.IsVisible) {
                try {
                    this.Show();
                    this.Focus();
                }
                catch {
                    return;
                }
            }

            _inlineWaitIndex = (_inlineWaitIndex + 1) % ScriptConsoleConfigs.InlineWaitSequence.Count;
            var waitText = ScriptConsoleConfigs.InlineWaitSequence[_inlineWaitIndex];
            _webView.PostScript(BuildInlineWaitJs(ToJsString(waitText)));
        }

        public void SelfDestructTimer(int seconds) {
            var dispatcherTimer = new DispatcherTimer();
            dispatcherTimer.Tick += (sender, e) => {
                var dt = (DispatcherTimer)sender;
                dt.Stop();
                Close();
            };
            dispatcherTimer.Interval = new TimeSpan(0, 0, seconds);
            dispatcherTimer.Start();
        }

        private void Window_Loaded(object sender, System.EventArgs e) {
            var outputWindow = (ScriptConsole)sender;
            // Install low-level keyboard hook for Ctrl+C/Ctrl+A support.
            // Installed here (not in constructor) so Window_Closing can always dispose it.
            // Fix for https://github.com/pyrevitlabs/pyRevit/issues/1729
            _keyHook = new ScriptConsoleLowLevelKeyHook(this);
            ScriptConsoleManager.AppendToOutputWindowList(this);
            ApplyCloseOthersConfig();
        }

        private void Window_Closing(object sender, System.ComponentModel.CancelEventArgs e) {
            var outputWindow = (ScriptConsole)sender;
            outputWindow._keyHook?.Dispose();

            outputWindow.stdinBar.CancelRead();

            ScriptConsoleManager.RemoveFromOutputList(this);
        }

        private void Window_Closed(object sender, System.EventArgs e) {
            var outputWindow = (ScriptConsole)sender;

            var grid = (Grid)outputWindow.Content;
            grid.Children.Remove(outputWindow._webView.Control);
            grid.Children.Clear();

            outputWindow._webView.Dispose();
            outputWindow.Content = null;

            if (outputWindow._outputHtmlPath != null) {
                try {
                    File.Delete(outputWindow._outputHtmlPath);
                }
                catch {
                }
                outputWindow._outputHtmlPath = null;
            }

            outputWindow.ClosedByUser = true;
        }

        internal void InjectHtmlElement(string targetName, string elementTag, string contents, Dictionary<string, string> attribs) {
            if (string.IsNullOrEmpty(elementTag))
                return;

            EnsureDocumentReadyBlocking();

            var target = string.Equals(targetName, "head", StringComparison.OrdinalIgnoreCase) ? "head" : "body";

            if (elementTag.Equals("script", StringComparison.OrdinalIgnoreCase)) {
                var attrs = new Dictionary<string, string>();
                if (attribs != null) {
                    foreach (var attr in attribs)
                        attrs[attr.Key] = attr.Value ?? string.Empty;
                }
                _webView.PostScript(BuildInjectScriptElementJs(
                    ToJsString(contents ?? string.Empty),
                    pyRevitLabs.Json.JsonConvert.SerializeObject(attrs),
                    ToJsString(target)));
                return;
            }

            var attrText = new StringBuilder();
            if (attribs != null) {
                foreach (var attr in attribs)
                    attrText.AppendFormat(
                        " {0}=\"{1}\"",
                        attr.Key,
                        (attr.Value ?? string.Empty).Replace("&", "&amp;").Replace("\"", "&quot;"));
            }

            var html = string.Format("<{0}{1}>{2}</{0}>", elementTag, attrText, contents ?? string.Empty);
            _webView.PostScript(BuildInjectHtmlJs(ToJsString(html), ToJsString(target)));
        }

        internal void PostRendererScript(string javaScript) {
            _webView.PostScript(javaScript);
        }

        internal bool RendererHasFocus {
            get { return _webView.Control != null && _webView.Control.IsKeyboardFocusWithin; }
        }

        internal static string ToJsString(string value) {
            return pyRevitLabs.Json.JsonConvert.SerializeObject(value ?? string.Empty);
        }

        internal static string DecodeJsonString(string jsonResult) {
            if (string.IsNullOrEmpty(jsonResult) || jsonResult == "null" || jsonResult == "undefined")
                return null;
            try {
                return pyRevitLabs.Json.JsonConvert.DeserializeObject<string>(jsonResult);
            }
            catch {
                return jsonResult;
            }
        }

        private System.Windows.Shapes.Path MakeButtonPath(string geom, int size = 14) {
            var path = new System.Windows.Shapes.Path();
            path.Stretch = Stretch.Uniform;
            path.Height = size;
            path.Fill = Brushes.White;
            path.Data = Geometry.Parse(geom);
            return path;
        }

        private System.Windows.Shapes.Path GetPinIcon(bool pinned) {
            if (pinned)
                return MakeButtonPath("M16,12V4H17V2H7V4H8V12L6,14V16H11.2V22H12.8V16H18V14L16,12Z");
            else
                return MakeButtonPath("M2,5.27L3.28,4L20,20.72L18.73,22L12.8,16.07V22H11.2V16H6V14L8,12V11.27L2,5.27M16,12L18,14V16H17.82L8,6.18V4H7V2H17V4H16V12Z");
        }

        private System.Windows.Shapes.Path GetAutoCollapseIcon(bool active) {
            if (active)
                return MakeButtonPath("M4.08,11.92L12,4L19.92,11.92L18.5,13.33L13,7.83V22H11V7.83L5.5,13.33L4.08,11.92M12,4H22V2H2V4H12Z");
            else
                return MakeButtonPath("M19.92,12.08L12,20L4.08,12.08L5.5,10.67L11,16.17V2H13V16.17L18.5,10.66L19.92,12.08M12,20H2V22H22V20H12Z");
        }

        private void Save_Contents_Button_Clicked(object sender, RoutedEventArgs e)
        {
            var saveDlg = new System.Windows.Forms.SaveFileDialog()
            {
                Title = "Save Output to:",
                Filter = "HTML Files|*.html",
                DefaultExt = "html",
                AddExtension = true,
                RestoreDirectory = true
            };
            if (saveDlg.ShowDialog() != System.Windows.Forms.DialogResult.OK || string.IsNullOrWhiteSpace(saveDlg.FileName))
            {
                return;
            }
            try
            {
                using (StreamWriter writer = File.CreateText(saveDlg.FileName))
                {
                    writer.Write(GetFullHtml());
                }
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show($"Error saving file: {ex.Message}", "Save Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }


        private void PinButton_Click(object sender, RoutedEventArgs e) {
            var button = e.Source as Button;

            if (Topmost) {
                if (IsAutoCollapseActive) {
                    Topmost = false;
                    IsAutoCollapseActive = false;
                    button.Content = GetPinIcon(false);
                    button.ToolTip = "Keep On Top";
                } else {
                    IsAutoCollapseActive = true;
                    button.Content = GetAutoCollapseIcon(true);
                    button.ToolTip = "Release";
                }
            }
            else {
                if (IsAutoCollapseActive)
                    IsAutoCollapseActive = false;
                Topmost = true;
                IsAutoCollapseActive = false;
                button.Content = GetPinIcon(true);
                button.ToolTip = "Activate Auto Collapse";
            }
        }

        private System.Windows.Shapes.Path GetExpandToggleIcon(bool expanded) {
            if (expanded)
                return MakeButtonPath("M19,6.41L17.59,5L7,15.59V9H5V19H15V17H8.41L19,6.41Z", size: 12);
            else
                return MakeButtonPath("M5,17.59L15.59,7H9V5H19V15H17V8.41L6.41,19L5,17.59Z", size: 12);
        }

        private void ExpandToggleButton_Click(object sender, RoutedEventArgs e) {
            var button = e.Source as Button;

            if (IsExpanded) {
                Width = Width / 2;
                IsExpanded = false;
                button.Content = GetExpandToggleIcon(IsExpanded);
                button.ToolTip = "Expand";
            }
            else {
                Width = Width * 2;
                IsExpanded = true;
                button.Content = GetExpandToggleIcon(IsExpanded);
                button.ToolTip = "Shrink";
            }
        }

        private string SaveContentsToTemp() {
            string tempHtml = Path.Combine(UserEnv.UserTemp, string.Format("{0}.html", OutputTitle));
            var f = File.CreateText(tempHtml);
            f.Write(GetFullHtml());
            f.Close();
            return tempHtml;
        }

        private void OpenButton_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                var uri = new Uri(SaveContentsToTemp()).AbsoluteUri;
                var processInfo = new ProcessStartInfo()
                {
                    FileName = uri,
                    UseShellExecute = true
                };
                Process.Start(processInfo);
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show($"Error opening file: {ex.Message}", "Open Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void PrintButton_Click(object sender, RoutedEventArgs e) {
            _webView.ShowPrintUi();
        }

        private void CopyButton_Click(object sender, RoutedEventArgs e) {
            SyncFlushBlocking();
            var text = DecodeJsonString(_webView.EvalScript("document.body.innerText"));
            Clipboard.SetText(text ?? string.Empty);
            var notif = new ToolTip() { Content = "Copied to Clipboard" };
            notif.StaysOpen = false;
            notif.IsOpen = true;
        }

        /// <summary>
        /// Low-level keyboard hook that intercepts Ctrl+C/Ctrl+A before Revit's
        /// accelerator table consumes them. Revit calls IOleInPlaceActiveObject
        /// .TranslateAccelerator in its message loop, which processes Ctrl+C for
        /// its own Copy command before WPF events or JavaScript onkeydown ever
        /// see the keystroke. WH_KEYBOARD_LL fires at the OS level before any of
        /// this processing occurs.
        /// Fix for https://github.com/pyrevitlabs/pyRevit/issues/1729
        /// </summary>
        private class ScriptConsoleLowLevelKeyHook : IDisposable {
            private delegate IntPtr LowLevelKeyboardProc(int nCode, IntPtr wParam, IntPtr lParam);

            [System.Runtime.InteropServices.DllImport("user32.dll", SetLastError = true)]
            private static extern IntPtr SetWindowsHookEx(int idHook, LowLevelKeyboardProc lpfn, IntPtr hMod, uint dwThreadId);

            [System.Runtime.InteropServices.DllImport("user32.dll", SetLastError = true)]
            private static extern bool UnhookWindowsHookEx(IntPtr hhk);

            [System.Runtime.InteropServices.DllImport("user32.dll")]
            private static extern IntPtr CallNextHookEx(IntPtr hhk, int nCode, IntPtr wParam, IntPtr lParam);

            [System.Runtime.InteropServices.DllImport("kernel32.dll")]
            private static extern IntPtr GetModuleHandle(string lpModuleName);

            private const int WH_KEYBOARD_LL = 13;
            private const int WM_KEYDOWN = 0x0100;
            private const int VK_C = 0x43;
            private const int VK_A = 0x41;

            private IntPtr _hookId = IntPtr.Zero;
            private readonly ScriptConsole _console;
            private readonly LowLevelKeyboardProc _proc;

            public ScriptConsoleLowLevelKeyHook(ScriptConsole console) {
                _console = console;
                _proc = HookCallback;
                _hookId = SetWindowsHookEx(WH_KEYBOARD_LL, _proc,
                    GetModuleHandle(null), 0);
                if (_hookId == IntPtr.Zero)
                    System.Diagnostics.Debug.WriteLine("[ScriptConsoleLowLevelKeyHook] SetWindowsHookEx failed to install keyboard hook.");
            }

            private IntPtr HookCallback(int nCode, IntPtr wParam, IntPtr lParam) {
                if (nCode >= 0 && wParam == (IntPtr)WM_KEYDOWN) {
                    int vkCode = System.Runtime.InteropServices.Marshal.ReadInt32(lParam);
                    bool ctrl = (System.Windows.Forms.Control.ModifierKeys & System.Windows.Forms.Keys.Control) != 0;

                    if (ctrl && (vkCode == VK_C || vkCode == VK_A) &&
                        _console.IsActive && _console.RendererHasFocus) {
                        try {
                            _console.PostRendererScript(
                                vkCode == VK_C
                                    ? "document.execCommand('Copy');"
                                    : "document.execCommand('SelectAll');");
                        } catch (Exception ex) {
                            System.Diagnostics.Debug.WriteLine($"[ScriptConsoleLowLevelKeyHook] execCommand failed: {ex.Message}");
                        }
                        return (IntPtr)1;
                    }
                }
                return CallNextHookEx(_hookId, nCode, wParam, lParam);
            }

            public void Dispose() {
                if (_hookId != IntPtr.Zero) {
                    UnhookWindowsHookEx(_hookId);
                    _hookId = IntPtr.Zero;
                }
            }
        }

        private void CollapseWindow() {
            prevHeight = Height;
            Height = TitleBarHeight;
            //ResizeBorderThickness = new Thickness(0);
            IsCollapsed = true;
        }

        private void UnCollapseWindow() {
            Height = prevHeight;
            //ResizeBorderThickness = new Thickness(10);
            IsCollapsed = false;
        }

        private void ScriptOutput_GotFocus(object sender, EventArgs e) {
            if (IsAutoCollapseActive && IsCollapsed)
                UnCollapseWindow();
        }

        private void ScriptOutput_LostFocus(object sender, EventArgs e) {
            if (IsAutoCollapseActive && !IsCollapsed)
                CollapseWindow();
        }

        public void Dispose() {
        }
    }
}
