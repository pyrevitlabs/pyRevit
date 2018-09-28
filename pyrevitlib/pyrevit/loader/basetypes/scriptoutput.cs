using System;
using System.Windows;
using System.IO;
using System.Windows.Controls;
using System.Windows.Markup;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using Autodesk.Revit.UI;
using System.Text.RegularExpressions;
using System.Runtime.InteropServices;
using System.Net.Cache;

using MahApps.Metro.Controls;
using pyRevitLabs.CommonWPF.Controls;


namespace PyRevitBaseClasses {
    public partial class PyRevitTemplateWindow : pyRevitLabs.CommonWPF.Windows.AppWindow {
        public PyRevitTemplateWindow() {
            // setup window styles
            SetupDynamicResources();
            EnablePyRevitTemplateWindowStyle();
        }

        public void EnablePyRevitTemplateWindowStyle() {
            SizeChanged += ScriptOutput_SizeChanged;

            // setup template styles
            Background = Brushes.White;
            var glowColor = Color.FromArgb(0x66, 0x2c, 0x3e, 0x50);
            GlowBrush = new SolidColorBrush() { Color = glowColor };
            NonActiveGlowBrush = new SolidColorBrush() { Color = glowColor };

            ResetIcon();

            ResizeBorderThickness = new Thickness(10, 10, 10, 10);
            BorderThickness = new Thickness();
            WindowStartupLocation = WindowStartupLocation.Manual;
            WindowTransitionsEnabled = false;
            SaveWindowPosition = false;
        }

        private void SetupDynamicResources() {
            Resources.MergedDictionaries.Add(new ResourceDictionary() {
                Source = new Uri("pack://application:,,,/MahApps.Metro;component/Styles/Controls.xaml")
            });

            Resources.MergedDictionaries.Add(new ResourceDictionary() {
                Source = new Uri("pack://application:,,,/MahApps.Metro;component/Styles/Fonts.xaml")
            });

            Resources.MergedDictionaries.Add(new ResourceDictionary() {
                Source = new Uri("pack://application:,,,/MahApps.Metro;component/Styles/Colors.xaml")
            });

            var accentResDict = new ResourceDictionary() {
                Source = new Uri("pack://application:,,,/MahApps.Metro;component/Styles/Accents/Steel.xaml")
            };

            // TODO: read the colors from css? all colors and styles should be in the same place
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

        public string GetCurrentPyRevitVersion() {
            var envDict = new EnvDictionary();
            return envDict.pyRevitVersion;
        }

        private void ScriptOutput_SizeChanged(object sender, SizeChangedEventArgs e) {
            Visibility isVisible = Visibility.Visible;
            if (ActualWidth < 400)
                isVisible = Visibility.Collapsed;
            foreach (Button item in RightWindowCommands.Items)
                item.Visibility = isVisible;

            this.TitleForeground = isVisible == Visibility.Visible ? Brushes.White : new SolidColorBrush() { Color = Color.FromArgb(0xFF, 0x2c, 0x3e, 0x50) };
        }

        // app version
        public override string AppVersion { get { return GetCurrentPyRevitVersion(); } }

        public void SetIcon(string iconPath) {
            Icon = LoadIcon(new Uri(iconPath));
            IconBitmapScalingMode = BitmapScalingMode.HighQuality;
            IconEdgeMode = EdgeMode.Aliased;
            IconScalingMode = MultiFrameImageMode.ScaleDownLargerFrame;
            ShowIconOnTitleBar = true;
        }

        public void ResetIcon() {
            var iconPath = Path.Combine(Path.GetDirectoryName(typeof(ActivityBar).Assembly.Location), "outputwindow_icon.png");
            SetIcon(iconPath);
        }
    }

    public partial class ScriptOutput : PyRevitTemplateWindow, IComponentConnector, IDisposable {
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

        // Html renderer and its Winforms host, and navigate handler method
        public System.Windows.Forms.Integration.WindowsFormsHost host;
        public System.Windows.Forms.WebBrowser renderer;
        public System.Windows.Forms.WebBrowserNavigatingEventHandler _navigateHandler;
        public ActivityBar activityBar;

        public ScriptOutput(bool debugMode = false, UIApplication uiApp = null) : base() {
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

            if (_debugMode) {
                var splitterRow = new RowDefinition();
                var replRow = new RowDefinition();

                splitterRow.Height = new GridLength(6);
                replRow.Height = new GridLength(100);

                baseGrid.RowDefinitions.Add(splitterRow);
                baseGrid.RowDefinitions.Add(replRow);

                var splitter = new GridSplitter();
                splitter.ResizeDirection = GridResizeDirection.Rows;
                splitter.HorizontalAlignment = HorizontalAlignment.Stretch;
                splitter.Background = Brushes.LightGray;

                var repl = new REPLControl();

                Grid.SetRow(splitter, 2);
                Grid.SetRow(repl, 3);

                baseGrid.Children.Add(splitter);
                baseGrid.Children.Add(repl);
            }
            
            // set activity bar and host
            Grid.SetRow(activityBar, 0);
            Grid.SetRow(host, 1);

            baseGrid.Children.Add(activityBar);
            baseGrid.Children.Add(host);
            this.Content = baseGrid;

            // TODO: add report button, get email from envvars
            var saveButton = new Button() { Content = "Save Contents" };
            saveButton.Click += Save_Contents_Button_Clicked;
            RightWindowCommands.Items.Insert(0, saveButton);

            this.Width = 900; this.MinWidth = 50;
            this.Height = 600; this.MinHeight = 100;
            this.ResizeMode = ResizeMode.CanResize;

            this.Title = "pyRevit";
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

        private string GetStyleSheetFile() {
            var envDict = new EnvDictionary();
            return envDict.activeStyleSheet;
        }

        private void SetupDefaultPage(string styleSheetFilePath = null) {
            string cssFilePath;
            if (styleSheetFilePath != null)
                cssFilePath = styleSheetFilePath;
            else
                cssFilePath = GetStyleSheetFile();

            // create the head with default styling
            var dochead = string.Format(
                ExternalConfig.doctype + ExternalConfig.dochead,
                GetCurrentPyRevitVersion(),
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

        public void AppendError(string OutputText, string HtmlElementType) {
            Unfreeze();
            AppendText(OutputText, HtmlElementType);
        }

        private void renderer_Navigating(object sender, System.Windows.Forms.WebBrowserNavigatingEventArgs e) {
            if (!(e.Url.ToString().Equals("about:blank", StringComparison.InvariantCultureIgnoreCase))) {
                var inputUrl = e.Url.ToString();

                if (inputUrl.StartsWith("http") && !inputUrl.StartsWith("http://localhost")) {
                    System.Diagnostics.Process.Start(inputUrl);
                }
                else if (inputUrl.StartsWith("revit")) {
                    e.Cancel = true;
                    ScriptOutputHelpers.ProcessUrl(_uiApp, inputUrl);
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
                var pbarcontainer = ActiveDocument.GetElementById(ExternalConfig.progressindicatorid);
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

                var pbargraph = ActiveDocument.GetElementById(ExternalConfig.progressbarid);
                if (pbargraph == null) {
                    if (ActiveDocument != null) {
                        var pbar = ActiveDocument.CreateElement(ExternalConfig.progressindicator);
                        var newpbargraph = ActiveDocument.CreateElement(ExternalConfig.progressbar);
                        pbar.AppendChild(newpbargraph);
                        ActiveDocument.Body.AppendChild(pbar);
                    }

                    pbargraph = ActiveDocument.GetElementById(ExternalConfig.progressbarid);
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

                var inlinewait = ActiveDocument.GetElementById(ExternalConfig.inlinewaitid);
                if (inlinewait == null) {
                    if (ActiveDocument != null) {
                        inlinewait = ActiveDocument.CreateElement(ExternalConfig.inlinewait);
                        ActiveDocument.Body.AppendChild(inlinewait);
                    }

                    inlinewait = ActiveDocument.GetElementById(ExternalConfig.inlinewaitid);
                }

                SetElementVisibility(true, ExternalConfig.inlinewaitid);

                int idx = ExternalConfig.inlinewaitsequence.IndexOf(inlinewait.InnerText);
                if (idx + 1 > ExternalConfig.inlinewaitsequence.Count - 1)
                    idx = 0;
                inlinewait.InnerText = ExternalConfig.inlinewaitsequence[idx + 1];
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
            var outputWindow = (ScriptOutput)sender;
            ScriptOutputManager.AppendToOutputWindowList(this);
        }

        private void Window_Closing(object sender, System.ComponentModel.CancelEventArgs e) {
            var outputWindow = (ScriptOutput)sender;

            ScriptOutputManager.RemoveFromOutputList(this);

            outputWindow.renderer.Navigating -= _navigateHandler;
            outputWindow._navigateHandler = null;
        }

        private void Window_Closed(object sender, System.EventArgs e) {
            var outputWindow = (ScriptOutput)sender;

            var grid = (Grid)outputWindow.Content;
            grid.Children.Remove(host);
            grid.Children.Clear();

            outputWindow.renderer.Dispose();
            outputWindow.renderer = null;

            outputWindow.host = null;
            outputWindow.Content = null;

            outputWindow.ClosedByUser = true;
        }

        private void Save_Contents_Button_Clicked(object sender, RoutedEventArgs e) {
            var head = ActiveDocument.GetElementsByTagName("head")[0];
            var fullHtml = ExternalConfig.doctype + head.OuterHtml + ActiveDocument.Body.OuterHtml;
            var saveDlg = new System.Windows.Forms.SaveFileDialog() {
                Title = "Save Output to:",
                Filter = "HTML|*.html"
            };
            saveDlg.ShowDialog();
            var f = File.CreateText(saveDlg.FileName);
            f.Write(fullHtml);
            f.Close();
        }

        public void Dispose() {
        }
    }
}
