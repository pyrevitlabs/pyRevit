using System.Threading;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Decides when the host warms the agent engine: starting it, importing the runner and
    /// running the runner's code paths once per session load, after the first request an agent
    /// sends, so the first run doesn't pay two to three seconds for them.
    /// </summary>
    /// <remarks>
    /// Waiting for the first request keeps the cost off Revit sessions whose agent never
    /// connects; warming on the first Idling froze Revit for up to 2.4 s as the model opened.
    /// Only the IronPython engine is warmed, and only when it is the configured default.
    /// CPython is left to its first run: pythonnet's first initialize scans every loaded
    /// assembly, can fail on missing add-in dependencies, and keeps the interpreter up for the
    /// rest of the Revit process, which is not a safe thing to start unasked.
    /// Thread-safe: requests arrive on pipe threads, reloads on the Revit main thread.
    /// </remarks>
    internal sealed class AgentEngineWarmUp {
        private const string RunMethod = "run";
        private int load;
        private int contactedLoad = -1;

        /// <summary>
        /// The current session load, to pass back to <see cref="OnRequest"/> once the request
        /// has been handled.
        /// </summary>
        public int Load => Volatile.Read(ref load);

        /// <summary>
        /// Starts a new session load. A reload drops the cached engines, so the next request
        /// warms again.
        /// </summary>
        public void Reset() {
            Interlocked.Increment(ref load);
        }

        /// <summary>
        /// Records a handled agent request and says whether it should queue the warm-up: only
        /// the first request of the session load other than a <c>run</c> does. A <c>run</c>
        /// records nothing: one that executes starts the engine itself, and one refused before
        /// it executes leaves the next request to warm.
        /// </summary>
        /// <param name="method">The request's JSON-RPC method.</param>
        /// <param name="loadAtStart"><see cref="Load"/> read before the request was handled.</param>
        /// <remarks>
        /// A request during which a reload happened, such as a <c>run</c> that reloads pyRevit,
        /// belongs to the previous load. It records nothing, so the new load stays unwarmed until
        /// its own first request.
        /// </remarks>
        public bool OnRequest(string method, int loadAtStart) {
            if (loadAtStart != Load || method == RunMethod)
                return false;
            return Interlocked.Exchange(ref contactedLoad, loadAtStart) != loadAtStart;
        }

        /// <summary>
        /// Whether the queued warm-up should run when the main thread reaches it.
        /// </summary>
        /// <remarks>
        /// A cached engine means a run got there first, so warming would only repeat its work.
        /// </remarks>
        public static bool ShouldWarm(bool agentEnabled, bool defaultEngineIsIronPython, bool engineCached) {
            return agentEnabled && defaultEngineIsIronPython && !engineCached;
        }
    }
}
