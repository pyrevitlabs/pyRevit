#if !NETFRAMEWORK
namespace pyRevitLabs.PyRevit.Runtime.Shared {
    /// <summary>
    /// Owner of the isolated WebView2 load context of the process.
    ///
    /// The context must be one per process, not one per runtime version. Every
    /// runtime version is deployed to the same engine folder and the loader
    /// sweeps that folder, so a host process holds the Revit 2025, 2026 and
    /// 2027 runtimes at once. A context owned by a per-year runtime would
    /// therefore give the process one copy of the WebView2 stack and one
    /// Chromium environment per runtime version.
    ///
    /// The owner lives in the shared runtime assembly, which is deployed as a
    /// single file to the binary folder and loaded once per process. Every
    /// runtime version binds that one instance, so they all share the same
    /// context.
    ///
    /// Invariant: the context is created on first use and kept for the
    /// lifetime of the process. The WebView2 browser process and its profile
    /// outlive any single output window, and a second context would bring a
    /// second copy of the stack along.
    ///
    /// Important: the folder of the first caller wins. Every runtime version
    /// resolves the same isolated folder, so the callers cannot disagree.
    /// </summary>
    public static class IsolatedWebView2Context {
        private static readonly object SyncRoot = new object();

        private static WebView2LoadContext _context;

        /// <summary>
        /// The isolated WebView2 load context of this process, created on
        /// first use.
        /// </summary>
        /// <param name="isolatedDirectory">
        /// Folder holding the isolated WebView2 stack.
        /// </param>
        public static WebView2LoadContext GetOrCreate(string isolatedDirectory) {
            lock (SyncRoot) {
                if (_context == null)
                    _context = new WebView2LoadContext(isolatedDirectory);

                return _context;
            }
        }
    }
}
#endif
