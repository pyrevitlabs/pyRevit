using System;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Threading;
using Microsoft.Web.WebView2.Core;
using PyRevitLabs.PyRevit.Renderer;
using WebView2Control = Microsoft.Web.WebView2.Wpf.WebView2;

namespace PyRevitLabs.PyRevit.WebView2 {
    /// <summary>
    /// Chromium renderer behind a script output window. Owns WebView2 control
    /// lifecycle, environment/user-data-folder setup, runtime availability
    /// handling, and script execution over the async WebView2 API. Every
    /// operation marshals onto the dispatcher that created the control.
    ///
    /// Warning: initialization and content writes never pump. pyRevit drives
    /// them from Revit API callbacks during session load, where a nested
    /// dispatcher frame re-enters Revit's message loop mid-initialization and
    /// terminates the host. Only the explicitly synchronous read API
    /// (<see cref="WaitUntilReady"/>, <see cref="EvalScript"/>) pumps, and only
    /// from user commands.
    /// </summary>
    public sealed class WebView2ScriptRenderer : IScriptRenderer {
        private static readonly object EnvironmentLock = new object();
        private static Task<CoreWebView2Environment> _sharedEnvironment;
        private static int _runtimeMissingPromptShown;
        private static Exception _loaderFolderError;

        static WebView2ScriptRenderer() {
            PinLoaderFolder();
        }

        private readonly WebView2Control _control;
        private readonly Dispatcher _dispatcher;
        private readonly string _profileFolder;
        private TaskCompletionSource<bool> _navigationTcs;
        private readonly TaskCompletionSource<bool> _readyTcs =
            new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        private volatile bool _coreReady;
        private volatile RendererFailure _failure = RendererFailure.None;
        private volatile bool _initFailed;
        private volatile bool _initStarted;
        private volatile bool _everNavigated;
        private volatile bool _lastNavigationCompleted = true;
        private bool _disposed;

        /// <summary>
        /// Creates the renderer.
        /// </summary>
        /// <param name="ownerDispatcher">Dispatcher owning the renderer control.</param>
        /// <param name="profileFolder">
        /// Name of the per-host browser profile folder. Every Revit version gets
        /// its own so that side-by-side hosts do not share a browser process.
        /// </param>
        public WebView2ScriptRenderer(Dispatcher ownerDispatcher, string profileFolder) {
            _dispatcher = ownerDispatcher ?? Dispatcher.CurrentDispatcher;
            _profileFolder = string.IsNullOrEmpty(profileFolder) ? "shared" : profileFolder;
            _control = new WebView2Control();
        }

        /// <inheritdoc />
        public event EventHandler<RendererNavigationStartingEventArgs> NavigationStartingRequested;

        /// <inheritdoc />
        public event EventHandler DocumentReady;

        /// <inheritdoc />
        public event EventHandler<RendererMessageReceivedEventArgs> MessageReceived;

        /// <inheritdoc />
        public FrameworkElement Control => _control;

        /// <inheritdoc />
        public string BrowserVersion { get; private set; } = string.Empty;

        /// <inheritdoc />
        public RendererFailure Failure { get { return _failure; } }

        /// <inheritdoc />
        public bool InitializationFailed { get { return _initFailed; } }

        /// <inheritdoc />
        public Task ReadyTask { get { return _readyTcs.Task; } }

        /// <inheritdoc />
        public bool IsDocumentReady {
            get { return _coreReady && _failure == RendererFailure.None && _everNavigated && _lastNavigationCompleted; }
        }

        /// <inheritdoc />
        public bool IsCoreReady { get { return _coreReady; } }

        /// <inheritdoc />
        public void EnsureReady(Func<string> firstNavigationProvider) {
            if (_disposed)
                return;

            if (_dispatcher.CheckAccess()) {
                BeginInitialize(firstNavigationProvider);
                return;
            }

            try {
                _dispatcher.BeginInvoke(new Action(() => EnsureReady(firstNavigationProvider)));
            }
            catch (TaskCanceledException) {
            }
        }

        /// <inheritdoc />
        public void WaitUntilReady(int timeoutMilliseconds = 30000) {
            if (_disposed || _failure != RendererFailure.None || _initFailed || IsDocumentReady)
                return;

            if (!_dispatcher.CheckAccess()) {
                try {
                    _dispatcher.Invoke(new Action(() => WaitUntilReady(timeoutMilliseconds)));
                }
                catch (TaskCanceledException) {
                }
                return;
            }

            if (!_coreReady)
                PumpUntil(_readyTcs.Task, timeoutMilliseconds);

            if (_disposed || _failure != RendererFailure.None || _initFailed)
                return;

            var navigation = _navigationTcs;
            if (navigation != null && !IsDocumentReady)
                PumpUntil(navigation.Task, timeoutMilliseconds);
        }

        /// <inheritdoc />
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
            });
        }

        /// <inheritdoc />
        public void PostScript(string javaScript) {
            if (_disposed || javaScript == null)
                return;
            if (_dispatcher.CheckAccess())
                _control?.CoreWebView2?.ExecuteScriptAsync(javaScript);
            else
                _dispatcher.BeginInvoke(new Action(() => _control?.CoreWebView2?.ExecuteScriptAsync(javaScript)));
        }

        /// <inheritdoc />
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

        /// <inheritdoc />
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

        /// <inheritdoc />
        public bool PostMessage(string json) {
            if (_disposed || !_coreReady || string.IsNullOrEmpty(json))
                return false;
            if (_dispatcher.CheckAccess())
                SendMessage(json);
            else
                _dispatcher.BeginInvoke(new Action(() => SendMessage(json)));
            return true;
        }

        /// <inheritdoc />
        public void Dispose() {
            if (_disposed)
                return;
            _disposed = true;
            _readyTcs.TrySetResult(false);
            try {
                InvokeOnUi(() => {
                    var core = _control.CoreWebView2;
                    if (core != null) {
                        core.NavigationStarting -= OnNavigationStarting;
                        core.NavigationCompleted -= OnNavigationCompleted;
                        core.WebMessageReceived -= OnWebMessageReceived;
                    }
                    _control.Dispose();
                });
            }
            catch {
            }
        }

        /// <summary>
        /// Start initialization once. Runs on the owner dispatcher and returns immediately.
        ///
        /// Important: the controller is created only after the control is loaded.
        /// The WPF control builds its child HWND as part of entering the visual
        /// tree, and a controller created before that attaches the browser to a
        /// window that does not exist yet, leaving the view black.
        /// </summary>
        private void BeginInitialize(Func<string> firstNavigationProvider) {
            if (_disposed || _failure != RendererFailure.None || _initFailed)
                return;

            if (_coreReady) {
                RunFirstNavigation(firstNavigationProvider);
                return;
            }

            if (_initStarted)
                return;
            _initStarted = true;

            var runtimeState = _loaderFolderError != null ? RuntimeState.Broken : ProbeRuntime();
            if (runtimeState != RuntimeState.Available) {
                _failure = runtimeState == RuntimeState.Missing
                    ? RendererFailure.RuntimeMissing
                    : RendererFailure.BrokenDeployment;
                BrowserVersion = string.Empty;
                _readyTcs.TrySetResult(false);
                if (runtimeState == RuntimeState.Missing) {
                    _dispatcher.BeginInvoke(
                        new Action(ShowRuntimeMissingDialog),
                        DispatcherPriority.ApplicationIdle);
                }
                return;
            }

            ScriptRendererLog.Debug(
                "init requested: loaded={0} size={1}x{2} visible={3}",
                _control.IsLoaded, _control.ActualWidth, _control.ActualHeight, _control.IsVisible);

            if (!_control.IsLoaded) {
                System.Windows.RoutedEventHandler onLoaded = null;
                onLoaded = (s, e) => {
                    _control.Loaded -= onLoaded;
                    ScriptRendererLog.Debug(
                        "control loaded: size={0}x{1}", _control.ActualWidth, _control.ActualHeight);
                    if (_disposed)
                        return;
                    StartInitialization(firstNavigationProvider);
                };
                _control.Loaded += onLoaded;
                return;
            }

            StartInitialization(firstNavigationProvider);
        }

        /// <summary>
        /// Start the async initialization from inside a dispatcher operation.
        ///
        /// This must not be called directly, even from the UI thread. pyRevit
        /// reaches this from Revit API callbacks where SynchronizationContext
        /// .Current is null -- WPF only installs the DispatcherSynchronizationContext
        /// while a dispatcher operation runs. Starting the async method without
        /// it makes WebView2's own internal awaits resume on the thread pool,
        /// where SyncControllerWithParentWindow touches the control and dies on
        /// Dispatcher.VerifyAccess. Going through InvokeAsync guarantees the
        /// context for this method and everything it awaits.
        /// </summary>
        private void StartInitialization(Func<string> firstNavigationProvider) {
            _dispatcher.InvokeAsync(() => {
                if (_disposed)
                    return;
                var pending = InitializeCoreAsync(firstNavigationProvider);
            });
        }

        /// <summary>
        /// Bring the environment and controller up, then run the first navigation.
        /// Faults are recorded on <see cref="InitializationFailed"/>, never
        /// rethrown: nothing awaits this task, so an escaping exception would
        /// reach the dispatcher unhandled and terminate the host.
        ///
        /// Invariant: the first navigation starts before <see cref="ReadyTask"/>
        /// completes, so a waiter always observes the pending navigation instead
        /// of racing ahead of the initial page. A faulted shared environment is
        /// evicted so a transient failure does not poison every later window in
        /// this Revit session.
        /// </summary>
        private async Task InitializeCoreAsync(Func<string> firstNavigationProvider) {
            try {
                Task<CoreWebView2Environment> envTask;
                lock (EnvironmentLock) {
                    if (_sharedEnvironment == null) {
                        var options = new CoreWebView2EnvironmentOptions {
                            AdditionalBrowserArguments = BuildBrowserArguments()
                        };
                        _sharedEnvironment = CoreWebView2Environment.CreateAsync(
                            null, GetUserDataFolder(), options);
                    }
                    envTask = _sharedEnvironment;
                }

                CoreWebView2Environment environment;
                try {
                    environment = await envTask;
                }
                catch {
                    lock (EnvironmentLock) {
                        if (ReferenceEquals(_sharedEnvironment, envTask))
                            _sharedEnvironment = null;
                    }
                    throw;
                }

                if (_disposed)
                    return;

                ScriptRendererLog.Debug(
                    "environment ready (runtime {0}); creating controller",
                    environment.BrowserVersionString);
                await _control.EnsureCoreWebView2Async(environment);
                LogLoadContexts();
                ScriptRendererLog.Debug(
                    "controller created: core={0} size={1}x{2}",
                    _control.CoreWebView2 != null, _control.ActualWidth, _control.ActualHeight);

                if (_disposed)
                    return;
                if (_control.CoreWebView2 == null)
                    throw new InvalidOperationException("WebView2 controller was not created.");

                BrowserVersion = environment.BrowserVersionString;

                _control.CoreWebView2.NavigationStarting += OnNavigationStarting;
                _control.CoreWebView2.NavigationCompleted += OnNavigationCompleted;
                _control.CoreWebView2.WebMessageReceived += OnWebMessageReceived;
                _control.CoreWebView2.Settings.AreDevToolsEnabled = false;
                _control.CoreWebView2.Settings.IsStatusBarEnabled = false;

                _coreReady = true;

                RunFirstNavigation(firstNavigationProvider);
                _readyTcs.TrySetResult(true);
                RaiseDocumentReady();
            }
            catch (Exception ex) {
                _initFailed = true;
                _readyTcs.TrySetResult(false);
                ScriptRendererLog.Error(
                    "WebView2 initialization failed; this output window will not render. {0}", ex);
            }
        }

#if !NETFRAMEWORK
        /// <summary>
        /// Records the load context of the WebView2 assemblies so that the
        /// isolation from the host process is observable in the runtime log.
        /// </summary>
        private static void LogLoadContexts() {
            LogLoadContext("Microsoft.Web.WebView2.Core", typeof(CoreWebView2Environment).Assembly);
            LogLoadContext("Microsoft.Web.WebView2.Wpf", typeof(WebView2Control).Assembly);
            LogLoadContext("pyRevitLabs.PyRevit.WebView2", typeof(WebView2ScriptRenderer).Assembly);
        }

        private static void LogLoadContext(string label, System.Reflection.Assembly assembly) {
            var context = System.Runtime.Loader.AssemblyLoadContext.GetLoadContext(assembly);
            ScriptRendererLog.Debug(
                "{0} version {1} loaded into load context '{2}'",
                label,
                assembly.GetName().Version,
                context == null ? "<none>" : context.Name);
        }
#else
        private static void LogLoadContexts() {
        }
#endif

        private void RunFirstNavigation(Func<string> firstNavigationProvider) {
            if (firstNavigationProvider == null || _everNavigated || !_coreReady || _disposed)
                return;
            var uri = firstNavigationProvider();
            ScriptRendererLog.Debug("first navigation: {0}", uri ?? "<none>");
            if (!string.IsNullOrEmpty(uri))
                Navigate(uri);
        }

        private void RaiseDocumentReady() {
            ScriptRendererLog.Debug(
                "document ready check: ready={0} core={1} navigated={2} navigationSettled={3}",
                IsDocumentReady, _coreReady, _everNavigated, _lastNavigationCompleted);
            if (_disposed || !IsDocumentReady)
                return;
            var handler = DocumentReady;
            if (handler != null)
                handler(this, EventArgs.Empty);
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
        /// Per-host WebView2 profile folder. Sharing one folder across Revit
        /// versions makes every host connect to whichever browser process won
        /// the race, which can deadlock or fail-fast during startup when
        /// several versions run side by side.
        /// </summary>
        private string GetUserDataFolder() {
            return Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "pyRevit",
                "WebView2",
                _profileFolder
                );
        }

        /// <summary>
        /// Pins the native loader to the folder this renderer was loaded from.
        ///
        /// The core probes for <c>WebView2Loader.dll</c> itself before falling
        /// back to the managed resolution path, so the load-context override
        /// alone cannot guarantee which copy wins when the host process or the
        /// host search path offers another one. A copy from a different WebView2
        /// version is what breaks the environment at startup, which is why the
        /// folder is stated rather than probed.
        ///
        /// Important: the core ignores this setting once it has loaded the
        /// loader, so it runs from the type initializer, before any environment
        /// API is reachable.
        /// </summary>
        private static void PinLoaderFolder() {
            try {
                var folder = Path.GetDirectoryName(typeof(WebView2ScriptRenderer).Assembly.Location);
                if (string.IsNullOrEmpty(folder))
                    throw new InvalidOperationException(
                        "The renderer assembly has no location, so the folder holding the native "
                        + "WebView2 loader is unknown.");

                CoreWebView2Environment.SetLoaderDllFolderPath(folder);
            }
            catch (Exception ex) {
                ScriptRendererLog.Error(
                    "could not pin the WebView2 loader folder: {0}", ex.Message);
                if (LoaderFolderIsIsolated)
                    _loaderFolderError = ex;
            }
        }

        /// <summary>
        /// True when the renderer owns its WebView2 core, which makes the
        /// loader pin mandatory: without it the core can pick up a loader from
        /// a different version and the environment start fails. On the .NET
        /// Framework the host shares its core with pyRevit and may already have
        /// loaded the loader, so the pin is best effort and a failure leaves
        /// the previous resolution in place.
        /// </summary>
        private static bool LoaderFolderIsIsolated {
            get {
#if NETFRAMEWORK
                return false;
#else
                return true;
#endif
            }
        }

        /// <summary>
        /// Distinguishes an absent Evergreen runtime, which the user can fix by
        /// installing it, from a broken deployment, which the user cannot.
        /// Treating the second as the first sends people to install a runtime
        /// they already have while the real fault stays hidden.
        /// </summary>
        private static RuntimeState ProbeRuntime() {
            try {
                CoreWebView2Environment.GetAvailableBrowserVersionString();
                return RuntimeState.Available;
            }
            catch (WebView2RuntimeNotFoundException) {
                return RuntimeState.Missing;
            }
            catch (Exception ex) {
                ScriptRendererLog.Error(
                    "the WebView2 stack could not start: {0}: {1}", ex.GetType().Name, ex.Message);
                return RuntimeState.Broken;
            }
        }

        /// <summary>
        /// Invariant: does not touch the navigation-settled flag, which
        /// <see cref="Navigate"/> owns. Navigations this class did not start —
        /// revit:// deep links, blocked http — are cancelled by the policy
        /// handler, and clearing the flag here would strand the view as "not
        /// ready" whenever a cancelled navigation never reports completion.
        /// </summary>
        private void OnNavigationStarting(object sender, CoreWebView2NavigationStartingEventArgs e) {
            var args = new RendererNavigationStartingEventArgs(e.Uri);
            NavigationStartingRequested?.Invoke(this, args);
            e.Cancel = args.Cancel;
        }

        private void OnNavigationCompleted(object sender, CoreWebView2NavigationCompletedEventArgs e) {
            ScriptRendererLog.Debug(
                "navigation completed: success={0} status={1}", e.IsSuccess, e.WebErrorStatus);
            _lastNavigationCompleted = true;
            var tcs = _navigationTcs;
            _navigationTcs = null;
            tcs?.TrySetResult(e.IsSuccess);
            RaiseDocumentReady();
        }

        private void OnWebMessageReceived(object sender, CoreWebView2WebMessageReceivedEventArgs e) {
            var handler = MessageReceived;
            if (handler == null)
                return;
            string text = null;
            try {
                text = e.TryGetWebMessageAsString();
            }
            catch (ArgumentException) {
            }
            handler(this, new RendererMessageReceivedEventArgs(e.WebMessageAsJson, text));
        }

        private void SendMessage(string json) {
            try {
                _control?.CoreWebView2?.PostWebMessageAsJson(json);
            }
            catch (Exception ex) {
                ScriptRendererLog.Error("could not post a message to the page. {0}", ex.Message);
            }
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
            if (Interlocked.Exchange(ref _runtimeMissingPromptShown, 1) != 0)
                return;
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
                        new System.Diagnostics.ProcessStartInfo(ScriptRendererConsts.RuntimeDownloadUrl) {
                            UseShellExecute = true
                        });
            }
            catch {
            }
        }

        private enum RuntimeState {
            Available,
            Missing,
            Broken,
        }
    }
}
