using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;
using System.Windows.Forms;
using IronPython.Runtime.Exceptions;
using Microsoft.Scripting.Hosting;

namespace PyRevitBaseClasses
{
    /// A stream to write output to...
    /// This can be passed into the python interpreter to render all output to.
    /// Only a minimal subset is actually implemented - this is all we really expect to use.
    public class ScriptOutputStream: Stream
    {
        private readonly ScriptOutput _gui;
        private int _bomCharsLeft; // we want to get rid of pesky UTF8-BOM-Chars on write
        private readonly Queue<MemoryStream> _completedLines; // one memorystream per line of input
        private MemoryStream _inputBuffer;

        public ScriptOutputStream(ScriptOutput gui)
        {
            _gui = gui;
            _gui.txtStdOut.Focus();

            _completedLines = new Queue<MemoryStream>();
            _inputBuffer = new MemoryStream();
        }

        public void write(string s)
        {
            Write(Encoding.ASCII.GetBytes(s), 0, s.Length);
        }

        public void WriteError(string error_msg)
        {
            var err_div = _gui.txtStdOut.Document.CreateElement(ExternalConfig.errordiv);
            err_div.InnerHtml = error_msg.Replace("\n", "<br/>");

            var output_err_message = err_div.OuterHtml.Replace("<", "&clt;").Replace(">", "&cgt;");
            Write(Encoding.ASCII.GetBytes(output_err_message), 0, output_err_message.Length);
        }

        /// Append the text in the buffer to gui.txtStdOut
        public override void Write(byte[] buffer, int offset, int count)
        {
            lock (this)
            {
                if (_gui.IsDisposed)
                {
                    return;
                }

                if (!_gui.Visible)
                {
                    _gui.Show();
                }

                var actualBuffer = new byte[count];
                Array.Copy(buffer, offset, actualBuffer, 0, count);
                var text = Encoding.UTF8.GetString(actualBuffer);
                _gui.BeginInvoke((Action)delegate()
                {
                    // Cleanup output for html
                    var div = _gui.txtStdOut.Document.CreateElement(ExternalConfig.defaultelement);
                    if (text.EndsWith("\n"))
                        text = text.Remove(text.Length - 1);
                    text = text.Replace("<", "&lt;").Replace(">", "&gt;");
                    text = text.Replace("&clt;", "<").Replace("&cgt;", ">");
                    text = text.Replace("\n", "<br/>");
                    text = text.Replace("\t", "&emsp;&emsp;");
                    div.InnerHtml = text;
                    _gui.txtStdOut.Document.Body.AppendChild(div);
                });
                Application.DoEvents();
            }
        }

        public override void Flush()
        {
        }

        public override long Seek(long offset, SeekOrigin origin)
        {
            throw new NotImplementedException();
        }

        public override void SetLength(long value)
        {
            throw new NotImplementedException();
        }

        /// Read from the _inputBuffer, block until a new line has been entered...
        public override int Read(byte[] buffer, int offset, int count)
        {
            while (_completedLines.Count < 1)
            {
                if (_gui.Visible == false)
                {
                    throw new EndOfStreamException();
                }
                // wait for user to complete a line
                Application.DoEvents();
                Thread.Sleep(10);
            }
            var line = _completedLines.Dequeue();
            return line.Read(buffer, offset, count);
        }

        public override bool CanRead
        {
            get { return !_gui.IsDisposed; }
        }

        public override bool CanSeek
        {
            get { return false; }
        }

        public override bool CanWrite
        {
            get { return true; }
        }

        public override long Length
        {
            get { return _gui.txtStdOut.DocumentText.Length; }
        }

        public override long Position
        {
            get { return 0; }
            set { }
        }
    }
}
