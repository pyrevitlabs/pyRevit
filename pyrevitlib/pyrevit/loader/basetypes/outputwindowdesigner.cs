using System.Windows.Forms;

namespace PyRevitBaseClasses
{
    partial class ScriptOutput
    {
        /// <summary>
        /// Required designer variable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// Clean up any resources being used.
        /// </summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        /// <summary>
        /// Required method for Designer support - do not modify
        /// the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent()
        {
            this.renderer = new System.Windows.Forms.WebBrowser();
            this.SuspendLayout();
            //
            // renderer
            //
            this.renderer.AllowWebBrowserDrop = false;
            this.renderer.Dock = System.Windows.Forms.DockStyle.Fill;
            this.renderer.Location = new System.Drawing.Point(0, 0);
            this.renderer.Margin = new System.Windows.Forms.Padding(0);
            this.renderer.MinimumSize = new System.Drawing.Size(27, 25);
            this.renderer.Name = "renderer";
            this.renderer.Size = new System.Drawing.Size(878, 455);
            this.renderer.TabIndex = 0;
            this.renderer.Navigating += new System.Windows.Forms.WebBrowserNavigatingEventHandler(this.txtStdOut_Navigating);
            //
            // ScriptOutput
            //
            this.AutoScaleDimensions = new System.Drawing.SizeF(8F, 16F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.BackColor = System.Drawing.Color.White;
            this.ClientSize = new System.Drawing.Size(900, 600);
            this.Controls.Add(this.renderer);
            this.Font = new System.Drawing.Font("Verdana", 9.75F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.Margin = new System.Windows.Forms.Padding(0);
            this.Name = "ScriptOutput";
            this.Padding = new System.Windows.Forms.Padding(0);
            this.ShowIcon = false;
            this.StartPosition = System.Windows.Forms.FormStartPosition.Manual;
            this.Text = "pyRevit";

            // this.Load += new System.EventHandler(this.ScriptOutput_Load);
            this.Shown += new System.EventHandler(this.AppendToOutputList);
            this.FormClosing += new System.Windows.Forms.FormClosingEventHandler(this.RemoveFromOutputList);

            this.ResumeLayout(false);
        }

        #endregion

        public System.Windows.Forms.WebBrowser renderer;


    }
}
