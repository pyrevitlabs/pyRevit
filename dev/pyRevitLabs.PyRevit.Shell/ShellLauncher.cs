using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Controls;
using System.Windows.Threading;
using Autodesk.Revit.UI;
using Microsoft.Scripting.Hosting;
using Microsoft.Scripting.Hosting.Shell;
using PythonConsoleControl;

namespace PyRevitLabs.PyRevit.Shell {
    /// <summary>
    /// Common host behavior for shell windows.
    /// </summary>
    internal interface IShellWindow {
        IronPythonConsoleControl ConsoleControl { get; }
        void ApplyTheme(bool useDarkTheme);
        void SetRevitAsWindowOwner();
    }

    /// <summary>
    /// Creates shell windows with a valid Revit execution context.
    /// </summary>
    internal static class ShellLauncher {
        public static InteractiveShellWindow ShowModal(UIApplication uiapp, IList<string> searchPaths)
            => ShowModalWindow<InteractiveShellWindow>(uiapp, searchPaths);

        public static InteractiveEditorWindow ShowModalEditor(UIApplication uiapp, IList<string> searchPaths)
            => ShowModalWindow<InteractiveEditorWindow>(uiapp, searchPaths);

        public static InteractiveShellWindow ShowModeless(UIApplication uiapp, IList<string> searchPaths)
            => ShowModelessWindow<InteractiveShellWindow>(uiapp, searchPaths);

        public static InteractiveEditorWindow ShowModelessEditor(UIApplication uiapp, IList<string> searchPaths)
            => ShowModelessWindow<InteractiveEditorWindow>(uiapp, searchPaths);

        static T ShowModalWindow<T>(UIApplication uiapp, IList<string> searchPaths) where T : System.Windows.Window, IShellWindow, new() {
            var gui = new T();
            gui.ApplyTheme(RevitThemeDetector.IsDarkTheme(uiapp));

            // A modal shell can reuse the command's live API context.
            var mainDispatcher = GetCurrentDispatcher();
            AttachAndDispatch(gui, uiapp, searchPaths, mainDispatcher, command => RunOnDispatcher(mainDispatcher, command));

            gui.SetRevitAsWindowOwner();
            gui.ShowDialog();
            return gui;
        }

        static T ShowModelessWindow<T>(UIApplication uiapp, IList<string> searchPaths) where T : System.Windows.Window, IShellWindow, new() {
            var gui = new T();
            gui.ApplyTheme(RevitThemeDetector.IsDarkTheme(uiapp));

            // A modeless shell needs an ExternalEvent to enter a valid API context.
            var mainDispatcher = GetCurrentDispatcher();
            var handler = new ShellExternalEventDispatcher(gui.ConsoleControl);
            var externalEvent = ExternalEvent.Create(handler);
            AttachAndDispatch(
                gui,
                uiapp,
                searchPaths,
                mainDispatcher,
                command => DispatchExternalEvent(handler, externalEvent, command)
            );

            gui.Title += " (modeless)";
            gui.SetRevitAsWindowOwner();
            gui.Show();
            return gui;
        }

        /// <summary>
        /// Creates a configured console for a dockable pane.
        /// </summary>
        public static UserControl CreateConfiguredConsole(UIApplication uiapp, IList<string> searchPaths) {
            var control = new IronPythonConsoleControl();
            control.ApplyTheme(RevitThemeDetector.IsDarkTheme(uiapp));
            ConfigureControl(control, uiapp, searchPaths, control, GetCurrentDispatcher());
            return control;
        }

        /// <summary>
        /// Creates a configured editor and console for a dockable pane.
        /// </summary>
        public static EditorView CreateConfiguredEditor(UIApplication uiapp, IList<string> searchPaths) {
            var editor = new EditorView();
            editor.ApplyTheme(RevitThemeDetector.IsDarkTheme(uiapp));
            ConfigureControl(editor.ConsoleControl, uiapp, searchPaths, editor, GetCurrentDispatcher());
            return editor;
        }

        static void ConfigureControl(IronPythonConsoleControl consoleControl, UIApplication uiapp, IList<string> searchPaths, object window, Dispatcher mainDispatcher) {
            var handler = new ShellExternalEventDispatcher(consoleControl);
            var externalEvent = ExternalEvent.Create(handler);

            consoleControl.WithConsoleHost(host => {
                // Install dispatch first so failed setup cannot leave an unsafe execution path.
                Action<Action> dispatch =
                    command => DispatchExternalEvent(handler, externalEvent, command);
                host.Console.SetCommandDispatcher(dispatch);
                host.Editor.SetCompletionDispatcher(dispatch);

                RunEngineSetupOnMainThread(host, uiapp, searchPaths, mainDispatcher);
                host.Console.ScriptScope.SetVariable("__window__", window);
                EnsureInteractiveBuiltins(host.Engine, host.Console.ScriptScope);
                EnsureSiteBuiltins(host.Engine, host.Console.ScriptScope);
            });
        }

        static Dispatcher GetCurrentDispatcher() {
            var dispatcher = Dispatcher.FromThread(Thread.CurrentThread);
            if (dispatcher == null)
                throw new InvalidOperationException(
                    "The pyRevit shell must be launched from a thread with a WPF dispatcher.");
            return dispatcher;
        }

        static void DispatchExternalEvent(
            ShellExternalEventDispatcher handler,
            ExternalEvent externalEvent,
            Action command
        ) {
            var request = handler.Enqueue(command);
            ExternalEventRequest response;
            try {
                response = externalEvent.Raise();
            }
            catch {
                if (!handler.Cancel(request))
                    request.Wait();
                throw;
            }

            if (response == ExternalEventRequest.Denied
                || response == ExternalEventRequest.TimedOut) {
                if (handler.Cancel(request))
                    throw new InvalidOperationException(
                        "Revit rejected the pyRevit shell ExternalEvent request: " + response);
            }

            request.Wait();
        }

        // Environment setup reads Revit-owned UI state and must run on its dispatcher.
        static void AttachAndDispatch(IShellWindow gui, UIApplication uiapp, IList<string> searchPaths, Dispatcher mainDispatcher, Action<Action> dispatch) {
            gui.ConsoleControl.WithConsoleHost(host => {
                host.Console.SetCommandDispatcher(dispatch);
                host.Editor.SetCompletionDispatcher(dispatch);

                RunEngineSetupOnMainThread(host, uiapp, searchPaths, mainDispatcher);
                host.Console.ScriptScope.SetVariable("__window__", gui);
                EnsureInteractiveBuiltins(host.Engine, host.Console.ScriptScope);
                EnsureSiteBuiltins(host.Engine, host.Console.ScriptScope);
            });
        }

        // Revit UI state can only be read from the main dispatcher.
        static void RunEngineSetupOnMainThread(PythonConsoleHost host, UIApplication uiapp, IList<string> searchPaths, Dispatcher mainDispatcher) {
            Exception setupError = null;
            if (mainDispatcher != null && !mainDispatcher.CheckAccess()) {
                mainDispatcher.Invoke(new Action(() => {
                    try { ConfigureEngineViaRuntime(host.Engine, uiapp, searchPaths); }
                    catch (Exception ex) { setupError = ex; }
                }));
            }
            else {
                try { ConfigureEngineViaRuntime(host.Engine, uiapp, searchPaths); }
                catch (Exception ex) { setupError = ex; }
            }
            if (setupError != null)
                host.Console.WriteLine(DescribeSetupError(setupError), Style.Error);
        }

        // Unwrap the reflection TargetInvocationException so the real failure (type, message,
        // stack) is shown in the shell instead of the generic "target of an invocation" wrapper.
        static string DescribeSetupError(Exception ex) {
            var real = (ex is TargetInvocationException tie && tie.InnerException != null)
                ? tie.InnerException
                : ex;
            return "pyRevit environment setup failed: ["
                + real.GetType().FullName + "] " + real.Message
                + Environment.NewLine + real.StackTrace;
        }

        // Preserve shell usability when environment setup cannot populate reserved builtins.
        static void EnsureInteractiveBuiltins(ScriptEngine engine, ScriptScope scope) {
            const string snippet =
"try: __execid__\nexcept NameError: __execid__ = ''\n" +
"try: __timestamp__\nexcept NameError: __timestamp__ = ''\n" +
"try: __cachedengine__\nexcept NameError: __cachedengine__ = False\n" +
"try: __cachedengineid__\nexcept NameError: __cachedengineid__ = None\n" +
"try: __scriptruntime__\nexcept NameError: __scriptruntime__ = None\n" +
"try: __revit__\nexcept NameError: __revit__ = None\n" +
"try: __commanddata__\nexcept NameError: __commanddata__ = None\n" +
"try: __elements__\nexcept NameError: __elements__ = None\n" +
"try: __uibutton__\nexcept NameError: __uibutton__ = None\n" +
"try: __commandpath__\nexcept NameError: __commandpath__ = ''\n" +
"try: __configcommandpath__\nexcept NameError: __configcommandpath__ = ''\n" +
"try: __commandname__\nexcept NameError: __commandname__ = 'Interactive Shell'\n" +
"try: __commandbundle__\nexcept NameError: __commandbundle__ = 'pyRevit Shell'\n" +
"try: __commandextension__\nexcept NameError: __commandextension__ = 'pyRevitCore'\n" +
"try: __commanduniqueid__\nexcept NameError: __commanduniqueid__ = 'pyrevit-interactive-shell'\n" +
"try: __commandcontrolid__\nexcept NameError: __commandcontrolid__ = 'pyrevit-interactive-shell'\n" +
"try: __forceddebugmode__\nexcept NameError: __forceddebugmode__ = False\n" +
"try: __shiftclick__\nexcept NameError: __shiftclick__ = False\n" +
"try: __result__\nexcept NameError: __result__ = {}\n" +
"try: __eventsender__\nexcept NameError: __eventsender__ = None\n" +
"try: __eventargs__\nexcept NameError: __eventargs__ = None\n";
            try {
                engine.Execute(snippet, scope);
            }
            catch {
                // Missing values surface through normal console errors.
            }
        }

        // The console banner advertises copyright/credits/license, but the host starts the
        // engine with empty search paths, so IronPython's own site import never resolves them.
        static void EnsureSiteBuiltins(ScriptEngine engine, ScriptScope scope) {
            const string snippet =
"try:\n" +
"    copyright\n" +
"except NameError:\n" +
"    try:\n" +
"        import site\n" +
"        site.setcopyright()\n" +
"    except Exception:\n" +
"        pass\n";
            try {
                engine.Execute(snippet, scope);
            }
            catch {
                // A shell without the informational banner objects is still usable.
            }
        }

        // Resolve configuration dynamically to stay compatible with the loaded runtime version.
        internal static void ConfigureEngineViaRuntime(ScriptEngine engine, UIApplication uiapp, IList<string> searchPaths) {
            var runtimeAsm = AppDomain.CurrentDomain.GetAssemblies().FirstOrDefault(a => {
                var name = a.GetName().Name;
                return name.StartsWith("pyRevitLabs.PyRevit.Runtime", StringComparison.Ordinal)
                       && !name.Contains("Shared");
            });
            var configure = runtimeAsm
                ?.GetType("PyRevitLabs.PyRevit.Runtime.InteractiveEngine")
                ?.GetMethod("ConfigureIronPythonEngine", BindingFlags.Public | BindingFlags.Static);
            if (configure == null)
                throw new InvalidOperationException(
                    "Could not find pyRevit runtime InteractiveEngine.ConfigureIronPythonEngine; "
                    + "is the pyRevit runtime loaded?");
            configure.Invoke(null, new object[] { engine, uiapp, searchPaths });
        }

        // Poll the dispatcher operation so a Ctrl+C keyboard interrupt can break a long run.
        static void RunOnDispatcher(Dispatcher dispatcher, Action command) {
            if (command == null)
                return;
            if (dispatcher == null)
                throw new ArgumentNullException(nameof(dispatcher));
            var operation = dispatcher.BeginInvoke(DispatcherPriority.Normal, command);
            while (operation.Status != DispatcherOperationStatus.Completed)
                operation.Wait(TimeSpan.FromSeconds(1));
        }
    }

    /// <summary>
    /// Tracks a shell command until Revit has executed it.
    /// </summary>
    internal sealed class ShellExternalEventRequest {
        readonly TaskCompletionSource<bool> _completed =
            new TaskCompletionSource<bool>(
                TaskCreationOptions.RunContinuationsAsynchronously);

        public ShellExternalEventRequest(Action command) {
            Command = command ?? throw new ArgumentNullException(nameof(command));
        }

        public Action Command { get; }

        public void Complete() {
            _completed.TrySetResult(true);
        }

        public void Wait() {
            _completed.Task.GetAwaiter().GetResult();
        }
    }

    internal sealed class ShellExternalEventDispatcher : IExternalEventHandler {
        readonly IronPythonConsoleControl _consoleControl;
        readonly object _requestsLock = new object();
        readonly List<ShellExternalEventRequest> _requests =
            new List<ShellExternalEventRequest>();

        public ShellExternalEventDispatcher(IronPythonConsoleControl consoleControl) {
            _consoleControl = consoleControl;
        }

        public ShellExternalEventRequest Enqueue(Action command) {
            var request = new ShellExternalEventRequest(command);
            lock (_requestsLock) {
                _requests.Add(request);
            }
            return request;
        }

        public bool Cancel(ShellExternalEventRequest request) {
            lock (_requestsLock) {
                return _requests.Remove(request);
            }
        }

        bool TryDequeue(out ShellExternalEventRequest request) {
            lock (_requestsLock) {
                if (_requests.Count == 0) {
                    request = null;
                    return false;
                }
                request = _requests[0];
                _requests.RemoveAt(0);
                return true;
            }
        }

        public void Execute(UIApplication app) {
            ShellExternalEventRequest request;
            while (TryDequeue(out request)) {
                try {
                    request.Command();
                }
                catch (Exception ex) {
                    _consoleControl.WithConsoleHost(host => {
                        var formatter = host.Engine.GetService<ExceptionOperations>();
                        host.Console.WriteLine(formatter.FormatException(ex), Style.Error);
                    });
                }
                finally {
                    request.Complete();
                }
            }
        }

        public string GetName() {
            return "pyRevit Interactive Shell";
        }
    }
}
