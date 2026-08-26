using System;
using System.IO;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Threading;

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>
    /// Chromium renderer behind a script output window. Owns WebView2 control
    /// lifecycle, environment/user-data-folder setup, runtime availability
    /// handling, and synchronous script execution over the async WebView2 API.
    /// Every operation marshals onto the dispatcher that created the control;
    /// blocking callers resume via a nested message pump, so engine worker
    /// threads can call in directly.
    /// </summary>
    internal sealed class ScriptWebView : IDisposable {
        private const string RuntimeDownloadUrl = "https://go.microsoft.com/fwlink/p/?LinkId=2124703";
        private static readonly object EnvironmentLock = new object();
        private static Task<Microsoft.Web.WebView2.Core.CoreWebView2Environment> _sharedEnvironment;

        private readonly Microsoft.Web.WebView2.Wpf.WebView2 _control;
        private readonly Dispatcher _dispatcher;
        private TaskCompletionSource<bool> _navigationTcs;
        private volatile bool _coreReady;
        private volatile bool _runtimeMissing;
        private volatile bool _initFailed;
        private volatile bool _everNavigated;
        private volatile bool _lastNavigationCompleted = true;
        private bool _disposed;

        public ScriptWebView(Dispatcher ownerDispatcher) {
            _dispatcher = ownerDispatcher ?? Dispatcher.CurrentDispatcher;
            _control = new Microsoft.Web.WebView2.Wpf.WebView2();
        }

        /// <summary>Raised for top-level navigations so the owner can enforce URL policy.</summary>
        public event EventHandler<Microsoft.Web.WebView2.Core.CoreWebView2NavigationStartingEventArgs> NavigationStartingRequested;

        public Microsoft.Web.WebView2.Wpf.WebView2 Control => _control;

        public Microsoft.Web.WebView2.Core.CoreWebView2 Core => _control.CoreWebView2;

        /// <summary>Version of the WebView2 Runtime backing this view; empty until initialized.</summary>
        public string BrowserVersion { get; private set; } = string.Empty;

        /// <summary>True when the machine has no WebView2 Runtime; the view shows an error page instead.</summary>
        public bool RuntimeMissing { get { return _runtimeMissing; } }

        /// <summary>Fast cross-thread check: core is up and the latest top-level navigation finished loading.</summary>
        public bool IsDocumentReady {
            get { return _coreReady && !_runtimeMissing && _everNavigated && _lastNavigationCompleted; }
        }

        public static bool IsRuntimeAvailable() {
            try {
                Microsoft.Web.WebView2.Core.CoreWebView2Environment.GetAvailableBrowserVersionString();
                return true;
            }
            catch {
                return false;
            }
        }

        /// <summary>
        /// Bring the core online and run the first navigation. The provider is
        /// invoked once, after the runtime is confirmed, and returns the URI to
        /// load (or null to skip navigation). Blocks until the page has loaded.
        /// </summary>
        public void EnsureReady(Func<string> firstNavigationProvider = null) {
            if (_disposed)
                return;

            if (_dispatcher.CheckAccess()) {
                InitializeCore();
                if (RuntimeMissing || !_coreReady)
                    return;
                if (firstNavigationProvider != null && !_everNavigated) {
                    var uri = firstNavigationProvider();
                    if (!string.IsNullOrEmpty(uri))
                        Navigate(uri);
                }
                return;
            }

            try {
                _dispatcher.Invoke(new Action(() => EnsureReady(firstNavigationProvider)));
            }
            catch (TaskCanceledException) {
            }
        }

        /// <summary>Navigate the top-level document and block until loading finishes (bounded).</summary>
        public void Navigate(string url) {
            if (_disposed || string.IsNullOrEmpty(url))
                return;

            InvokeOnUi(() => {
                if (_control.CoreWebView2 == null)
                    return;
                _navigationTcs = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
                _everNavigated = true;
                _lastNavigationCompleted = false;
                _control.CoreWebView2.Navigate(url);
                PumpUntil(_navigationTcs.Task);
            });
        }

        /// <summary>
        /// Submit a script for execution without waiting for a result. Calls
        /// made from the owning thread reach the browser in submission order,
        /// which keeps ordered content inserts consistent.
        /// </summary>
        public void PostScript(string javaScript) {
            if (_disposed || javaScript == null)
                return;
            if (_dispatcher.CheckAccess())
                _control?.CoreWebView2?.ExecuteScriptAsync(javaScript);
            else
                _dispatcher.BeginInvoke(new Action(() => _control?.CoreWebView2?.ExecuteScriptAsync(javaScript)));
        }

        /// <summary>Execute a script and block until its JSON-encoded result arrives.</summary>
        public string EvalScript(string javaScript) {
            if (_disposed || javaScript == null)
                return "null";

            return InvokeOnUi(() => {
                var core = _control.CoreWebView2;
                if (core == null)
                    return "null";
                var task = core.ExecuteScriptAsync(javaScript);
                PumpUntil(task);
                return task.IsCompleted ? task.Result : "null";
            });
        }

        /// <summary>Show the Chromium print dialog for the current document.</summary>
        public void ShowPrintUi() {
            if (_disposed)
                return;
            InvokeOnUi(() => {
                try {
                    _control.CoreWebView2?.ShowPrintUI();
                }
                catch {
                }
            });
        }

        public void Dispose() {
            if (_disposed)
                return;
            _disposed = true;
            try {
                _control.Dispose();
            }
            catch {
            }
        }

        private void InitializeCore() {
            if (_coreReady || _disposed)
                return;
            if (_initFailed)
                throw new InvalidOperationException(
                    "WebView2 initialization failed earlier in this window; not retrying.");

            if (!IsRuntimeAvailable()) {
                _runtimeMissing = true;
                BrowserVersion = string.Empty;
                ShowRuntimeMissingDialog();
                _control.NavigateToString(RuntimeMissingPageHtml);
                return;
            }

            try {
                Task<Microsoft.Web.WebView2.Core.CoreWebView2Environment> envTask;
                lock (EnvironmentLock) {
                    if (_sharedEnvironment == null) {
                        var options = new Microsoft.Web.WebView2.Core.CoreWebView2EnvironmentOptions {
                            AdditionalBrowserArguments = BuildBrowserArguments()
                        };
                        _sharedEnvironment = Microsoft.Web.WebView2.Core.CoreWebView2Environment.CreateAsync(
                            null, GetUserDataFolder(), options);
                    }
                    envTask = _sharedEnvironment;
                }

                PumpUntil(envTask);
                if (!envTask.IsCompleted)
                    throw new InvalidOperationException("Timed out creating the WebView2 environment.");

                var initTask = _control.EnsureCoreWebView2Async(envTask.Result);
                PumpUntil(initTask);
                if (!initTask.IsCompleted || _control.CoreWebView2 == null)
                    throw new InvalidOperationException(
                        "Timed out initializing the WebView2 controller. "
                        + "The host window may never have been shown.",
                        Flatten(initTask));

                BrowserVersion = envTask.Result.BrowserVersionString;
            }
            catch {
                _initFailed = true;
                throw;
            }

            _control.CoreWebView2.NavigationStarting += OnNavigationStarting;
            _control.CoreWebView2.NavigationCompleted += OnNavigationCompleted;
            _control.CoreWebView2.Settings.AreDevToolsEnabled = false;
            _control.CoreWebView2.Settings.IsStatusBarEnabled = false;

            _coreReady = true;
        }

        private static Exception Flatten(Task task) {
            return task.Exception != null ? task.Exception.GetBaseException() : null;
        }

        /// <summary>
        /// Revit hosts its own Chromium (CefSharp/libcef) in this process. When
        /// the WebView2 runtime's Chromium major version differs from the host
        /// CEF's, both register the same Win32 window classes and libcef fails
        /// a window-creation CHECK, taking Revit down. The opt-in
        /// --edge-webview-unique-window-class switch makes WebView2 suffix its
        /// app-process window class names, removing the collision. Extra
        /// arguments can be appended for diagnostics via PYREVIT_WEBVIEW2_ARGS.
        /// </summary>
        private static string BuildBrowserArguments() {
            var args = "--edge-webview-unique-window-class";
            var extraArgs = Environment.GetEnvironmentVariable("PYREVIT_WEBVIEW2_ARGS");
            if (!string.IsNullOrWhiteSpace(extraArgs))
                args += " " + extraArgs.Trim();
            return args;
        }

        /// <summary>
        /// Per-Revit-version WebView2 profile folder. Sharing one folder across
        /// Revit versions makes every host connect to whichever browser process
        /// won the race, which can deadlock or fail-fast during startup when
        /// several versions run side by side; the runtime assembly name carries
        /// the Revit version, so each gets an isolated browser process.
        /// </summary>
        private static string GetUserDataFolder() {
            var versionFolder = "shared";
            try {
                var match = Regex.Match(
                    Path.GetFileNameWithoutExtension(typeof(ScriptWebView).Assembly.Location),
                    @"(\d{4})$");
                if (match.Success)
                    versionFolder = match.Groups[1].Value;
            }
            catch {
            }
            return Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "pyRevit",
                "WebView2",
                versionFolder
                );
        }

        private void OnNavigationStarting(object sender, Microsoft.Web.WebView2.Core.CoreWebView2NavigationStartingEventArgs e) {
            _lastNavigationCompleted = false;
            NavigationStartingRequested?.Invoke(this, e);
        }

        private void OnNavigationCompleted(object sender, Microsoft.Web.WebView2.Core.CoreWebView2NavigationCompletedEventArgs e) {
            _lastNavigationCompleted = true;
            var tcs = _navigationTcs;
            _navigationTcs = null;
            tcs?.TrySetResult(e.IsSuccess);
        }

        private T InvokeOnUi<T>(Func<T> action) {
            if (_dispatcher.CheckAccess())
                return action();
            return _dispatcher.Invoke(action);
        }

        private void InvokeOnUi(Action action) {
            InvokeOnUi<object>(() => { action(); return null; });
        }

        /// <summary>
        /// Block the calling thread until the task completes while keeping the
        /// owner dispatcher alive through a nested message pump. Returns when
        /// the task completes OR the timeout elapses; callers must re-check
        /// <see cref="Task.IsCompleted"/>.
        /// </summary>
        private static void PumpUntil(Task task, int timeoutMilliseconds = 60000) {
            if (task.IsCompleted) {
                ThrowIfFaulted(task);
                return;
            }

            var frame = new DispatcherFrame();
            task.ContinueWith(_ => frame.Continue = false, TaskScheduler.Default);
            using (var timeoutTimer = new Timer(
                    _ => frame.Dispatcher.BeginInvoke(new Action(() => frame.Continue = false)),
                    null, timeoutMilliseconds, Timeout.Infinite)) {
                Dispatcher.PushFrame(frame);
            }

            ThrowIfFaulted(task);
        }

        private static void ThrowIfFaulted(Task task) {
            if (task.IsFaulted && task.Exception != null)
                throw task.Exception.GetBaseException();
        }

        private static void ShowRuntimeMissingDialog() {
            try {
                var choice = System.Windows.MessageBox.Show(
                    "pyRevit output windows render with the Microsoft Edge WebView2 Runtime, "
                    + "which was not found on this machine.\n\n"
                    + "Download and install the free Evergreen Runtime now?",
                    "WebView2 Runtime Required",
                    System.Windows.MessageBoxButton.YesNo,
                    System.Windows.MessageBoxImage.Warning
                    );
                if (choice == System.Windows.MessageBoxResult.Yes)
                    System.Diagnostics.Process.Start(
                        new System.Diagnostics.ProcessStartInfo(RuntimeDownloadUrl) {
                            UseShellExecute = true
                        });
            }
            catch {
            }
        }

        private static string RuntimeMissingPageHtml {
            get {
                return "<!DOCTYPE html><html><head><meta charset=\"utf-8\" /><style>"
                    + "body{font-family:Segoe UI,sans-serif;background:#fff;color:#2c3e50;"
                    + "display:flex;align-items:center;justify-content:center;height:95vh;margin:0}"
                    + ".box{max-width:32rem;padding:2rem;border:1px solid #e0e0e0;border-radius:8px}"
                    + "h1{font-size:1.1rem;margin-top:0}code{background:#f4f4f4;padding:.1rem .3rem}"
                    + "</style></head><body><div class=\"box\">"
                    + "<h1>WebView2 Runtime not found</h1>"
                    + "<p>This output window renders with the Microsoft Edge WebView2 Runtime, "
                    + "which is missing on this machine.</p>"
                    + "<p>Install the <b>Evergreen Runtime</b> from "
                    + "<code>https://go.microsoft.com/fwlink/p/?LinkId=2124703</code>, "
                    + "then reopen the window.</p>"
                    + "</div></body></html>";
            }
        }
    }
}
