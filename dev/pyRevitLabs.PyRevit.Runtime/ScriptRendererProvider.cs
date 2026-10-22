using System;
using System.IO;
using System.Text.RegularExpressions;
using System.Windows.Threading;
using PyRevitLabs.PyRevit.Renderer;
using PyRevitLabs.PyRevit.WebView2;

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>
    /// Creates the renderer behind a script output window.
    ///
    /// The renderer is hosted in its own assembly so that it can later be
    /// moved out of the host process default load context without the
    /// runtime having to give up its renderer abstraction.
    /// </summary>
    internal static class ScriptRendererProvider {
        /// <summary>
        /// Creates the renderer on <paramref name="dispatcher"/>.
        /// </summary>
        internal static IScriptRenderer Create(Dispatcher dispatcher) {
            return new WebView2ScriptRenderer(dispatcher, GetProfileFolder());
        }

        /// <summary>
        /// Name of the browser profile folder for this host. Every Revit
        /// version gets its own, because sharing one folder makes hosts that
        /// run side by side connect to whichever browser process won the race.
        /// </summary>
        private static string GetProfileFolder() {
            try {
                var match = Regex.Match(
                    Path.GetFileNameWithoutExtension(typeof(ScriptRendererProvider).Assembly.Location),
                    @"(\d{4})$");
                if (match.Success)
                    return match.Groups[1].Value;
            }
            catch {
            }

            return "shared";
        }
    }
}
