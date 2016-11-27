using System;
using System.Windows.Forms;

namespace PyRevitLoader
{
    public partial class ScriptOutput : Form
    {
        public ScriptOutput()
        {
            Application.EnableVisualStyles();
            InitializeComponent();
            txtStdOut.DocumentText = "<html><body></body></html>";

            // Let's leave the WebBrowser control working alone.
            while (txtStdOut.Document.Body == null)
            {
                Application.DoEvents();
            }

            var style = PyRevitLoaderApplication.ExtractDLLConfigParameter("htmlstyle");
            txtStdOut.Document.Body.Style = style;
        }

        private void ScriptOutput_Load(object sender, EventArgs e)
        {

        }


        private void txtStdOut_Navigating(object sender, WebBrowserNavigatingEventArgs e)
        {
            if (!(e.Url.ToString().Equals("about:blank", StringComparison.InvariantCultureIgnoreCase)))
            {
                System.Diagnostics.Process.Start(e.Url.ToString());
                e.Cancel = true;
            }
        }
    }
}
