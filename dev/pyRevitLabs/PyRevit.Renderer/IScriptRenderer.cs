using System;
using System.Threading.Tasks;
using System.Windows;

namespace PyRevitLabs.PyRevit.Renderer {
    /// <summary>
    /// Contract for the script output renderer.
    ///
    /// The contract is deliberately free of any renderer technology: it exposes
    /// a plain WPF <see cref="FrameworkElement"/> and neutral event payloads so
    /// that consumers never take a metadata reference on a specific rendering
    /// stack. That is what allows the implementation to be hosted in an
    /// isolated load context without dragging that stack into the host
    /// process.
    /// </summary>
    public interface IScriptRenderer : IDisposable {
        /// <summary>The visual host of the renderer, to be placed in a window.</summary>
        FrameworkElement Control { get; }

        /// <summary>Version of the browser backing the renderer; empty until initialized.</summary>
        string BrowserVersion { get; }

        /// <summary>
        /// Why the renderer cannot show a browser view, or
        /// <see cref="RendererFailure.None"/> while it can. When it is not
        /// <see cref="RendererFailure.None"/> the owner keeps the window usable
        /// as plain text and reports the matching cause instead of a generic
        /// failure.
        /// </summary>
        RendererFailure Failure { get; }

        /// <summary>True when the renderer could not be brought up; it will never render.</summary>
        bool InitializationFailed { get; }

        /// <summary>True when the document is readable and can accept content.</summary>
        bool IsDocumentReady { get; }

        /// <summary>True once the browser core is up; the document may still be navigating.</summary>
        bool IsCoreReady { get; }

        /// <summary>Completes when the renderer is up or has permanently failed; never faults.</summary>
        Task ReadyTask { get; }

        /// <summary>
        /// Start bringing the renderer online and run the first navigation.
        /// The provider is invoked once and returns the URI to load, or null to
        /// skip navigation. Never blocks.
        /// </summary>
        void EnsureReady(Func<string> firstNavigationProvider);

        /// <summary>
        /// Block the calling thread until the document is readable or
        /// initialization has permanently failed.
        /// </summary>
        void WaitUntilReady(int timeoutMilliseconds = 30000);

        /// <summary>Navigate the top-level document. Does not block.</summary>
        void Navigate(string url);

        /// <summary>Submit a script for execution without waiting for a result.</summary>
        void PostScript(string javaScript);

        /// <summary>Execute a script and block until its encoded result arrives.</summary>
        string EvalScript(string javaScript);

        /// <summary>Show the print dialog for the current document.</summary>
        void ShowPrintUi();

        /// <summary>Raised for top-level navigations so the owner can enforce URL policy.</summary>
        event EventHandler<RendererNavigationStartingEventArgs> NavigationStartingRequested;

        /// <summary>
        /// Raised whenever the view becomes able to accept content: after the
        /// core comes online and after each navigation settles.
        /// </summary>
        event EventHandler DocumentReady;
    }
}
