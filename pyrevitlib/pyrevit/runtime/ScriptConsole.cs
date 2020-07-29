using System;
using System.Windows;
using System.IO;
using System.Collections.Generic;
using System.Windows.Controls;
using System.Windows.Markup;
using System.Windows.Media;
using System.Windows.Threading;
using Autodesk.Revit.UI;
using System.Text.RegularExpressions;
using System.Diagnostics;

using pyRevitLabs.Common;
using pyRevitLabs.CommonWPF.Controls;

namespace PyRevitLabs.PyRevit.Runtime {
    public static class ScriptConsoleConfigs {
        public static string DOCTYPE = "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.01 Transitional//EN\" \"http://www.w3.org/TR/html4/loose.dtd\">";
        public static string DOCHead = "<head>" +
                                       "<meta http-equiv=\"X-UA-Compatible\" content=\"IE=Edge\" />" +
                                       "<meta http-equiv=\"content-type\" content=\"text/html; charset=utf-8\" />" +
                                       "<meta name=\"appversion\" content=\"{0}\" />" +
                                       "<meta name=\"rendererversion\" content=\"{1}\" />" +
                                       "<link rel=\"stylesheet\" href=\"file:///{2}\">" +
                                       "</head>";
        public static string DefaultBlock = "<div class=\"entry\"></div>";
        public static string ErrorBlock = "<div class=\"errorentry\"></div>";
        public static string IPYErrorHeader = "<strong>IronPython Traceback:</strong>";
        public static string CPYErrorHeader = "<strong>CPython Traceback:</strong>";
        public static string IRubyErrorHeader = "<strong>IronRuby Traceback:</strong>";
        public static string CLRErrorHeader = "<strong>Script Executor Traceback:</strong>";
        public static string CSharpErrorHeader = "<strong>C# Traceback:</strong>";
        public static string VBErrorHeader = "<strong>VB.NET Traceback:</strong>";
        public static string ProgressBlock = "<div class=\"progressindicator\" id=\"pbarcontainer\"></div>";
        public static string ProgressBlockId = "pbarcontainer";
        public static string ProgressBar = "<div class=\"progressbar\" id=\"pbar\"></div>";
        public static string ProgressBarId = "pbar";
        public static string InlineWaitBlock = "<div class=\"inlinewait\" id=\"inlnwait\">\u280b Preparing results...</div>";
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
                Source = new Uri("pack://application:,,,/pyRevitLabs.MahAppsMetro;component/Styles/Colors.xaml")
            });

            Resources.MergedDictionaries.Add(new ResourceDictionary() {
                Source = new Uri("pack://application:,,,/pyRevitLabs.MahAppsMetro;component/Styles/FlatButton.xaml")
            });

            var accentResDict = new ResourceDictionary() {
                Source = new Uri("pack://application:,,,/pyRevitLabs.MahAppsMetro;component/Styles/Accents/Steel.xaml")
            };

            var pyrevitHighlightColor = Color.FromArgb(0xFF, 0xf3, 0x9c, 0x12);
            var pyrevitBackground = new SolidColorBrush() { Color = Color.FromArgb(0xFF, 0x2c, 0x3e, 0x50) };
            var pyrevitHighlight = new SolidColorBrush() { Color = pyrevitHighlightColor };
            accentResDict["AccentColorBrush"] = pyrevitBackground;
            accentResDict["WindowTitleColorBrush"] = pyrevitBackground;

            // overriding colors on the progressbar control
            var progressBarOverlay = Color.FromArgb(0x66, 0xFF, 0xFF, 0xFF);
            accentResDict["ProgressBrush"] = pyrevitHighlight;
            accentResDict["ProgressIndeterminateColor1"] = progressBarOverlay;
            accentResDict["ProgressIndeterminateColor2"] = progressBarOverlay;
            accentResDict["ProgressIndeterminateColor3"] = pyrevitHighlightColor;
            accentResDict["ProgressIndeterminateColor4"] = pyrevitHighlightColor;

            Resources.MergedDictionaries.Add(accentResDict);
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

    public partial class ScriptConsole : ScriptConsoleTemplate, IComponentConnector, IDisposable {
        private bool _contentLoaded;
        private bool _debugMode;
        private bool _frozen = false;
        private DispatcherTimer _animationTimer;
        private System.Windows.Forms.HtmlElement _lastDocumentBody = null;
        private UIApplication _uiApp;

        // OutputUniqueId is set in constructor
        // OutputUniqueId is unique for every output window
        public string OutputUniqueId;

        // OutputId is set by the requesting pyRevit command
        // OutputId is the same for all output windows that belong to a single pyRevit command
        public string OutputId;

        // to track if user manually closed the window
        public bool ClosedByUser = false;

        // is window collapsed?
        private double prevHeight = 0;
        public bool IsCollapsed = false;
        public bool IsAutoCollapseActive = false;
        // is window expanded?
        public bool IsExpanded = false;

        // Html renderer and its Winforms host, and navigate handler method
        public System.Windows.Forms.Integration.WindowsFormsHost host;
        public System.Windows.Forms.WebBrowser renderer;
        public System.Windows.Forms.WebBrowserNavigatingEventHandler _navigateHandler;
        public ActivityBar activityBar;

        public ScriptConsole(bool debugMode = false, UIApplication uiApp = null) : base() {
            _debugMode = debugMode;
            _uiApp = uiApp;

            // setup unique id for this output window
            OutputUniqueId = Guid.NewGuid().ToString();

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

            host = new System.Windows.Forms.Integration.WindowsFormsHost();
            host.SnapsToDevicePixels = true;

            // Create the WebBrowser control.
            renderer = new System.Windows.Forms.WebBrowser();

            _navigateHandler = new System.Windows.Forms.WebBrowserNavigatingEventHandler(renderer_Navigating);
            renderer.Navigating += _navigateHandler;

            // setup the default html page
            SetupDefaultPage();

            // Assign the WebBrowser control as the host control's child.
            host.Child = renderer;

            // activiy bar
            activityBar = new ActivityBar();
            activityBar.Foreground = Brushes.White;
            activityBar.Visibility = Visibility.Collapsed;

            // Add the interop host control to the Grid
            // control's collection of child controls.
            Grid baseGrid = new Grid();
            baseGrid.Margin = new Thickness(0, 0, 0, 0);

            var activityBarRow = new RowDefinition();
            activityBarRow.Height = GridLength.Auto;
            baseGrid.RowDefinitions.Add(activityBarRow);

            var rendererRow = new RowDefinition();
            baseGrid.RowDefinitions.Add(rendererRow);

            //if (_debugMode) {
            //    var splitterRow = new RowDefinition();
            //    var replRow = new RowDefinition();

            //    splitterRow.Height = new GridLength(6);
            //    replRow.Height = new GridLength(100);

            //    baseGrid.RowDefinitions.Add(splitterRow);
            //    baseGrid.RowDefinitions.Add(replRow);

            //    var splitter = new GridSplitter();
            //    splitter.ResizeDirection = GridResizeDirection.Rows;
            //    splitter.HorizontalAlignment = HorizontalAlignment.Stretch;
            //    splitter.Background = Brushes.LightGray;

            //    var repl = new REPLControl();

            //    Grid.SetRow(splitter, 2);
            //    Grid.SetRow(repl, 3);

            //    baseGrid.Children.Add(splitter);
            //    baseGrid.Children.Add(repl);
            //}

            // set activity bar and host
            Grid.SetRow(activityBar, 0);
            Grid.SetRow(host, 1);

            baseGrid.Children.Add(activityBar);
            baseGrid.Children.Add(host);
            this.Content = baseGrid;

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

            this.Width = 900; this.MinWidth = 700;
            this.Height = 600; this.MinHeight = this.TitlebarHeight;
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

        public System.Windows.Forms.HtmlDocument ActiveDocument { get { return renderer.Document; } }

        public Version RendererVersion {
            get {
                return renderer.Version;
            }
        }

        private string GetStyleSheetFile() {
            var envDict = new EnvDictionary();
            return envDict.ActiveStyleSheet;
        }

        public string GetFullHtml() {
            var head = ActiveDocument.GetElementsByTagName("head")[0];
            return ScriptConsoleConfigs.DOCTYPE + head.OuterHtml + ActiveDocument.Body.OuterHtml;
        }

        private void SetupDefaultPage(string styleSheetFilePath = null) {
            string cssFilePath;
            if (styleSheetFilePath != null)
                cssFilePath = styleSheetFilePath;
            else
                cssFilePath = GetStyleSheetFile();

            // create the head with default styling
            var dochead = string.Format(
                ScriptConsoleConfigs.DOCTYPE + ScriptConsoleConfigs.DOCHead,
                AppVersion,
                RendererVersion,
                cssFilePath
                );
            // create default html
            renderer.DocumentText = string.Format("{0}<html><body></body></html>", dochead);

            while (ActiveDocument.Body == null)
                System.Windows.Forms.Application.DoEvents();
        }

        public void WaitReadyBrowser() {
            System.Windows.Forms.Application.DoEvents();
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
            WaitReadyBrowser();
            _lastDocumentBody = ActiveDocument.CreateElement("<body>");
            _lastDocumentBody.InnerHtml = ActiveDocument.Body.InnerHtml;
            _frozen = true;
            UpdateInlineWaitAnimation();
        }

        public void Unfreeze() {
            if (_frozen) {
                WaitReadyBrowser();
                ActiveDocument.Body.InnerHtml = _lastDocumentBody.InnerHtml;
                _frozen = false;
                _lastDocumentBody = null;
                UpdateInlineWaitAnimation(false);
            }
        }

        public void ScrollToBottom() {
            if (ActiveDocument != null) {
                ActiveDocument.Window.ScrollTo(0, ActiveDocument.Body.ScrollRectangle.Height);
            }
        }

        public void FocusOutput() {
            renderer.Focus();
        }

        public System.Windows.Forms.HtmlElement ComposeEntry(string contents, string HtmlElementType) {
            WaitReadyBrowser();
            
            // order is important
            // "<"      --->    &lt;
            contents = ScriptConsoleConfigs.EscapeForHtml(contents);
            // &clt;    --->    ">"
            contents = ScriptConsoleConfigs.FromCustomHtmlTags(contents);
            // "\n"     --->    <br/>
            contents = ScriptConsoleConfigs.EscapeForOutput(contents);
            // :heart:  --->    \uFFFF (emoji unicode)
            contents = ScriptConsoleEmojis.Emojize(contents);

            var htmlElement = ActiveDocument.CreateElement(HtmlElementType);
            htmlElement.InnerHtml = contents;
            return htmlElement;
        }

        public void AppendText(string OutputText, string HtmlElementType) {
            if (!_frozen) {
                WaitReadyBrowser();
                ActiveDocument.Body.AppendChild(ComposeEntry(OutputText, HtmlElementType));
                ScrollToBottom();
            }
            else if (_lastDocumentBody != null) {
                _lastDocumentBody.AppendChild(ComposeEntry(OutputText, HtmlElementType));
            }
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

            AppendText(errorHeader + OutputText, ScriptConsoleConfigs.ErrorBlock);
        }

        private void renderer_Navigating(object sender, System.Windows.Forms.WebBrowserNavigatingEventArgs e) {
            if (!(e.Url.ToString().Equals("about:blank", StringComparison.InvariantCultureIgnoreCase))) {
                var inputUrl = e.Url.ToString();

                if (inputUrl.StartsWith("http") && !inputUrl.StartsWith("http://localhost")) {
                    System.Diagnostics.Process.Start(inputUrl);
                }
                else if (inputUrl.StartsWith("revit")) {
                    e.Cancel = true;
                    ScriptConsoleUtils.ProcessUrl(_uiApp, inputUrl);
                    return;
                }
                else if (inputUrl.StartsWith("file")) {
                    e.Cancel = false;
                    return;
                }

                e.Cancel = true;
            }
        }

        public void SetElementVisibility(bool visibility, string elementId) {
            WaitReadyBrowser();
            if (ActiveDocument != null) {
                var cssdisplay = visibility ? "" : "display: none;";
                var element = ActiveDocument.GetElementById(elementId);
                if (element.Style != null) {
                    if (element.Style.Contains("display:"))
                        element.Style = Regex.Replace(element.Style, "display:.+?;", cssdisplay, RegexOptions.IgnoreCase);
                    else
                        element.Style += cssdisplay;
                }
                else
                    element.Style = cssdisplay;
            }
        }

        public void SetProgressBarVisibility(bool visibility) {
            if (this.TaskbarItemInfo != null)
                // taskbar progress object
                this.TaskbarItemInfo.ProgressState = visibility ? System.Windows.Shell.TaskbarItemProgressState.Normal : System.Windows.Shell.TaskbarItemProgressState.None;

            WaitReadyBrowser();
            if (ActiveDocument != null) {
                var cssdisplay = visibility ? "" : "display: none;";
                var pbarcontainer = ActiveDocument.GetElementById(ScriptConsoleConfigs.ProgressBlockId);
                if (pbarcontainer.Style != null) {
                    if (pbarcontainer.Style.Contains("display:"))
                        pbarcontainer.Style = Regex.Replace(pbarcontainer.Style, "display:.+?;",
                                                            cssdisplay,
                                                            RegexOptions.IgnoreCase);
                    else
                        pbarcontainer.Style += cssdisplay;
                }
                else
                    pbarcontainer.Style = cssdisplay;
            }
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

            WaitReadyBrowser();
            if (ActiveDocument != null) {
                if (!this.IsVisible) {
                    try {
                        this.Show();
                        this.Focus();
                    }
                    catch {
                        return;
                    }
                }

                var pbargraph = ActiveDocument.GetElementById(ScriptConsoleConfigs.ProgressBarId);
                if (pbargraph == null) {
                    if (ActiveDocument != null) {
                        var pbar = ActiveDocument.CreateElement(ScriptConsoleConfigs.ProgressBlock);
                        var newpbargraph = ActiveDocument.CreateElement(ScriptConsoleConfigs.ProgressBar);
                        pbar.AppendChild(newpbargraph);
                        ActiveDocument.Body.AppendChild(pbar);
                    }

                    pbargraph = ActiveDocument.GetElementById(ScriptConsoleConfigs.ProgressBarId);
                }

                SetProgressBarVisibility(true);

                var newWidthStyleProperty = string.Format("width:{0}%;", (curValue / maxValue) * 100);
                if (pbargraph.Style == null)
                    pbargraph.Style = newWidthStyleProperty;
                else
                    pbargraph.Style = Regex.Replace(pbargraph.Style, "width:.+?;", newWidthStyleProperty, RegexOptions.IgnoreCase);
            }
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

            WaitReadyBrowser();
            if (ActiveDocument != null) {
                if (!this.IsVisible) {
                    try {
                        this.Show();
                        this.Focus();
                    }
                    catch {
                        return;
                    }
                }

                var inlinewait = ActiveDocument.GetElementById(ScriptConsoleConfigs.InlineWaitBlockId);
                if (inlinewait == null) {
                    if (ActiveDocument != null) {
                        inlinewait = ActiveDocument.CreateElement(ScriptConsoleConfigs.InlineWaitBlock);
                        ActiveDocument.Body.AppendChild(inlinewait);
                    }

                    inlinewait = ActiveDocument.GetElementById(ScriptConsoleConfigs.InlineWaitBlockId);
                }

                SetElementVisibility(true, ScriptConsoleConfigs.InlineWaitBlockId);

                int idx = ScriptConsoleConfigs.InlineWaitSequence.IndexOf(inlinewait.InnerText);
                if (idx + 1 > ScriptConsoleConfigs.InlineWaitSequence.Count - 1)
                    idx = 0;
                inlinewait.InnerText = ScriptConsoleConfigs.InlineWaitSequence[idx + 1];
                ScrollToBottom();
            }
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
            ScriptConsoleManager.AppendToOutputWindowList(this);
        }

        private void Window_Closing(object sender, System.ComponentModel.CancelEventArgs e) {
            var outputWindow = (ScriptConsole)sender;

            ScriptConsoleManager.RemoveFromOutputList(this);

            outputWindow.renderer.Navigating -= _navigateHandler;
            outputWindow._navigateHandler = null;
        }

        private void Window_Closed(object sender, System.EventArgs e) {
            var outputWindow = (ScriptConsole)sender;

            var grid = (Grid)outputWindow.Content;
            grid.Children.Remove(host);
            grid.Children.Clear();

            outputWindow.renderer.Dispose();
            outputWindow.renderer = null;

            outputWindow.host = null;
            outputWindow.Content = null;

            outputWindow.ClosedByUser = true;
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

        private void Save_Contents_Button_Clicked(object sender, RoutedEventArgs e) {
            var saveDlg = new System.Windows.Forms.SaveFileDialog() {
                Title = "Save Output to:",
                Filter = "HTML|*.html"
            };
            saveDlg.ShowDialog();
            var f = File.CreateText(saveDlg.FileName);
            f.Write(GetFullHtml());
            f.Close();
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

        private void OpenButton_Click(object sender, RoutedEventArgs e) {
            Process.Start(string.Format("file:///{0}", SaveContentsToTemp()));
        }

        private void PrintButton_Click(object sender, RoutedEventArgs e) {
            renderer.ShowPrintPreviewDialog();
        }

        private void CopyButton_Click(object sender, RoutedEventArgs e) {
            Clipboard.SetText(ActiveDocument.Body.InnerText);
            var notif = new ToolTip() { Content = "Copied to Clipboard" };
            notif.StaysOpen = false;
            notif.IsOpen = true;
        }

        private void CollapseWindow() {
            prevHeight = Height;
            Height = TitlebarHeight;
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
