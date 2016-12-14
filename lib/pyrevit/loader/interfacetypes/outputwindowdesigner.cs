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
            this.txtStdOut = new System.Windows.Forms.WebBrowser();
            this.SuspendLayout();
            // 
            // txtStdOut
            // 
            this.txtStdOut.AllowWebBrowserDrop = false;
            this.txtStdOut.Dock = System.Windows.Forms.DockStyle.Fill;
            this.txtStdOut.Location = new System.Drawing.Point(3, 3);
            this.txtStdOut.Margin = new System.Windows.Forms.Padding(0);
            this.txtStdOut.MinimumSize = new System.Drawing.Size(27, 25);
            this.txtStdOut.Name = "txtStdOut";
            this.txtStdOut.Size = new System.Drawing.Size(878, 455);
            this.txtStdOut.TabIndex = 0;
            this.txtStdOut.Navigating += new System.Windows.Forms.WebBrowserNavigatingEventHandler(this.txtStdOut_Navigating);
            // 
            // ScriptOutput
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(8F, 16F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.BackColor = System.Drawing.Color.White;
            this.ClientSize = new System.Drawing.Size(884, 461);
            this.Controls.Add(this.txtStdOut);
            this.Font = new System.Drawing.Font("Verdana", 9.75F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.Margin = new System.Windows.Forms.Padding(4);
            this.Name = "ScriptOutput";
            this.Padding = new System.Windows.Forms.Padding(3);
            this.ShowIcon = false;
            this.StartPosition = System.Windows.Forms.FormStartPosition.Manual;
            this.Text = "pyRevit";
            this.Load += new System.EventHandler(this.ScriptOutput_Load);
            this.ResumeLayout(false);

        }

        #endregion

        public System.Windows.Forms.WebBrowser txtStdOut;


    }
}