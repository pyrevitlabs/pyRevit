using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.Linq;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Wall-clock breakdown of one agent run, reported as <c>timings_ms</c> in the run record
    /// so slow phases can be found without a profiler.
    /// </summary>
    /// <remarks>
    /// Host phases are measured back to back with <see cref="Lap"/>; phases the in-engine runner
    /// reports through <see cref="AgentScriptContext.ReportTiming"/> are nested inside the host's
    /// <c>engine</c> phase and keep a <c>script.</c> prefix. A phase recorded twice accumulates.
    /// Not thread-safe: the host and the runner both use it on the Revit main thread.
    /// </remarks>
    internal sealed class AgentRunTimings {
        private readonly Stopwatch clock = Stopwatch.StartNew();
        private readonly List<KeyValuePair<string, double>> phases = new List<KeyValuePair<string, double>>();
        private readonly double queueWaitMs;
        private double lastLapMs;

        /// <summary>
        /// Starts the clock and records <paramref name="queueWaitMs"/> as the <c>queue_wait</c> phase,
        /// which happened before construction but still counts toward <see cref="TotalMilliseconds"/>.
        /// </summary>
        public AgentRunTimings(double queueWaitMs) {
            this.queueWaitMs = queueWaitMs;
            Add("queue_wait", queueWaitMs);
        }

        /// <summary>
        /// Records the time since the previous lap (or since construction) as <paramref name="phase"/>.
        /// </summary>
        public void Lap(string phase) {
            var now = clock.Elapsed.TotalMilliseconds;
            Add(phase, now - lastLapMs);
            lastLapMs = now;
        }

        public void Add(string phase, double milliseconds) {
            for (var i = 0; i < phases.Count; i++) {
                if (phases[i].Key == phase) {
                    phases[i] = new KeyValuePair<string, double>(phase, phases[i].Value + milliseconds);
                    return;
                }
            }
            phases.Add(new KeyValuePair<string, double>(phase, milliseconds));
        }

        public double TotalMilliseconds => queueWaitMs + clock.Elapsed.TotalMilliseconds;

        public JObject ToJson() {
            var json = new JObject();
            foreach (var phase in phases)
                json[phase.Key] = Round(phase.Value);
            json["total"] = Round(TotalMilliseconds);
            return json;
        }

        public string Describe() {
            return string.Join(", ", phases.Select(phase => phase.Key + "=" + Round(phase.Value).ToString(CultureInfo.InvariantCulture)))
                + ", total=" + Round(TotalMilliseconds).ToString(CultureInfo.InvariantCulture);
        }

        private static double Round(double milliseconds) {
            return System.Math.Round(milliseconds, 1);
        }
    }
}
