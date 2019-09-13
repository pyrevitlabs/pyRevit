using System;
using System.IO;
using System.Text;

using pyRevitLabs.Common.Extensions;

namespace PyRevitLabs.PyRevit.Runtime {
    /// A stream to write output to...
    /// This can be passed into the python interpreter to render all output to.
    /// Only a minimal subset is actually implemented - this is all we really expect to use.
    public class ScriptIO : Stream, IDisposable {
        private WeakReference<ScriptRuntime> _runtime;
        private WeakReference<ScriptConsole> _gui;
        private string _outputBuffer;
        private bool _errored = false;
        private ScriptEngineType _erroredEngine;

        public bool PrintDebugInfo = false;

        public ScriptIO(ScriptRuntime runtime) {
            _outputBuffer = string.Empty;
            _runtime = new WeakReference<ScriptRuntime>(runtime);
            _gui = new WeakReference<ScriptConsole>(null);
        }

        public ScriptIO(ScriptConsole gui) {
            _outputBuffer = string.Empty;
            _runtime = new WeakReference<ScriptRuntime>(null);
            _gui = new WeakReference<ScriptConsole>(gui);
        }

        public ScriptConsole GetOutput() {
            ScriptRuntime runtime;
            var re = _runtime.TryGetTarget(out runtime);
            if (re && runtime != null)
                return runtime.OutputWindow;

            ScriptConsole output;
            re = _gui.TryGetTarget(out output);
            if (re && output != null)
                return output;

            return null;
        }

        public Encoding OutputEncoding {
            get {
                return Encoding.UTF8;
            }
        }

        // this is for python stream compatibility
        public void write(string content) {
            var buffer = OutputEncoding.GetBytes(content);
            Write(buffer, 0, buffer.Length);
        }

        public void WriteError(string error_msg, ScriptEngineType engineType) {
            _errored = true;
            _erroredEngine = engineType;
            foreach (string message_part in error_msg.SplitIntoChunks(1024)) {
                var buffer = OutputEncoding.GetBytes(message_part);
                Write(buffer, 0, buffer.Length);
            }
        }

        public override void Write(byte[] buffer, int offset, int count) {
            var output = GetOutput();
            if (output != null) {
                if (output.ClosedByUser) {
                    _gui = null;
                    _outputBuffer = string.Empty;
                    return;
                }

                if (!output.IsVisible) {
                    try {
                        output.Show();
                        output.Focus();
                    }
                    catch {
                        return;
                    }
                }

                lock (this) {

                    var tempBuffer = new byte[count];
                    Array.Copy(buffer, offset, tempBuffer, 0, count);
                    var outputText = OutputEncoding.GetString(tempBuffer);

                    // append output to the buffer
                    _outputBuffer += outputText;

                    // log buffer information in debug mode
                    if (PrintDebugInfo)
                        output.AppendText(
                            string.Format("<---- Offset: {0}, Count: {1} ---->", offset, count),
                            ScriptConsoleConfigs.DefaultBlock);

                    if (count < 1024) {
                        // write to output window
                        if (!_errored)
                            output.AppendText(_outputBuffer, ScriptConsoleConfigs.DefaultBlock);
                        else
                            output.AppendError(_outputBuffer, _erroredEngine);

                        // reset buffer and flush state for next time
                        _outputBuffer = string.Empty;
                    }
                }
            }
        }

        public override void Flush() {
        }

        public override long Seek(long offset, SeekOrigin origin) {
            throw new NotImplementedException();
        }

        public override void SetLength(long value) {
            throw new NotImplementedException();
        }

        public override int Read(byte[] buffer, int offset, int count) {
            throw new NotImplementedException();
        }

        public override bool CanRead {
            get { return false; }
        }

        public override bool CanSeek {
            get { return false; }
        }

        public override bool CanWrite {
            get { return true; }
        }

        public override long Length {
            get { return 0; }
        }

        public override long Position {
            get { return 0; }
            set { }
        }

        new public void Dispose() {
            _runtime = null;
            _gui = null;
            Dispose(true);
        }
    }
}
