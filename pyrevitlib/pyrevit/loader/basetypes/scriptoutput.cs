using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Markup;
using System.Windows.Media;
using System.Windows.Threading;
using Autodesk.Revit.UI;
using System.Text.RegularExpressions;

namespace PyRevitBaseClasses
{
    public partial class ScriptOutput : Window, IComponentConnector, IDisposable
    {
        private bool _contentLoaded;
        private bool _debugMode;
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

        public ScriptOutput(bool debugMode=false, UIApplication uiApp = null)
        {
            _debugMode = debugMode;
            _uiApp = uiApp;

            // setup unique id for this output window
            OutputUniqueId = Guid.NewGuid().ToString();

            InitializeComponent();
        }

        [System.Diagnostics.DebuggerNonUserCodeAttribute()]
        [System.CodeDom.Compiler.GeneratedCodeAttribute("PresentationBuildTasks", "4.0.0.0")]
        public void InitializeComponent()
        {
            if (_contentLoaded)
            {
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

            if (_debugMode)
            {
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

            // taskbar progress object
            var taskbarinfo = new System.Windows.Shell.TaskbarItemInfo();
            taskbarinfo.ProgressState = System.Windows.Shell.TaskbarItemProgressState.Normal;
            this.TaskbarItemInfo = taskbarinfo;

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
        void System.Windows.Markup.IComponentConnector.Connect(int connectionId, object target)
        {
            this._contentLoaded = true;
        }

        private void SetupDefaultPage(string styleSheetFilePath = null)
        {
            string cssFilePath;
            if (styleSheetFilePath != null)
                cssFilePath = styleSheetFilePath;
            else
                cssFilePath = GetStyleSheetFile();

            // create the head with default styling
            var dochead = String.Format(ExternalConfig.doctype, cssFilePath);
            // create default html
            renderer.DocumentText = String.Format("{0}<html><body></body></html>", dochead);

            while (renderer.Document.Body == null)
                System.Windows.Forms.Application.DoEvents();
        }

        private string GetStyleSheetFile()
        {
            var envDict = new EnvDictionary();
            return envDict.activeStyleSheet;
        }

        public void WaitReadyBrowser()
        {
            System.Windows.Forms.Application.DoEvents();
        }

        public void LockSize()
        {
            this.ResizeMode = ResizeMode.NoResize;
        }

        public void UnlockSize()
        {
            this.ResizeMode = ResizeMode.CanResizeWithGrip;
        }

        public void ScrollToBottom()
        {
            if (renderer.Document != null)
            {
                renderer.Document.Window.ScrollTo(0, renderer.Document.Body.ScrollRectangle.Height);
            }
        }

        public void FocusOutput()
        {
            renderer.Focus();
        }

        public System.Windows.Forms.HtmlElement ComposeEntry(String OutputText, String HtmlElementType)
        {
            WaitReadyBrowser();
            var div = renderer.Document.CreateElement(HtmlElementType);
            div.InnerHtml = OutputText;
            return div;
        }

        public void AppendText(String OutputText, String HtmlElementType)
        {
            WaitReadyBrowser();
            renderer.Document.Body.AppendChild(ComposeEntry(OutputText, HtmlElementType));
            ScrollToBottom();
        }

        private void renderer_Navigating(object sender, System.Windows.Forms.WebBrowserNavigatingEventArgs e)
        {
            if (!(e.Url.ToString().Equals("about:blank", StringComparison.InvariantCultureIgnoreCase)))
            {
                var inputUrl = e.Url.ToString();

                if (inputUrl.StartsWith("http") && !inputUrl.StartsWith("http://localhost"))
                {
                    System.Diagnostics.Process.Start(inputUrl);
                }
                else if (inputUrl.StartsWith("revit"))
                {
                    e.Cancel = true;
                    ScriptOutputHelpers.ProcessUrl(_uiApp, inputUrl);
                    return;
                }
                else if (inputUrl.StartsWith("file"))
                {
                    e.Cancel = false;
                    return;
                }

                e.Cancel = true;
            }
        }

        public void ShowProgressBar()
        {
            WaitReadyBrowser();
            if (renderer.Document != null)
            {
                var pbar = renderer.Document.CreateElement(ExternalConfig.progressindicator);
                var pbargraph = renderer.Document.CreateElement(ExternalConfig.progressbar);
                pbar.AppendChild(pbargraph);
                renderer.Document.Body.AppendChild(pbar);
            }
        }

        public void UpdateProgressBar(float curValue, float maxValue)
        {
            var progValue = (curValue / maxValue);
            this.TaskbarItemInfo.ProgressValue = progValue;

            if (this.ClosedByUser)
            {
                return;
            }

            WaitReadyBrowser();
            if (renderer.Document != null)
            {
                if (!this.IsVisible)
                {
                    try
                    {
                        this.Show();
                        this.Focus();
                    }
                    catch
                    {
                        return;
                    }
                }

                var pbargraph = renderer.Document.GetElementById(ExternalConfig.progressbarid);
                if (pbargraph == null)
                {
                    ShowProgressBar();
                    pbargraph = renderer.Document.GetElementById(ExternalConfig.progressbarid);
                }

                var newWidthStyleProperty = String.Format("width:{0}%;", progValue * 100);
                if (pbargraph.Style == null)
                    pbargraph.Style = newWidthStyleProperty;
                else
                    pbargraph.Style = Regex.Replace(pbargraph.Style, "width:.+?;", newWidthStyleProperty, RegexOptions.IgnoreCase);
            }
        }

        public void SelfDestructTimer(int seconds)
        {
            var dispatcherTimer = new DispatcherTimer();
            dispatcherTimer.Tick += (sender, e) => {
                var dt = (DispatcherTimer)sender;
                dt.Stop();
                Close();
                };
            dispatcherTimer.Interval = new TimeSpan(0, 0, seconds);
            dispatcherTimer.Start();
        }

        private void Window_Loaded(object sender, System.EventArgs e)
        {
            var outputWindow = (ScriptOutput)sender;
            ScriptOutputManager.AppendToOutputWindowList(this);
        }

        private void Window_Closing(object sender, System.ComponentModel.CancelEventArgs e)
        {
            var outputWindow = (ScriptOutput)sender;

            ScriptOutputManager.RemoveFromOutputList(this);

            outputWindow.renderer.Navigating -= _navigateHandler;
            outputWindow._navigateHandler = null;
        }

        private void Window_Closed(object sender, System.EventArgs e)
        {
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

        public void Dispose()
        {
        }
    }
}
