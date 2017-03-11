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
        private readonly Queue<byte[]> _outputBuffer = new Queue<byte[]>();

        public ScriptOutputStream(ScriptOutput gui)
        {
            _gui = gui;
            _gui.FocusOutput();
        }


        public void write(string s)
        {
            Write(Encoding.ASCII.GetBytes(s), 0, s.Length);
            Flush();
        }


        public void WriteError(string error_msg)
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

                _gui.Write(error_msg.Replace("\n", "<br/>"), ExternalConfig.errordiv);
            }
        }


        /// Append the text in the buffer to gui.txtStdOut
        public override void Write(byte[] buffer, int offset, int count)
        {
            // Copy written data to new buffer and add to output queue
            byte[] data = new byte[count];
            Array.Copy(buffer, offset, data, 0, count);
            _outputBuffer.Enqueue(data);
        }


        public override void Flush()
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

                // pull everything out of the queue and create a string to be processed for html output
                byte[] curr;
                String text = String.Empty;
                while (_outputBuffer.Count > 0) {
                    curr = _outputBuffer.Dequeue();
                    text += Encoding.UTF8.GetString(curr);
                }

                // Cleanup output for html
                if (text.EndsWith("\n"))
                    text = text.Remove(text.Length - 1);
                text = text.Replace("<", "&lt;").Replace(">", "&gt;");
                text = text.Replace("&clt;", "<").Replace("&cgt;", ">");
                text = text.Replace("\n", "<br/>");
                text = text.Replace("\t", "&emsp;&emsp;");

                _gui.Write(text, ExternalConfig.defaultelement);
            }
        }


        public override long Seek(long offset, SeekOrigin origin)
        {
            throw new NotImplementedException();
        }


        public override void SetLength(long value)
        {
            throw new NotImplementedException();
        }


        public override int Read(byte[] buffer, int offset, int count)
        {
            throw new NotImplementedException();
        }


        public override bool CanRead
        {
            get { return false; }
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
            get { return _gui.txtStdOut.DocumentText.Length; }
            set {}
        }
    }
}
