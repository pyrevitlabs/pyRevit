using System;
using System.Windows.Forms;
using System.Collections.Generic;


namespace PyRevitBaseClasses
{
    public partial class ScriptOutput : Form
    {
        public delegate void CustomProtocolHandler(String url);
        public CustomProtocolHandler UrlHandler;
        public string OutputId;

        public ScriptOutput() {
            Application.EnableVisualStyles();
            InitializeComponent();
            renderer.DocumentText = String.Format("{0}<html><body></body></html>", ExternalConfig.doctype);

            // Let's leave the WebBrowser control working alone.
            while (renderer.Document.Body == null)
            {
                Application.DoEvents();
            }

            renderer.Document.Body.Style = ExternalConfig.htmlstyle;

        }

        private void ScriptOutput_Load(object sender, EventArgs e) {}

        public void AppendToOutputList(object sender, EventArgs e)
        {
            var outputList = (List<object>) AppDomain.CurrentDomain.GetData(EnvDictionaryKeys.outputWindows);
            if (outputList == null) {
                var newOutputList = new List<object>();
                newOutputList.Add(this);

                AppDomain.CurrentDomain.SetData(EnvDictionaryKeys.outputWindows, newOutputList);
            }
            else
            {
                outputList.Add(this);
            }
        }

        public void RemoveFromOutputList(object sender, FormClosingEventArgs e)
        {
            var outputList = (List<object>) AppDomain.CurrentDomain.GetData(EnvDictionaryKeys.outputWindows);
            if (outputList == null) {
                return;
            }
            else
            {
                if (outputList.Contains(this))
                {
                    outputList.Remove(this);
                }
            }
        }

        public void WaitReadyBrowser() {
               Application.DoEvents();
        }

        public void LockSize() {
            this.MaximizeBox = false;
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
        }

        public void ScrollToBottom() {
            if (renderer.Document != null)
            {
                renderer.Document.Window.ScrollTo(0, renderer.Document.Body.ScrollRectangle.Height);
            }
        }

        public void FocusOutput() {
            renderer.Focus();
        }

        public void AppendText(String OutputText, String HtmlElementType) {
            WaitReadyBrowser();
            var div = renderer.Document.CreateElement(HtmlElementType);
            div.InnerHtml = OutputText;
            renderer.Document.Body.AppendChild(div);
            ScrollToBottom();
        }

        private void UserNavigatingLink(object sender, WebBrowserNavigatingEventArgs e) {
            if (!(e.Url.ToString().Equals("about:blank", StringComparison.InvariantCultureIgnoreCase)))
            {
                var commandStr = e.Url.ToString();
                if (commandStr.StartsWith("http")) {
                    System.Diagnostics.Process.Start(e.Url.ToString());
                }
                else
                    UrlHandler(e.Url.OriginalString);

                e.Cancel = true;
            }
        }

        public void ShowProgressBar() {
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

        public void UpdateProgressBar(float curValue, float maxValue) {
            WaitReadyBrowser();
            if (renderer.Document != null)
            {
                HtmlElement pbargraph;
                pbargraph = renderer.Document.GetElementById(ExternalConfig.progressbargraphid);
                if (pbargraph == null) {
                    ShowProgressBar();
                    pbargraph = renderer.Document.GetElementById(ExternalConfig.progressbargraphid);
                }
                pbargraph.Style = String.Format(ExternalConfig.progressbargraphstyle, (curValue/maxValue)*100);
            }
        }

        public void SelfDestructTimer(int miliseconds) {
            // Create a 30 min timer
            var timer = new System.Timers.Timer(miliseconds);
            // Hook up the Elapsed event for the timer.
            timer.Elapsed += (sender, e) => SelfDestructTimerEvent(sender, e, this);
            timer.Enabled = true;
        }

        private static void SelfDestructTimerEvent(object source, System.Timers.ElapsedEventArgs e, ScriptOutput output_window) {
            output_window.Close();
        }
    }
}
