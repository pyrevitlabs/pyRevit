using System.Collections.Concurrent;
using System.Globalization;
using System.Threading;

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>
    /// Holds element id lists too long to travel inside a <c>revit://</c> link and hands out the
    /// short token the link carries instead.
    /// </summary>
    /// <remarks>
    /// Owned by a <see cref="ScriptOutput"/> and bound to the window it renders into, so
    /// registering never touches the window and is safe from any thread. Tokens live until the
    /// bound window closes or the owning output is released.
    /// </remarks>
    internal sealed class ElementIdRegistry {
        private readonly ConcurrentDictionary<string, string> _idsByToken =
            new ConcurrentDictionary<string, string>();
        private int _tokenCounter;

        /// <param name="commaSeparatedIds">Element id values joined by commas.</param>
        /// <returns>Token to pass as the <c>elements</c> query parameter.</returns>
        public string Register(string commaSeparatedIds) {
            var token = Interlocked.Increment(ref _tokenCounter)
                .ToString(CultureInfo.InvariantCulture);
            _idsByToken[token] = commaSeparatedIds;
            return token;
        }

        /// <returns>The registered comma separated ids, or null for an unknown token.</returns>
        public string Resolve(string token) {
            string ids;
            return token != null && _idsByToken.TryGetValue(token, out ids) ? ids : null;
        }

        /// <summary>
        /// Drops every registration. Called when the window closes: its links die with the page,
        /// so the ids would only be held for as long as the owning output lives.
        /// </summary>
        public void Clear() {
            _idsByToken.Clear();
        }
    }
}
