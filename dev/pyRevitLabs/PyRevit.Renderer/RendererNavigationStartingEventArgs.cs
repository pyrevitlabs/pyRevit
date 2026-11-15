using System;

namespace PyRevitLabs.PyRevit.Renderer {
    /// <summary>
    /// Neutral payload for a renderer navigation request.
    ///
    /// Replaces the renderer-specific navigation event arguments so the
    /// renderer contract does not force its consumers to reference the
    /// rendering stack.
    /// </summary>
    public sealed class RendererNavigationStartingEventArgs : EventArgs {
        /// <summary>Creates the arguments for a navigation to <paramref name="uri"/>.</summary>
        public RendererNavigationStartingEventArgs(string uri) {
            Uri = uri;
        }

        /// <summary>The URI the renderer is about to navigate to.</summary>
        public string Uri { get; }

        /// <summary>Set to true to abort the navigation.</summary>
        public bool Cancel { get; set; }
    }
}
