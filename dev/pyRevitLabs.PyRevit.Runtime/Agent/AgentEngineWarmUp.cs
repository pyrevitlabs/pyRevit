namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Decides when the host warms the agent engine: starting it and importing the runner
    /// once per session load, on the first Idling after the load, so the first agent run
    /// doesn't pay about two seconds for both.
    /// </summary>
    /// <remarks>
    /// Only the IronPython engine is warmed, and only when it is the configured default.
    /// CPython is left to its first run: pythonnet's first initialize scans every loaded
    /// assembly, can fail on missing add-in dependencies, and keeps the interpreter up for the
    /// rest of the Revit process, which is not a safe thing to start unasked on Idling.
    /// Not thread-safe: the host uses it on the Revit main thread only.
    /// </remarks>
    internal sealed class AgentEngineWarmUp {
        private bool scheduled;

        /// <summary>
        /// Whether the caller should subscribe the warm-up to the next Idling event.
        /// </summary>
        /// <remarks>
        /// False while a warm-up is already waiting, so loads before the first Idling subscribe
        /// once, and false when Revit has no user interface, where Idling never comes.
        /// </remarks>
        public bool Schedule(bool hasUserInterface) {
            if (scheduled || !hasUserInterface)
                return false;
            scheduled = true;
            return true;
        }

        /// <summary>
        /// Consumes the scheduled warm-up, so the next load can schedule another one.
        /// </summary>
        /// <returns>Whether a warm-up was scheduled.</returns>
        public bool TakeScheduled() {
            var wasScheduled = scheduled;
            scheduled = false;
            return wasScheduled;
        }

        /// <summary>
        /// Whether a taken warm-up should run: the host must still be running, because a
        /// reload that turned the agent off happens before the Idling, and the default engine
        /// must be IronPython.
        /// </summary>
        public static bool ShouldWarm(bool hostRunning, bool defaultEngineIsIronPython) {
            return hostRunning && defaultEngineIsIronPython;
        }
    }
}
