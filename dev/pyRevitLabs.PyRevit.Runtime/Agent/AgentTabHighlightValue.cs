using System;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>Repaints and restores an opaque property only while its installed value still owns the slot.</summary>
    internal sealed class AgentTabHighlightValue {
        private readonly Func<object> read;
        private readonly Action<object> write;
        private readonly Action restore;
        private object installed;
        private bool applied;
        private bool released;

        internal AgentTabHighlightValue(Func<object> read, Action<object> write, Action restore) {
            this.read = read;
            this.write = write;
            this.restore = restore;
        }

        internal void Apply(object value) {
            if (released)
                return;
            if (applied && !ReferenceEquals(read(), installed)) {
                released = true;
                return;
            }
            installed = value;
            applied = true;
            write(value);
        }

        internal void Restore() {
            if (!released && applied && ReferenceEquals(read(), installed))
                restore();
            installed = null;
            applied = false;
        }
    }
}
