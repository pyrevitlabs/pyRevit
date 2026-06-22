using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Windows.Threading;
using pyRevitLabs.Common.Extensions;

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>
    /// Stream connecting script stdout/stderr/stdin to the output window.
    /// Writes are buffered and rendered in batches; only the minimal stream
    /// surface used by the script engines is implemented.
    /// </summary>
    public class ScriptIO : Stream, IDisposable {
        private WeakReference<ScriptRuntime> _runtime;
        private WeakReference<ScriptConsole> _gui;
        private readonly Queue<string> _pending = new Queue<string>();
        private int _pendingChars;
        private readonly StringBuilder _partial = new StringBuilder();
        private readonly object _logLock = new object();
        private bool _inputReceived = false;
        private bool _errored = false;
        private ScriptEngineType _erroredEngine;
        private bool _prefixAtLineStart = true;

        private const int StreamChunkSize = 1024;
        private const int MaxStreamEntryChars = 8192;
        private const int SoftFlushCharLimit = 16384;
        private const int MaxPendingChars = 1048576;
        private const int FlushMaxEntriesPerTick = 256;
        private const int FlushMaxCharsPerTick = 65536;
        private static readonly TimeSpan FlushInterval = TimeSpan.FromMilliseconds(16);
        private static readonly TimeSpan SyncFlushInterval = TimeSpan.FromMilliseconds(50);

        private readonly object _timerLock = new object();
        private DispatcherTimer _flushTimer;

        // Guards against re-entrant flushing. Rendering an entry pumps the message
        // queue (DoEvents/render), which can fire the flush timer or another window's
        // flush mid-drain and recurse until the stack overflows. A flush already in
        // progress on this thread drains the queue, so re-entrant calls are skipped.
        [ThreadStatic]
        private static bool _flushingOnThread;
        private bool _firstShowPending = true;
        private bool _syncFlushedOnce = false;
        private readonly System.Diagnostics.Stopwatch _syncFlushClock = System.Diagnostics.Stopwatch.StartNew();

        public bool PrintDebugInfo = false;

        public ScriptIO(ScriptRuntime runtime) {
            _runtime = new WeakReference<ScriptRuntime>(runtime);
            _gui = new WeakReference<ScriptConsole>(null);
        }

        public ScriptIO(ScriptConsole gui) {
            _runtime = new WeakReference<ScriptRuntime>(null);
            _gui = new WeakReference<ScriptConsole>(gui);
        }

        private ScriptRuntime GetRuntime() {
            if (_runtime == null)
                return null;

            ScriptRuntime runtime;
            var re = _runtime.TryGetTarget(out runtime);
            return re ? runtime : null;
        }

        private string GetLogFilePath() {
            var runtime = GetRuntime();
            var logFilePath = runtime?.ScriptRuntimeConfigs?.LogFilePath;
            return string.IsNullOrWhiteSpace(logFilePath) ? null : logFilePath;
        }

        private void AppendLog(string outputText) {
            var logFilePath = GetLogFilePath();
            if (string.IsNullOrEmpty(logFilePath))
                return;

            lock (_logLock) {
                try {
                    var logDir = Path.GetDirectoryName(logFilePath);
                    if (!string.IsNullOrEmpty(logDir))
                        Directory.CreateDirectory(logDir);
                    File.AppendAllText(logFilePath, outputText, OutputEncoding);
                }
                catch (Exception ex) {
                    if (PrintDebugInfo) {
                        System.Diagnostics.Debug.WriteLine(
                            string.Format("[ScriptIO] Failed to append to log file '{0}': {1}", logFilePath, ex)
                        );
                    }
                }
            }
        }

        private string PrefixStartupOutput(string outputText) {
            var prefix = ScriptOutput.GetStartupOutputPrefix(GetRuntime());
            if (string.IsNullOrEmpty(prefix) || string.IsNullOrEmpty(outputText))
                return outputText;

            var output = new StringBuilder();
            foreach (var chr in outputText) {
                if (chr == '\r' || chr == '\n') {
                    output.Append(chr);
                    _prefixAtLineStart = true;
                    continue;
                }

                if (_prefixAtLineStart) {
                    output.Append(prefix);
                    _prefixAtLineStart = false;
                }

                output.Append(chr);
            }

            return output.ToString();
        }

        public ScriptConsole GetOutput() {
            var runtime = GetRuntime();
            if (runtime != null) {
                if (runtime.ScriptRuntimeConfigs != null && runtime.ScriptRuntimeConfigs.SuppressOutput)
                    return null;
                return runtime.OutputWindow;
            }

            if (_gui == null)
                return null;

            ScriptConsole output;
            if (_gui.TryGetTarget(out output) && output != null)
                return output;

            return null;
        }

        public Encoding OutputEncoding {
            get {
                return Encoding.UTF8;
            }
        }

        /// <summary>
        /// Write stdout/stderr text. A large print arrives as a run of
        /// full-size chunks and is reassembled (see <see cref="Write"/>) so
        /// emoji tokens and html constructs are not split across entries.
        /// </summary>
        public void write(string content) {
            var buffer = OutputEncoding.GetBytes(content);
            Write(buffer, 0, buffer.Length);
        }

        /// <summary>
        /// Render a pre-composed html payload (print_html/md/code/table) as a
        /// single entry regardless of size.
        /// </summary>
        public void WriteEntry(string content) {
            if (string.IsNullOrEmpty(content))
                return;
            if (content.IndexOf('\0') >= 0)
                content = content.Replace("\0", string.Empty);
            AppendLog(content);

            var output = GetOutput();
            if (output == null)
                return;

            if (output.ClosedByUser) {
                _gui = new WeakReference<ScriptConsole>(null);
                ClearPending();
                StopFlushTimer();
                return;
            }

            bool needShow = !output.IsVisible;
            int pendingChars;

            lock (this) {
                FinalizePendingEntry();
                _partial.Append(content);
                FinalizePendingEntry(splitLargeEntries: false);

                while (_pendingChars > MaxPendingChars && _pending.Count > 1)
                    _pendingChars -= _pending.Dequeue().Length;

                pendingChars = _pendingChars;
            }

            PumpAfterWrite(output, needShow, pendingChars, forceSyncFlush: true);
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
            var tempBuffer = new byte[count];
            Array.Copy(buffer, offset, tempBuffer, 0, count);
            var outputText = OutputEncoding.GetString(tempBuffer);
            if (outputText.IndexOf('\0') >= 0)
                outputText = outputText.Replace("\0", string.Empty);
            AppendLog(outputText);

            var output = GetOutput();
            if (output == null) {
                return;
            }

            if (output.ClosedByUser) {
                _gui = new WeakReference<ScriptConsole>(null);
                ClearPending();
                StopFlushTimer();
                return;
            }

            bool needShow = outputText.Length > 0 && !output.IsVisible;
            int pendingChars;

            lock (this) {
                if (PrintDebugInfo) {
                    output.AppendText(
                        string.Format("<---- W offset: {0} count: {1} ---->", offset, count),
                        ScriptConsoleConfigs.DefaultBlock);
                }

                if (outputText.Length > 0)
                    _partial.Append(outputText);

                // a full-size chunk signals more of this stream write is still coming
                if (count < StreamChunkSize || _partial.Length >= MaxStreamEntryChars)
                    FinalizePendingEntry();

                while (_pendingChars > MaxPendingChars && _pending.Count > 1)
                    _pendingChars -= _pending.Dequeue().Length;

                pendingChars = _pendingChars;
            }

            PumpAfterWrite(output, needShow, pendingChars);
        }

        private void PumpAfterWrite(ScriptConsole output, bool needShow, int pendingChars, bool forceSyncFlush = false) {
            if (needShow) {
                try {
                    output.Show();
                }
                catch {
                    return;
                }
                if (_firstShowPending) {
                    _firstShowPending = false;
                    try {
                        if (IsDispatcherReady(output.Dispatcher)) {
                            output.Dispatcher.BeginInvoke(
                                new Action(output.ForceRenderFrame),
                                DispatcherPriority.Render);
                        }
                    }
                    catch {
                    }
                }
            }

            EnsureFlushTimer(output);

            var dispatcher = output.Dispatcher;
            if (IsDispatcherReady(dispatcher) && dispatcher.CheckAccess()
                    && (forceSyncFlush
                        || !_syncFlushedOnce
                        || pendingChars >= SoftFlushCharLimit
                        || _syncFlushClock.Elapsed >= SyncFlushInterval)) {
                _syncFlushedOnce = true;
                FlushUpToBudget();
                output.ForceRenderFrame();
                _syncFlushClock.Restart();
            }
        }

        private static bool IsDispatcherReady(Dispatcher dispatcher) {
            return dispatcher != null
                && !dispatcher.HasShutdownStarted
                && !dispatcher.HasShutdownFinished;
        }

        private void EnsureFlushTimer(ScriptConsole output) {
            var dispatcher = output.Dispatcher;
            if (!IsDispatcherReady(dispatcher))
                return;

            DispatcherTimer timer;
            lock (_timerLock) {
                if (_flushTimer != null)
                    return;

                timer = new DispatcherTimer(DispatcherPriority.Background, dispatcher);
                timer.Interval = FlushInterval;
                timer.Tick += OnFlushTick;
                _flushTimer = timer;
            }

            if (dispatcher.CheckAccess()) {
                timer.Start();
                return;
            }

            dispatcher.BeginInvoke(new Action(() => {
                lock (_timerLock) {
                    if (_flushTimer == timer)
                        timer.Start();
                }
            }));
        }

        private void StopFlushTimer() {
            DispatcherTimer timer;
            lock (_timerLock) {
                timer = _flushTimer;
                _flushTimer = null;
            }

            if (timer == null)
                return;

            timer.Tick -= OnFlushTick;
            var dispatcher = timer.Dispatcher;
            if (dispatcher.CheckAccess())
                timer.Stop();
            else if (IsDispatcherReady(dispatcher))
                dispatcher.BeginInvoke(new Action(timer.Stop));
        }

        private void OnFlushTick(object sender, EventArgs e) {
            FlushUpToBudget();
        }

        private void ClearPending() {
            lock (this) {
                _pending.Clear();
                _pendingChars = 0;
                _partial.Clear();
            }
        }

        private void FinalizePendingEntry(bool splitLargeEntries = true, bool keepIncompleteShortcode = true) {
            if (_partial.Length == 0)
                return;

            string heldShortcode = null;
            var holdStart = keepIncompleteShortcode ? FindTrailingShortcodeStart(_partial) : -1;
            if (holdStart >= 0) {
                heldShortcode = _partial.ToString(holdStart, _partial.Length - holdStart);
                _partial.Remove(holdStart, _partial.Length - holdStart);
            }

            if (splitLargeEntries) {
                while (_partial.Length > MaxStreamEntryChars) {
                    var splitIndex = FindSplitIndex(_partial, MaxStreamEntryChars);
                    EnqueuePending(_partial.ToString(0, splitIndex));
                    _partial.Remove(0, splitIndex);
                }
            }

            var entry = _partial.ToString();
            _partial.Clear();
            EnqueuePending(entry);

            if (heldShortcode != null)
                _partial.Append(heldShortcode);
        }

        private void EnqueuePending(string entry) {
            if (entry.Length == 0)
                return;

            _pending.Enqueue(entry);
            _pendingChars += entry.Length;
        }

        private static int FindSplitIndex(StringBuilder text, int maxChars) {
            var limit = Math.Min(maxChars, text.Length);
            var shortcodeStart = -1;
            var colonCount = 0;
            for (var idx = limit - 1; idx >= 0; idx--) {
                if (char.IsWhiteSpace(text[idx]))
                    break;
                if (text[idx] == ':') {
                    colonCount++;
                    shortcodeStart = idx;
                }
            }

            if (colonCount == 1 && shortcodeStart > 0)
                return shortcodeStart;

            for (var idx = limit - 1; idx > 0; idx--) {
                if (text[idx] == '\n' || text[idx] == '\r')
                    return idx + 1;
            }

            for (var idx = limit - 1; idx > 0; idx--) {
                if (char.IsWhiteSpace(text[idx]))
                    return idx + 1;
            }

            if (limit < text.Length
                    && limit > 0
                    && char.IsHighSurrogate(text[limit - 1])
                    && char.IsLowSurrogate(text[limit]))
                return limit - 1;

            return limit;
        }

        private static int FindTrailingShortcodeStart(StringBuilder text) {
            var tokenStart = text.Length;
            for (var idx = text.Length - 1; idx >= 0; idx--) {
                if (char.IsWhiteSpace(text[idx]))
                    break;
                tokenStart = idx;
            }

            var colonCount = 0;
            var firstColon = -1;
            for (var idx = tokenStart; idx < text.Length; idx++) {
                if (text[idx] == ':') {
                    if (firstColon == -1)
                        firstColon = idx;
                    colonCount++;
                }
            }

            if (colonCount == 1 && firstColon == tokenStart && firstColon < text.Length - 1)
                return firstColon;

            return -1;
        }

        private void FlushUpToBudget() {
            if (_flushingOnThread)
                return;
            _flushingOnThread = true;
            try {
                int charBudget = FlushMaxCharsPerTick;
                int entryBudget = FlushMaxEntriesPerTick;
                while (entryBudget-- > 0) {
                    if (!FlushOneEntry())
                        return;
                    charBudget -= _lastEntryChars;
                    if (charBudget <= 0)
                        return;
                }
            }
            finally {
                _flushingOnThread = false;
            }
        }

        private int _lastEntryChars;

        private bool FlushOneEntry() {
            ScriptConsole output;
            string entry;
            bool morePending;

            lock (this) {
                if (_pending.Count == 0) {
                    StopFlushTimer();
                    return false;
                }

                output = GetOutput();
                if (output == null || output.ClosedByUser) {
                    _pending.Clear();
                    _pendingChars = 0;
                    StopFlushTimer();
                    return false;
                }

                entry = _pending.Dequeue();
                _pendingChars -= entry.Length;
                _lastEntryChars = entry.Length;
                morePending = _pending.Count > 0;
            }

            DrainOutput(output, entry);

            if (!morePending) {
                StopFlushTimer();
                return false;
            }
            return true;
        }

        private void DrainOutput(ScriptConsole output, string pending) {
            if (string.IsNullOrEmpty(pending))
                return;

            var prefixed = PrefixStartupOutput(pending);
            if (_errored)
                output.AppendError(prefixed, _erroredEngine);
            else
                output.AppendHtmlFragment(prefixed, ScriptConsoleConfigs.DefaultBlock);
        }

        /// <summary>
        /// Synchronously render everything buffered so far. Callers that
        /// inspect or modify the rendered document must flush first.
        /// </summary>
        public override void Flush() {
            StopFlushTimer();
            lock (this) {
                FinalizePendingEntry(keepIncompleteShortcode: false);
            }
            if (_flushingOnThread)
                return;
            _flushingOnThread = true;
            try {
                while (FlushOneEntry()) {
                }
            }
            finally {
                _flushingOnThread = false;
            }
        }

        public override long Seek(long offset, SeekOrigin origin) {
            throw new NotImplementedException();
        }

        public override void SetLength(long value) {
            throw new NotImplementedException();
        }

        public string read(int size = -1) {
            return readline(size);
        }

        public string readline(int size=-1) {
            var buffer = new byte[1024];
            var _ = Read(buffer, 0, 1024);
            _ = Read(buffer, 0, 1024);
            return OutputEncoding.GetString(buffer);
        }

        public override int Read(byte[] buffer, int offset, int count) {
            if (buffer == null)
                throw new ArgumentNullException("buffer", "buffer is null");
            if (count < 0 || offset < 0)
                throw new ArgumentException("offset or count is negative.");
            if (offset + count > buffer.Length)
                throw new IndexOutOfRangeException("The sum of offset and count is larger than the buffer length.");

            var output = GetOutput();
            if (output != null) {
                if (output.ClosedByUser) {
                    _gui = new WeakReference<ScriptConsole>(null);
                    ClearPending();
                    StopFlushTimer();
                    return 0;
                }

                if (!output.IsVisible) {
                    try {
                        output.Show();
                        output.Focus();
                    }
                    catch {
                        return 0;
                    }
                }

                lock (this) {
                    string input = string.Empty;

                    if (_inputReceived) {
                        _inputReceived = false;
                        return 0;
                    }

                    input = output.GetInput();
                    _inputReceived = true;

                    if (PrintDebugInfo)
                        output.AppendText(
                            string.Format("<---- R offset: {0} count: {1} ---->", offset, count),
                            ScriptConsoleConfigs.DefaultBlock);

                    var inputBytes = OutputEncoding.GetBytes(input);
                    if (inputBytes.Length > 0) {
                        int copyCount = Math.Min(inputBytes.Length, count);
                        Buffer.BlockCopy(inputBytes, 0, buffer, offset, copyCount);
                        if (PrintDebugInfo)
                            output.AppendText(
                                string.Format("<---- R copied: \"{0}\" size: {1} ---->", input, copyCount),
                                ScriptConsoleConfigs.DefaultBlock);
                    }

                    return inputBytes.Length;
                }
            }

            return 0;
        }

        public override bool CanRead {
            get { return true; }
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
            StopFlushTimer();
            _runtime = null;
            _gui = null;
            Dispose(true);
        }
    }
}
