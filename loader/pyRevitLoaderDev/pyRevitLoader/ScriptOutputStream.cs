using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;
using System.Windows.Forms;
using IronPython.Runtime.Exceptions;
using Microsoft.Scripting.Hosting;

namespace PyRevitLoader
{
    /// <summary>
    /// A stream to write output to...
    /// This can be passed into the python interpreter to render all output to.
    /// Only a minimal subset is actually implemented - this is all we really
    /// expect to use.
    /// </summary>
    public class ScriptOutputStream: Stream
    {
        private readonly ScriptOutput _gui;
        private readonly ScriptEngine _engine;
        private int _bomCharsLeft; // we want to get rid of pesky UTF8-BOM-Chars on write
        private readonly Queue<MemoryStream> _completedLines; // one memorystream per line of input
        private MemoryStream _inputBuffer;

        public ScriptOutputStream(ScriptOutput gui, ScriptEngine engine)
        {
            _gui = gui;
            _engine = engine;
            _gui.txtStdOut.KeyPress += KeyPressEventHandler;
            _gui.txtStdOut.KeyDown += KeyDownEventHandler;
            //_gui.Closing += ClosingEventHandler;
            //_gui.Closed += ClosedEventHandler;

            _gui.txtStdOut.Focus();

            _completedLines = new Queue<MemoryStream>();
            _inputBuffer = new MemoryStream();

            _bomCharsLeft = 3; //0xef, 0xbb, 0xbf for UTF-8 (see http://en.wikipedia.org/wiki/Byte_order_mark#Representations_of_byte_order_marks_by_encoding)
        }

        void ClosedEventHandler(object sender, EventArgs e)
        {
            _engine.Runtime.Shutdown();
            _completedLines.Enqueue(new MemoryStream());
        }

        /// <summary>
        /// Terminate reading from STDIN.
        /// FIXME: this doesn't work!
        /// </summary>
        private void ClosingEventHandler(object sender, System.ComponentModel.CancelEventArgs e)
        {        
            _engine.Runtime.Shutdown();            
            _completedLines.Enqueue(new MemoryStream());
        }

        /// <summary>
        /// Complete a line when the enter key is pressed. Also
        /// try to emulate a nice control window. This is going to be a big gigantic pile
        /// of ifs, sigh.
        /// </summary>
        void KeyDownEventHandler(object sender, KeyEventArgs e)
        {
            if (e.KeyCode == Keys.Enter || e.KeyCode == Keys.Return)
            {
                var line = _inputBuffer;
                var newLine = new byte[] {/*0x0d,*/ 0x0a};
                line.Write(newLine, 0, newLine.Length); // append new-line
                line.Seek(0, SeekOrigin.Begin); // rewind the line for later reading...
                _completedLines.Enqueue(line);
                _inputBuffer = new MemoryStream();
            }            
            else if (e.KeyCode == Keys.Back || e.KeyCode == Keys.Left)
            {
                // remove last character from input buffer
                if (_inputBuffer.Position > 0)
                {
                    var line = new MemoryStream();
                    line.Write(_inputBuffer.GetBuffer(), 0, (int)(_inputBuffer.Position - 1));
                    _inputBuffer = line;
                    _gui.txtStdOut.Text = _gui.txtStdOut.Text.Substring(0, _gui.txtStdOut.Text.Length - 1);
                    _gui.txtStdOut.SelectionStart = _gui.txtStdOut.Text.Length;
                    _gui.txtStdOut.ScrollToCaret();
                }                
                // do not pass backspace / left on to txtStdOut
                e.Handled = true;                
            }
            else if (e.KeyCode == Keys.Right)
            {                
                // do not move right ever...
                e.Handled = true;
            }
        }

        /// <summary>
        /// Stash away any printable characters for later...
        /// </summary>
        void KeyPressEventHandler(object sender, KeyPressEventArgs e)
        {
            if (!char.IsControl(e.KeyChar))
            {
                var bytes = Encoding.UTF8.GetBytes(new[] {e.KeyChar});
                _inputBuffer.Write(bytes, 0, bytes.Length);
                _gui.txtStdOut.Focus();
            }            
            else
            {
                if (e.KeyChar == '\r')
                {
                    // user pressed enter
                    _gui.txtStdOut.Text += "\r\n";
                    _gui.txtStdOut.SelectionStart = _gui.txtStdOut.Text.Length;
                    _gui.txtStdOut.Focus();
                }
                // pretend we have handled this key (so using arrows does not confuse the user)
                e.Handled = true;
            }
        }



        /// <summary>
        /// Append the text in the buffer to gui.txtStdOut
        /// </summary>
        public override void Write(byte[] buffer, int offset, int count)
        {
            lock (this)
            {
                if (_gui.IsDisposed)
                {
                    return;
                }

                while (_bomCharsLeft > 0 && count > 0)
                {
                    _bomCharsLeft--;
                    count--;
                    offset++;
                }

                var actualBuffer = new byte[count];
                Array.Copy(buffer, offset, actualBuffer, 0, count);
                var text = Encoding.UTF8.GetString(actualBuffer);
                Debug.WriteLine(text);
                _gui.BeginInvoke((Action)delegate()
                {
                    _gui.txtStdOut.AppendText(text);
                    _gui.txtStdOut.SelectionStart = _gui.txtStdOut.Text.Length;
                    _gui.txtStdOut.ScrollToCaret();
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

        /// <summary>
        /// Read from the _inputBuffer, block until a new line has been entered...
        /// </summary>
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
            get { return _gui.txtStdOut.Text.Length; }
        }

        public override long Position
        {
            get { return 0; }
            set { }
        }
    }
}