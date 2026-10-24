using System;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>Restores an opaque property only while its installed value still owns the slot.</summary>
    internal sealed class AgentTabHighlightValue {
        private readonly Func<object> read;
        private readonly Action<object> write;
        private readonly Action restore;
        private object installed;

        internal AgentTabHighlightValue(Func<object> read, Action<object> write, Action restore) {
            this.read = read;
            this.write = write;
            this.restore = restore;
        }

        internal void Apply(object value) {
            installed = value;
            write(value);
        }

        internal void Restore() {
            if (installed != null && ReferenceEquals(read(), installed))
                restore();
            installed = null;
        }
    }
}
