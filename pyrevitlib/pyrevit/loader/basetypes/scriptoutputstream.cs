using System;
using System.IO;
using System.Text;


namespace PyRevitBaseClasses
{
    /// A stream to write output to...
    /// This can be passed into the python interpreter to render all output to.
    /// Only a minimal subset is actually implemented - this is all we really expect to use.
    public class ScriptOutputStream: Stream, IDisposable
    {
        private WeakReference<PyRevitCommandRuntime> _pyrvtCmd;
        private WeakReference<ScriptOutput> _gui;
        private string _outputBuffer;
        private bool _errored = false;


        public ScriptOutputStream(PyRevitCommandRuntime pyrvtCmd)
        {
            _outputBuffer = String.Empty;
            _pyrvtCmd = new WeakReference<PyRevitCommandRuntime>(pyrvtCmd);
            _gui = new WeakReference<ScriptOutput>(null);
        }


        public ScriptOutputStream(ScriptOutput gui)
        {
            _outputBuffer = String.Empty;
            _pyrvtCmd = new WeakReference<PyRevitCommandRuntime>(null);
            _gui = new WeakReference<ScriptOutput>(gui);
        }


        private ScriptOutput GetOutput()
        {
            PyRevitCommandRuntime pyrvtCmd;
            var re = _pyrvtCmd.TryGetTarget(out pyrvtCmd);
            if (re && pyrvtCmd != null)
               return pyrvtCmd.OutputWindow;

            ScriptOutput output;
            re = _gui.TryGetTarget(out output);
            if (re && output != null)
                return output;

            return null;
        }


        // this is for python stream compatibility
        public void write(string s)
        {
            Write(Encoding.ASCII.GetBytes(s), 0, s.Length);
        }


        public void WriteError(string error_msg)
        {
            var output = GetOutput();
            if(output != null)
            {
                if (output.ClosedByUser)
                {
                    _gui = null;
                    _outputBuffer = String.Empty;
                    return;
                }

                _errored = true;
                var err_div = output.ComposeEntry(error_msg.Replace("\n", "<br/>"), ExternalConfig.errordiv);
                var output_err_message = err_div.OuterHtml.Replace("<", "&clt;").Replace(">", "&cgt;");
                Write(Encoding.ASCII.GetBytes(output_err_message), 0, output_err_message.Length);
            }
        }


        public override void Write(byte[] buffer, int offset, int count)
        {
            var output = GetOutput();
            if (output != null)
            {
                if(output.ClosedByUser)
                {
                    _gui = null;
                    _outputBuffer = String.Empty;
                    return;
                }

                if (!output.IsVisible)
                {
                    try
                    {
                        output.Show();
                        output.Focus();
                    }
                    catch
                    {
                        return;
                    }
                }

                lock (this)
                {

                    var actualBuffer = new byte[count];
                    Array.Copy(buffer, offset, actualBuffer, 0, count);
                    var text = Encoding.UTF8.GetString(actualBuffer);

                    // append output to the buffer
                    _outputBuffer += text;

                    if (count < 1024)
                    {
                        // Cleanup output for html
                        if (_outputBuffer.EndsWith("\n"))
                            _outputBuffer = _outputBuffer.Remove(_outputBuffer.Length - 1);
                        _outputBuffer = _outputBuffer.Replace("<", "&lt;").Replace(">", "&gt;");
                        _outputBuffer = _outputBuffer.Replace("&clt;", "<").Replace("&cgt;", ">");
                        _outputBuffer = _outputBuffer.Replace("\n", "<br/>");
                        _outputBuffer = _outputBuffer.Replace("\t", "&emsp;&emsp;");

                        // write to output window
                        if (!_errored)
                            output.AppendText(_outputBuffer, ExternalConfig.defaultelement);
                        else
                            output.AppendError(_outputBuffer, ExternalConfig.defaultelement);

                        // reset buffer and flush state for next time
                        _outputBuffer = String.Empty;
                    }
                }
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
            get { return 0; }
        }


        public override long Position
        {
            get { return 0; }
            set { }
        }


        new public void Dispose()
        {
            _pyrvtCmd = null;
            _gui = null;
            Dispose(true);
        }
    }
}
