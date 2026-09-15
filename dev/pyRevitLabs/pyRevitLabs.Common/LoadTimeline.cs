using System;
using System.Collections.Generic;
using System.Diagnostics;

namespace pyRevitLabs.Common {
    /// <summary>
    /// One pyRevit session load measured on a single monotonic clock, recorded as a tree of named
    /// spans that the C# loader, the script runtime and script engines all write into, so their
    /// timings add up against the same total.
    /// </summary>
    /// <remarks>
    /// <para>
    /// Spans open and close on the Revit main thread in nested order: <see cref="StartSpan"/>
    /// parents the new span under the innermost span still open.
    /// </para>
    /// <para>
    /// Invariant: <see cref="Active"/> is null outside a load, so timing calls made by engines and
    /// scripts that run after startup record nothing.
    /// </para>
    /// </remarks>
    public sealed class LoadTimeline {
        private static readonly object ActiveLock = new object();
        private static LoadTimeline _active;

        private readonly object _lock = new object();
        private readonly Stack<LoadSpan> _openSpans = new Stack<LoadSpan>();

        private LoadTimeline(string name, long startTimestamp) {
            Root = new LoadSpan(this, name, startTimestamp);
            _openSpans.Push(Root);
        }

        /// <summary>The load in progress, or null when no load is running.</summary>
        public static LoadTimeline Active {
            get {
                lock (ActiveLock)
                    return _active;
            }
        }

        /// <summary>Span covering the whole load; its direct children are the top-level steps.</summary>
        public LoadSpan Root { get; }

        /// <summary>
        /// True when another load began before this one ended, as when postload triggers a reload.
        /// A replaced timeline still accepts spans from callers holding it, but is no longer
        /// <see cref="Active"/>.
        /// </summary>
        public bool IsReplaced { get; private set; }

        public bool IsEnded => Root.IsEnded;

        /// <summary>Milliseconds since the load started, or its total once ended.</summary>
        public double ElapsedMilliseconds => Root.ElapsedMilliseconds;

        /// <summary>
        /// How long the host process had been running when the load started. Set for the first
        /// load of a process only.
        /// </summary>
        public double? ProcessUptimeAtStartMilliseconds { get; set; }

        /// <summary>Load time not covered by any top-level step, which reveals uninstrumented work.</summary>
        public double UnaccountedMilliseconds {
            get {
                lock (_lock) {
                    var covered = 0.0;
                    foreach (var step in Root.Children)
                        covered += step.ElapsedMilliseconds;
                    return Math.Max(0.0, Root.ElapsedMilliseconds - covered);
                }
            }
        }

        /// <summary>
        /// Starts a new load and makes it <see cref="Active"/>, marking an unfinished active load as
        /// replaced.
        /// </summary>
        /// <param name="startTimestamp">
        /// <see cref="Stopwatch.GetTimestamp"/> value the load started at. It may predate this call
        /// when the caller had to load this assembly first.
        /// </param>
        public static LoadTimeline Begin(string name, long startTimestamp) {
            var timeline = new LoadTimeline(name, startTimestamp);
            lock (ActiveLock) {
                if (_active != null && !_active.IsEnded)
                    _active.IsReplaced = true;
                _active = timeline;
            }
            return timeline;
        }

        /// <summary>
        /// Opens a span under the innermost open span. Close it with <see cref="LoadSpan.End"/> or by
        /// disposing it.
        /// </summary>
        /// <returns>
        /// The new span. Once the load has ended the span is still returned, so callers can time
        /// unconditionally, but it is not attached to the tree.
        /// </returns>
        public LoadSpan StartSpan(string name) {
            var now = Stopwatch.GetTimestamp();
            lock (_lock) {
                if (IsEnded)
                    return new LoadSpan(this, name, now);

                var span = new LoadSpan(this, name, now, _openSpans.Peek());
                _openSpans.Push(span);
                return span;
            }
        }

        /// <summary>
        /// Adds an already finished span under the innermost open span, for work timed before this
        /// timeline could be reached.
        /// </summary>
        public LoadSpan RecordSpan(string name, long startTimestamp, long endTimestamp) {
            lock (_lock) {
                var span = new LoadSpan(this, name, startTimestamp, IsEnded ? null : _openSpans.Peek());
                span.EndTimestamp = endTimestamp;
                return span;
            }
        }

        /// <summary>
        /// Ends the load, closing any spans still open, and clears <see cref="Active"/> if this is
        /// still the active load.
        /// </summary>
        public void End() {
            Root.End();
            lock (ActiveLock) {
                if (_active == this)
                    _active = null;
            }
        }

        internal double EndSpan(LoadSpan span) {
            var now = Stopwatch.GetTimestamp();
            lock (_lock) {
                if (!span.IsEnded) {
                    if (_openSpans.Contains(span)) {
                        LoadSpan closed;
                        do {
                            closed = _openSpans.Pop();
                            closed.EndTimestamp = now;
                        } while (closed != span);
                    }
                    else
                        span.EndTimestamp = now;
                }
                return span.ElapsedMilliseconds;
            }
        }
    }

    /// <summary>A named, timed step within a <see cref="LoadTimeline"/>.</summary>
    public sealed class LoadSpan : IDisposable {
        private readonly LoadTimeline _timeline;
        private readonly List<LoadSpan> _children = new List<LoadSpan>();

        internal LoadSpan(LoadTimeline timeline, string name, long startTimestamp, LoadSpan parent = null) {
            _timeline = timeline;
            Name = name;
            StartTimestamp = startTimestamp;
            Parent = parent;
            parent?._children.Add(this);
        }

        public string Name { get; }

        public LoadSpan Parent { get; }

        public IReadOnlyList<LoadSpan> Children => _children;

        public long StartTimestamp { get; }

        public long? EndTimestamp { get; internal set; }

        public bool IsEnded => EndTimestamp.HasValue;

        /// <summary>Duration once ended; time since the span started while it is still open.</summary>
        public double ElapsedMilliseconds =>
            ((EndTimestamp ?? Stopwatch.GetTimestamp()) - StartTimestamp) * 1000.0 / Stopwatch.Frequency;

        /// <summary>
        /// Closes this span and any spans opened inside it that are still open. Ending a span that
        /// already ended changes nothing.
        /// </summary>
        /// <returns>The span's duration in milliseconds.</returns>
        public double End() => _timeline.EndSpan(this);

        public void Dispose() => End();
    }
}
