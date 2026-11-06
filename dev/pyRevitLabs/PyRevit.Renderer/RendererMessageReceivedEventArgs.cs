using System;

namespace PyRevitLabs.PyRevit.Renderer {
    /// <summary>
    /// Neutral payload for a message a page posted to the host.
    ///
    /// Replaces the renderer-specific web message arguments so the renderer
    /// contract does not force its consumers to reference the rendering stack.
    /// </summary>
    public sealed class RendererMessageReceivedEventArgs : EventArgs {
        /// <summary>Creates the arguments for a message with the given JSON and string forms.</summary>
        public RendererMessageReceivedEventArgs(string json, string text) {
            Json = json;
            Text = text;
        }

        /// <summary>The posted message serialized as JSON; a posted string arrives as a JSON string literal.</summary>
        public string Json { get; }

        /// <summary>The posted message when it was a plain string; null for any other type.</summary>
        public string Text { get; }
    }
}
