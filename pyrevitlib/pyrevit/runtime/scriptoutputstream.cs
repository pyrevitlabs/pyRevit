using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

using pyRevitLabs.Common.Extensions;

namespace PyRevitLabs.PyRevit.Runtime {
    /// A stream to write output to...
    /// This can be passed into the python interpreter to render all output to.
    /// Only a minimal subset is actually implemented - this is all we really expect to use.
    public class ScriptOutputStream : Stream, IDisposable {
        private WeakReference<ScriptRuntime> _pyrvtScript;
        private WeakReference<ScriptOutput> _gui;
        private string _outputBuffer;
        private bool _errored = false;
        private EngineType _erroredEngine;

        public bool PrintDebugInfo = false;

        public ScriptOutputStream(ScriptRuntime pyrvtScript) {
            _outputBuffer = string.Empty;
            _pyrvtScript = new WeakReference<ScriptRuntime>(pyrvtScript);
            _gui = new WeakReference<ScriptOutput>(null);
        }

        public ScriptOutputStream(ScriptOutput gui) {
            _outputBuffer = string.Empty;
            _pyrvtScript = new WeakReference<ScriptRuntime>(null);
            _gui = new WeakReference<ScriptOutput>(gui);
        }

        public ScriptOutput GetOutput() {
            ScriptRuntime pyrvtScript;
            var re = _pyrvtScript.TryGetTarget(out pyrvtScript);
            if (re && pyrvtScript != null)
                return pyrvtScript.OutputWindow;

            ScriptOutput output;
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

        public void WriteError(string error_msg, EngineType engineType) {
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
                            ScriptOutputConfigs.DefaultBlock);

                    if (count < 1024) {
                        // write to output window
                        if (!_errored)
                            output.AppendText(_outputBuffer, ScriptOutputConfigs.DefaultBlock);
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
            _pyrvtScript = null;
            _gui = null;
            Dispose(true);
        }
    }
}
