using System;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using PyRevitLabs.PyRevit.Renderer;

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>
    /// Stand-in renderer for a window whose renderer could not be loaded.
    ///
    /// The output window has to survive a renderer it cannot construct: a
    /// half-updated installation can leave an isolated folder from another
    /// pyRevit version, and failing the window would take the running script
    /// with it. The stand-in renders nothing, reports a broken deployment
    /// through the contract, and leaves the owner on the plain-text fallback it
    /// already has for an unusable renderer.
    ///
    /// Invariant: never touches WebView2. Reaching for it here would undo the
    /// isolation that kept the broken assembly out of the host process.
    /// </summary>
    internal sealed class UnavailableScriptRenderer : IScriptRenderer {
        private readonly Grid _control = new Grid();
        private readonly TaskCompletionSource<bool> _ready =
            new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);

        public UnavailableScriptRenderer() {
            _ready.TrySetResult(false);
        }

        public FrameworkElement Control {
            get { return _control; }
        }

        public string BrowserVersion {
            get { return string.Empty; }
        }

        public RendererFailure Failure {
            get { return RendererFailure.BrokenDeployment; }
        }

        public bool InitializationFailed {
            get { return false; }
        }

        public bool IsDocumentReady {
            get { return false; }
        }

        public bool IsCoreReady {
            get { return false; }
        }

        public Task ReadyTask {
            get { return _ready.Task; }
        }

        public event EventHandler<RendererNavigationStartingEventArgs> NavigationStartingRequested {
            add { }
            remove { }
        }

        public event EventHandler DocumentReady {
            add { }
            remove { }
        }

        public void EnsureReady(Func<string> firstNavigationProvider) {
        }

        public void WaitUntilReady(int timeoutMilliseconds = 30000) {
        }

        public void Navigate(string url) {
        }

        public void PostScript(string javaScript) {
        }

        public string EvalScript(string javaScript) {
            return string.Empty;
        }

        public void ShowPrintUi() {
        }

        public void Dispose() {
        }
    }
}
