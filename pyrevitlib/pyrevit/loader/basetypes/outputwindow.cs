using System;
using System.Windows.Forms;
using System.Collections.Generic;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace PyRevitBaseClasses
{
    public partial class ScriptOutput : System.Windows.Forms.Form
    {
        private readonly UIApplication _revit;
        public delegate int CustomProtocolHandler(String url);
        public CustomProtocolHandler UrlHandler;

        public ScriptOutput(UIApplication uiApplication)
        {
            _revit = uiApplication;

            Application.EnableVisualStyles();
            InitializeComponent();
            txtStdOut.DocumentText = "<html><body></body></html>";

            // Let's leave the WebBrowser control working alone.
            while (txtStdOut.Document.Body == null)
            {
                Application.DoEvents();
            }

            txtStdOut.Document.Body.Style = ExternalConfig.htmlstyle;
        }

        private void ScriptOutput_Load(object sender, EventArgs e)
        {

        }


        private void txtStdOut_Navigating(object sender, WebBrowserNavigatingEventArgs e)
        {
            if (!(e.Url.ToString().Equals("about:blank", StringComparison.InvariantCultureIgnoreCase)))
            {
                var commandStr = e.Url.ToString();
                if (commandStr.StartsWith("http")) {
                    System.Diagnostics.Process.Start(e.Url.ToString());
                }
                else if (commandStr.StartsWith("id")){
                    UrlHandler(commandStr);
                }

                e.Cancel = true;
            }
        }
    }
}
