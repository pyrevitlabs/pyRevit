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
    /// Bounded FIFO of log records an output could not show yet, plus the gate that decides
    /// whether a new record must wait behind them.
    /// </summary>
    /// <remarks>
    /// The gate starts closed. <see cref="DrainOrOpen"/> hands back the backlog in batches and
    /// opens the gate only when it finds nothing left, under the same lock <see cref="TryHold"/>
    /// uses. A record written while the backlog is being released is therefore held and comes out
    /// in a later batch, never ahead of older records.
    /// <para>
    /// Past <c>capacity</c> the oldest record is discarded and counted, rather than letting a
    /// session that never opens a window grow the buffer without bound; the count survives until
    /// the next drain reports it.
    /// </para>
    /// <para>
    /// Invariant: the hold decision and the gate change happen under one lock. Deciding "no window
    /// yet" outside it lets a thread be preempted while the backlog drains and the gate opens,
    /// then hold a record nothing will ever release.
    /// </para>
    /// </remarks>
    internal sealed class HeldRecordBuffer {
        private static readonly HeldRecord[] Empty = new HeldRecord[0];

        private readonly object _lock = new object();
        private readonly Queue<HeldRecord> _records = new Queue<HeldRecord>();
        private readonly int _capacity;
        private int _dropped;
        private bool _open;

        internal HeldRecordBuffer(int capacity) {
            _capacity = capacity;
        }

        internal int Count {
            get {
                lock (_lock)
                    return _records.Count;
            }
        }

        internal bool IsOpen {
            get {
                lock (_lock)
                    return _open;
            }
        }

        /// <summary>
        /// Holds the record unless the gate is open.
        /// </summary>
        /// <returns>
        /// True if the record was held. False means the backlog has been released and the caller
        /// must write the record itself.
        /// </returns>
        internal bool TryHold(string content, bool markError) {
            lock (_lock) {
                if (_open)
                    return false;

                while (_records.Count >= _capacity) {
                    _records.Dequeue();
                    _dropped++;
                }
                _records.Enqueue(new HeldRecord(content, markError));
                return true;
            }
        }

        /// <summary>
        /// Closes the gate so records wait again, ahead of a window being (re)created.
        /// </summary>
        internal void Close() {
            lock (_lock)
                _open = false;
        }

        /// <summary>
        /// Removes and returns everything held, oldest first, or opens the gate if nothing is.
        /// </summary>
        /// <param name="dropped">
        /// How many records were discarded for capacity since the last drain. Reported separately
        /// because those records no longer exist to be returned.
        /// </param>
        /// <remarks>
        /// Call repeatedly until it returns an empty batch with no drops; that call is the one that
        /// opens the gate.
        /// </remarks>
        internal HeldRecord[] DrainOrOpen(out int dropped) {
            lock (_lock) {
                if (_records.Count == 0 && _dropped == 0) {
                    _open = true;
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
