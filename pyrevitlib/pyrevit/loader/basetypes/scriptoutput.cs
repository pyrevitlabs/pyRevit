using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Markup;
using System.Windows.Media;
using System.Windows.Threading;
using Autodesk.Revit.UI;
using System.Text.RegularExpressions;
using System.Diagnostics;

using MahApps.Metro;
using MahApps.Metro.Controls;

using pyRevitLabs.CommonWPF;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.Common.Extensions;
using System.IO;

namespace PyRevitBaseClasses {
    public partial class ScriptOutput : pyRevitLabs.CommonWPF.Windows.AppWindow, IComponentConnector, IDisposable {
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
        System.Windows.Forms.Integration.WindowsFormsHost host;
        public System.Windows.Forms.WebBrowser renderer;
        public System.Windows.Forms.WebBrowserNavigatingEventHandler _navigateHandler;

        public ScriptOutput(bool debugMode = false, UIApplication uiApp = null) {
            _debugMode = debugMode;
            _uiApp = uiApp;

            // setup unique id for this output window
            OutputUniqueId = Guid.NewGuid().ToString();

            //// setup window styles
            SetupWindowStyleResources();

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

            // Create the WebBrowser control.
            renderer = new System.Windows.Forms.WebBrowser();

            _navigateHandler = new System.Windows.Forms.WebBrowserNavigatingEventHandler(renderer_Navigating);
            renderer.Navigating += _navigateHandler;

            // setup the default html page
            SetupDefaultPage();

            // Assign the WebBrowser control as the host control's child.
            host.Child = renderer;

            // Add the interop host control to the Grid
            // control's collection of child controls.
            Grid baseGrid = new Grid();

            if (_debugMode) {
                var rendererRow = new RowDefinition();
                var splitterRow = new RowDefinition();
                var replRow = new RowDefinition();

                splitterRow.Height = new GridLength(6);
                replRow.Height = new GridLength(100);

                baseGrid.RowDefinitions.Add(rendererRow);
                baseGrid.RowDefinitions.Add(splitterRow);
                baseGrid.RowDefinitions.Add(replRow);

                var splitter = new GridSplitter();
                splitter.ResizeDirection = GridResizeDirection.Rows;
                splitter.HorizontalAlignment = HorizontalAlignment.Stretch;
                splitter.Background = Brushes.LightGray;

                var repl = new REPLControl();

                Grid.SetRow(host, 0);
                Grid.SetRow(splitter, 1);
                Grid.SetRow(repl, 2);

                baseGrid.Children.Add(splitter);
                baseGrid.Children.Add(repl);
            }

            baseGrid.Children.Add(host);
            this.Content = baseGrid;

            // TODO: add report button, get email from envvars
            // setup header buttons
            // setting up user name and app version buttons
            var envDict = new EnvDictionary();
            // TODO: add report button, get email from envvars
            var saveButton = new Button() { Content = "Save Contents" };
            saveButton.Click += Save_Contents_Button_Clicked;

            var userNameButton = new Button() { Content = CurrentUser };
            userNameButton.Click += Copy_Button_Title;

            var versionButton = new Button() { Content = envDict.pyRevitVersion };
            versionButton.Click += Copy_Button_Title;

            var winButtons = new WindowCommands() { Items = { saveButton, userNameButton, versionButton } };
            RightWindowCommands = winButtons;

            // Setup window styles
            this.Background = Brushes.White;
            this.Width = 900;
            this.Height = 600;
            this.WindowStartupLocation = WindowStartupLocation.Manual;
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

        private void SetupWindowStyleResources() {
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
            var accentOverride = new SolidColorBrush() { Color = Color.FromArgb(0xFF, 0x2c, 0x3e, 0x50) };
            accentResDict["AccentColorBrush"] = accentOverride;
            accentResDict["WindowTitleColorBrush"] = accentOverride;
            Resources.MergedDictionaries.Add(accentResDict);

            WindowTransitionsEnabled = false;
        }

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
            var dochead = string.Format(ExternalConfig.doctype + ExternalConfig.dochead, cssFilePath);
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

        public System.Windows.Forms.HtmlElement ComposeEntry(String OutputText, String HtmlElementType) {
            WaitReadyBrowser();
            var div = ActiveDocument.CreateElement(HtmlElementType);
            div.InnerHtml = OutputText;
            return div;
        }

        public void AppendText(String OutputText, String HtmlElementType) {
            if (!_frozen) {
                WaitReadyBrowser();
                ActiveDocument.Body.AppendChild(ComposeEntry(OutputText, HtmlElementType));
                ScrollToBottom();
            }
            else if (_lastDocumentBody != null) {
                _lastDocumentBody.AppendChild(ComposeEntry(OutputText, HtmlElementType));
            }
        }

        public void AppendError(String OutputText, String HtmlElementType) {
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

        public void UpdateProgressBar(float curValue, float maxValue) {
            if (this.ClosedByUser) {
                return;
            }

            if (this.TaskbarItemInfo == null) {
                // taskbar progress object
                var taskbarinfo = new System.Windows.Shell.TaskbarItemInfo();
                taskbarinfo.ProgressState = System.Windows.Shell.TaskbarItemProgressState.Normal;
                this.TaskbarItemInfo = taskbarinfo;
            }

            var progValue = (curValue / maxValue);
            this.TaskbarItemInfo.ProgressValue = progValue;

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

                var newWidthStyleProperty = string.Format("width:{0}%;", progValue * 100);
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

        private void Copy_Button_Title(object sender, RoutedEventArgs e) {
            var button = e.Source as Button;
            Clipboard.SetText(button.Content.ToString());
        }

        private void Save_Contents_Button_Clicked(object sender, RoutedEventArgs e) {
            var head = ActiveDocument.GetElementsByTagName("head")[0].OuterHtml;
            var fullHtml = ExternalConfig.doctype + head + ActiveDocument.Body.OuterHtml;
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
