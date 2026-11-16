using System;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Reloads the pyRevit config when its file path or write time changed since the last reload.
    /// </summary>
    /// <remarks>
    /// Invariant: the new path and write time are published only once the reload finished, so a
    /// request on another connection thread that sees them also sees the reloaded config, and a
    /// failed reload is tried again by the next request.
    /// </remarks>
    internal sealed class AgentConfigRefresh {
        private readonly object sync = new object();
        private readonly Func<string> configPath;
        private readonly Func<string, DateTime> lastWriteOf;
        private readonly Action reload;
        private string watchedPath;
        private DateTime watchedLastWrite = DateTime.MinValue;

        internal AgentConfigRefresh(Func<string> configPath, Func<string, DateTime> lastWriteOf, Action reload) {
            this.configPath = configPath;
            this.lastWriteOf = lastWriteOf;
            this.reload = reload;
        }

        /// <exception cref="Exception">Whatever reading the file time or reloading the config throws.</exception>
        internal void RefreshIfChanged() {
            var path = configPath();
            var lastWrite = lastWriteOf(path);
            lock (sync) {
                if (path == watchedPath && lastWrite == watchedLastWrite)
                    return;
                reload();
                watchedPath = path;
                watchedLastWrite = lastWrite;
            }
        }
    }
}
