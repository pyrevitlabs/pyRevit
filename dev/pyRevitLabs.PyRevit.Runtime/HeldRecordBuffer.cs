using System.Collections.Generic;

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>
    /// One log record held until an output window exists to show it.
    /// </summary>
    internal struct HeldRecord {
        internal HeldRecord(string content, bool markError) {
            Content = content;
            MarkError = markError;
        }

        internal string Content { get; }
        internal bool MarkError { get; }
    }

    /// <summary>
    /// Bounded FIFO of log records an output could not show yet, drained into its window once one
    /// opens. Owned per <see cref="ScriptOutput"/>, so one output never inherits another's backlog.
    /// </summary>
    /// <remarks>
    /// Records arrive from any thread and drain on the dispatcher thread, so every operation locks.
    /// Past <c>capacity</c> the oldest record is discarded and counted, rather than letting a
    /// session that never opens a window grow the buffer without bound; the count survives until
    /// the next drain reports it.
    /// </remarks>
    internal sealed class HeldRecordBuffer {
        private static readonly HeldRecord[] Empty = new HeldRecord[0];

        private readonly object _lock = new object();
        private readonly Queue<HeldRecord> _records = new Queue<HeldRecord>();
        private readonly int _capacity;
        private int _dropped;

        internal HeldRecordBuffer(int capacity) {
            _capacity = capacity;
        }

        internal int Count {
            get {
                lock (_lock)
                    return _records.Count;
            }
        }

        internal void Hold(string content, bool markError) {
            lock (_lock) {
                while (_records.Count >= _capacity) {
                    _records.Dequeue();
                    _dropped++;
                }
                _records.Enqueue(new HeldRecord(content, markError));
            }
        }

        /// <summary>
        /// Removes and returns everything held, oldest first.
        /// </summary>
        /// <param name="dropped">
        /// How many records were discarded for capacity since the last drain. Reported separately
        /// because those records no longer exist to be returned.
        /// </param>
        internal HeldRecord[] Drain(out int dropped) {
            lock (_lock) {
                if (_records.Count == 0 && _dropped == 0) {
                    dropped = 0;
                    return Empty;
                }

                var released = _records.ToArray();
                dropped = _dropped;
                _records.Clear();
                _dropped = 0;
                return released;
            }
        }
    }
}
