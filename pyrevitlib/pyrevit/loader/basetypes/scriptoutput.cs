using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Markup;
using System.Windows.Media;
using System.Windows.Threading;


namespace PyRevitBaseClasses
{
    public partial class ScriptOutput : Window, IComponentConnector, IDisposable
    {
        private bool _contentLoaded;
        private bool _debugMode;

        public string OutputUniqueId;
        public string OutputId;
        public bool ClosedByUser = false;

        System.Windows.Forms.Integration.WindowsFormsHost host;
        public System.Windows.Forms.WebBrowser renderer;

        public System.Windows.Forms.WebBrowserNavigatingEventHandler _navigateHandler;

        public ScriptOutput(bool debugMode=false)
        {
            _debugMode = debugMode;
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

            renderer.DocumentText = String.Format("{0}<html><body></body></html>", ExternalConfig.doctype);
            while (renderer.Document.Body == null)
                System.Windows.Forms.Application.DoEvents();

            // Setup body style
            renderer.Document.Body.Style = ExternalConfig.htmlstyle;

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
                var commandStr = e.Url.ToString();
                if (commandStr.StartsWith("http") && !commandStr.StartsWith("http://localhost"))
                {
                    System.Diagnostics.Process.Start(e.Url.ToString());
                }
                else if (commandStr.StartsWith("file"))
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
                var pbar = renderer.Document.CreateElement(ExternalConfig.progressbar);
                var pbargraph = renderer.Document.CreateElement("div");
                pbargraph.Id = ExternalConfig.progressbargraphid;
                pbargraph.Style = String.Format(ExternalConfig.progressbargraphstyle, 10);
                pbar.AppendChild(pbargraph);
                renderer.Document.Body.AppendChild(pbar);
            }
        }

        public void UpdateProgressBar(float curValue, float maxValue)
        {
            if(this.ClosedByUser)
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

                var pbargraph = renderer.Document.GetElementById(ExternalConfig.progressbargraphid);
                if (pbargraph == null)
                {
                    ShowProgressBar();
                    pbargraph = renderer.Document.GetElementById(ExternalConfig.progressbargraphid);
                }
                pbargraph.Style = String.Format(ExternalConfig.progressbargraphstyle, (curValue / maxValue) * 100);
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
            ScriptOutputManager.AppendToOutputList(this);
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
