using System.Windows.Forms;

namespace PyRevitBaseClasses
{
    partial class ScriptOutput
    {
        private System.ComponentModel.IContainer components = null;

        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        private void InitializeComponent()
        {
            this.renderer = new WebBrowser();
            this.SuspendLayout();
            //
            // renderer
            //
            this.renderer.AllowWebBrowserDrop = false;
            this.renderer.Dock = DockStyle.Fill;
            this.renderer.Location = new System.Drawing.Point(0, 0);
            this.renderer.Margin = new Padding(0);
            this.renderer.MinimumSize = new System.Drawing.Size(27, 25);
            this.renderer.Name = "renderer";
            this.renderer.Size = new System.Drawing.Size(878, 455);
            this.renderer.TabIndex = 0;

            //
            // ScriptOutput
            //
            this.AutoScaleDimensions = new System.Drawing.SizeF(8F, 16F);
            this.AutoScaleMode = AutoScaleMode.Font;
            this.BackColor = System.Drawing.Color.White;
            this.ClientSize = new System.Drawing.Size(900, 600);

            this.Font = new System.Drawing.Font("Verdana",
                                                9.75F,
                                                System.Drawing.FontStyle.Regular,
                                                System.Drawing.GraphicsUnit.Point,
                                                ((byte)(0)));
            this.Margin = new Padding(0);
            this.Name = "ScriptOutput";
            this.Padding = new Padding(0);
            this.ShowIcon = false;
            this.StartPosition = FormStartPosition.Manual;
            this.Text = "pyRevit";

            // this.Load += new System.EventHandler(this.ScriptOutput_Load);
            this.Shown += new System.EventHandler(this.OnFormShown);
            this.FormClosing += new FormClosingEventHandler(this.OnFormClosing);
            this.FormClosed += new FormClosedEventHandler(this.OnFormClosed);

            this.Controls.Add(this.renderer);

            this.ResumeLayout(false);
            this.PerformLayout();
        }

        public WebBrowser renderer;
    }
}
