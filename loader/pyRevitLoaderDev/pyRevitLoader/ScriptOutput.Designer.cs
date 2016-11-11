namespace PyRevitLoader
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
            this.txtStdOut = new System.Windows.Forms.TextBox();
            this.SuspendLayout();
            // 
            // txtStdOut
            // 
            this.txtStdOut.BackColor = System.Drawing.Color.FromArgb(((int)(((byte)(223)))), ((int)(((byte)(219)))), ((int)(((byte)(195)))));
            this.txtStdOut.BorderStyle = System.Windows.Forms.BorderStyle.None;
            this.txtStdOut.Dock = System.Windows.Forms.DockStyle.Fill;
            this.txtStdOut.Font = new System.Drawing.Font("Courier New", 8F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.txtStdOut.ForeColor = System.Drawing.Color.FromArgb(((int)(((byte)(59)))), ((int)(((byte)(39)))), ((int)(((byte)(34)))));
            this.txtStdOut.Location = new System.Drawing.Point(0, 0);
            this.txtStdOut.Multiline = true;
            this.txtStdOut.Name = "txtStdOut";
            this.txtStdOut.ReadOnly = true;
            this.txtStdOut.ScrollBars = System.Windows.Forms.ScrollBars.Both;
            this.txtStdOut.Size = new System.Drawing.Size(884, 461);
            this.txtStdOut.TabIndex = 4;
            this.txtStdOut.WordWrap = false;
            this.txtStdOut.TextChanged += new System.EventHandler(this.txtStdOut_TextChanged);
            // 
            // ScriptOutput
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 13F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(884, 461);
            this.Controls.Add(this.txtStdOut);
            this.Name = "ScriptOutput";
            this.ShowIcon = false;
            this.StartPosition = System.Windows.Forms.FormStartPosition.Manual;
            this.Text = "pyRevit";
            this.Load += new System.EventHandler(this.ScriptOutput_Load);
            this.ResumeLayout(false);
            this.PerformLayout();

        }

        #endregion

        public System.Windows.Forms.TextBox txtStdOut;

    }
}