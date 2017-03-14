using System;
using System.Windows.Forms;
using System.Collections.Generic;
using System.Threading;

namespace PyRevitBaseClasses
{
    public partial class ScriptOutput : Form
    {
        public delegate void CustomProtocolHandler(String url);
        public CustomProtocolHandler UrlHandler;

        public ScriptOutput()
        {
            Application.EnableVisualStyles();
            InitializeComponent();
            txtStdOut.DocumentText = String.Format("{0}<html><body></body></html>", ExternalConfig.doctype);

            // Let's leave the WebBrowser control working alone.
            while (txtStdOut.Document.Body == null)
            {
                Application.DoEvents();
            }

            txtStdOut.Document.Body.Style = ExternalConfig.htmlstyle;

        }

        private void ScriptOutput_Load(object sender, EventArgs e) {}

        public void WaitReadyBrowser() {
            // while(txtStdOut.ReadyState != WebBrowserReadyState.Complete)
            // {
               Application.DoEvents();
            // }
        }

        public void ScrollToBottom()
        {
            if (txtStdOut.Document != null)
            {
                txtStdOut.Document.Window.ScrollTo(0, txtStdOut.Document.Body.ScrollRectangle.Height);
            }
        }

        public void FocusOutput()
        {
            txtStdOut.Focus();
        }

        public void AppendText(String OutputText, String HtmlElementType)
        {
            WaitReadyBrowser();
            var div = txtStdOut.Document.CreateElement(HtmlElementType);
            div.InnerHtml = OutputText;
            txtStdOut.Document.Body.AppendChild(div);
            ScrollToBottom();
        }

        private void txtStdOut_Navigating(object sender, WebBrowserNavigatingEventArgs e)
        {
            if (!(e.Url.ToString().Equals("about:blank", StringComparison.InvariantCultureIgnoreCase)))
            {
                var commandStr = e.Url.ToString();
                if (commandStr.StartsWith("http")) {
                    System.Diagnostics.Process.Start(e.Url.ToString());
                }
                else {
                    UrlHandler(e.Url.OriginalString);
                }

                e.Cancel = true;
            }
        }

        public void ShowProgressBar()
        {
            WaitReadyBrowser();
            if (txtStdOut.Document != null)
            {
                var pbar = txtStdOut.Document.CreateElement(ExternalConfig.progressbar);
                var pbargraph = txtStdOut.Document.CreateElement("div");
                pbargraph.Id = ExternalConfig.progressbargraphid;
                pbargraph.Style = String.Format(ExternalConfig.progressbargraphstyle, 10);
                pbar.AppendChild(pbargraph);
                txtStdOut.Document.Body.AppendChild(pbar);
            }
        }

        public void UpdateProgressBar(float curValue, float maxValue)
        {
            WaitReadyBrowser();
            if (txtStdOut.Document != null)
            {
                HtmlElement pbargraph;
                pbargraph = txtStdOut.Document.GetElementById(ExternalConfig.progressbargraphid);
                if (pbargraph == null) {
                    ShowProgressBar();
                    pbargraph = txtStdOut.Document.GetElementById(ExternalConfig.progressbargraphid);
                }
                pbargraph.Style = String.Format(ExternalConfig.progressbargraphstyle, (curValue/maxValue)*100);
            }
        }

        public void SelfDestructTimer(int miliseconds)
        {
            // Create a 30 min timer
            var timer = new System.Timers.Timer(miliseconds);
            // Hook up the Elapsed event for the timer.
            timer.Elapsed += (sender, e) => SelfDestructTimerEvent(sender, e, this);
            timer.Enabled = true;
        }

        private static void SelfDestructTimerEvent(object source, System.Timers.ElapsedEventArgs e, ScriptOutput output_window)
        {
            output_window.Close();
        }
    }
}
