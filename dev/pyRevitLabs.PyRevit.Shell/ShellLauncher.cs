using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Threading;
using System.Windows.Controls;
using System.Windows.Threading;
using Autodesk.Revit.UI;
using Microsoft.Scripting.Hosting;
using Microsoft.Scripting.Hosting.Shell;
using PythonConsoleControl;

namespace PyRevitLabs.PyRevit.Shell {
    /// <summary>
    /// Common surface the launcher needs from any shell window (console-only or editor): the
    /// console control to wire the engine onto, plus theme/owner helpers. Lets the modal/modeless
    /// paths be generic over the concrete window type.
    /// </summary>
    internal interface IShellWindow {
        IronPythonConsoleControl ConsoleControl { get; }
        void ApplyTheme(bool useDarkTheme);
        void SetRevitAsWindowOwner();
    }

    /// <summary>
    /// Builds and shows the interactive shell window and wires its REPL to a valid Revit API
    /// context. Reached through <see cref="Shell"/> so the assembly resolver is installed first.
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

            // Modal: run typed code on this (the command's) thread. ShowDialog keeps pumping it,
            // so every statement executes in the live API context the shell was opened from.
            var mainDispatcher = Dispatcher.FromThread(Thread.CurrentThread);
            var dispatcher = mainDispatcher;
            AttachAndDispatch(gui, uiapp, searchPaths, mainDispatcher, command => RunOnDispatcher(dispatcher, command));

            gui.SetRevitAsWindowOwner();
            gui.ShowDialog();
            return gui;
        }

        static T ShowModelessWindow<T>(UIApplication uiapp, IList<string> searchPaths) where T : System.Windows.Window, IShellWindow, new() {
            var gui = new T();
            gui.ApplyTheme(RevitThemeDetector.IsDarkTheme(uiapp));

            // Modeless: marshal each statement into a valid API context via an ExternalEvent so
            // Revit stays interactive while the shell is open.
            var mainDispatcher = Dispatcher.FromThread(Thread.CurrentThread);
            var commandCompleted = new AutoResetEvent(false);
            var handler = new ShellExternalEventDispatcher(gui.ConsoleControl, commandCompleted);
            var externalEvent = ExternalEvent.Create(handler);
            AttachAndDispatch(gui, uiapp, searchPaths, mainDispatcher, command => {
                handler.Enqueue(command);
                externalEvent.Raise();
                commandCompleted.WaitOne();
            });

            gui.Title += " (modeless)";
            gui.SetRevitAsWindowOwner();
            gui.Show();
            return gui;
        }

        /// <summary>
        /// Create a configured console control for a dockable pane. Same environment and modeless
        /// dispatch as <see cref="ShowModelessWindow"/>, but returns the bare control so pyRevit can host
        /// it inside its own <c>WPFPanel</c>-based dockable pane.
        /// </summary>
        public static UserControl CreateConfiguredConsole(UIApplication uiapp, IList<string> searchPaths) {
            var control = new IronPythonConsoleControl();
            control.ApplyTheme(RevitThemeDetector.IsDarkTheme(uiapp));
            ConfigureControl(control, uiapp, searchPaths, control, Dispatcher.FromThread(Thread.CurrentThread));
            return control;
        }

        /// <summary>
        /// Create a configured editor (AvalonEdit + console) for a dockable pane. Same environment
        /// and modeless dispatch as <see cref="ShowModelessWindow"/>, but returns the bare
        /// <see cref="EditorView"/> so pyRevit can host it inside its own <c>WPFPanel</c>-based
        /// dockable pane. The editor's Run sends its buffer to the same REPL, so statements run in
        /// a valid Revit API context through the ExternalEvent below.
        /// </summary>
        public static EditorView CreateConfiguredEditor(UIApplication uiapp, IList<string> searchPaths) {
            var editor = new EditorView();
            editor.ApplyTheme(RevitThemeDetector.IsDarkTheme(uiapp));
            ConfigureControl(editor.ConsoleControl, uiapp, searchPaths, editor, Dispatcher.FromThread(Thread.CurrentThread));
            return editor;
        }

        // Shared by the window-based and dockable shells: configure the engine and wire the
        // modeless dispatch (ExternalEvent) onto an already-created console control.
        static void ConfigureControl(IronPythonConsoleControl consoleControl, UIApplication uiapp, IList<string> searchPaths, object window, Dispatcher mainDispatcher) {
            var commandCompleted = new AutoResetEvent(false);
            var handler = new ShellExternalEventDispatcher(consoleControl, commandCompleted);
            var externalEvent = ExternalEvent.Create(handler);

            consoleControl.WithConsoleHost(host => {
                // Wire dispatch first so statements run in a valid Revit API context even if the
                // environment setup below throws.
                Action<Action> dispatch = command => {
                    handler.Enqueue(command);
                    externalEvent.Raise();
                    commandCompleted.WaitOne();
                };
                host.Console.SetCommandDispatcher(dispatch);
                host.Editor.SetCompletionDispatcher(dispatch);

                RunEngineSetupOnMainThread(host, uiapp, searchPaths, mainDispatcher);
                host.Console.ScriptScope.SetVariable("__window__", window);
                EnsureInteractiveBuiltins(host.Engine, host.Console.ScriptScope);
            });
        }

        // Give the console's engine the full pyRevit environment, then wire its REPL dispatcher.
        // Dispatch is installed *before* ConfigureEngineViaRuntime so the REPL always lands in a
        // valid API context. The environment setup runs on Revit's main UI thread (see
        // RunEngineSetupOnMainThread) because InjectBuiltins touches the Ribbon, which only the
        // main thread may access.
        static void AttachAndDispatch(IShellWindow gui, UIApplication uiapp, IList<string> searchPaths, Dispatcher mainDispatcher, Action<Action> dispatch) {
            gui.ConsoleControl.WithConsoleHost(host => {
                host.Console.SetCommandDispatcher(dispatch);
                host.Editor.SetCompletionDispatcher(dispatch);

                RunEngineSetupOnMainThread(host, uiapp, searchPaths, mainDispatcher);
                host.Console.ScriptScope.SetVariable("__window__", gui);
                EnsureInteractiveBuiltins(host.Engine, host.Console.ScriptScope);
            });
        }

        // ConfigureEngineViaRuntime calls InjectBuiltins, which reads ScriptRuntime.UIControl ->
        // ComponentManager.Ribbon -> RibbonControl.Tabs. The Ribbon is a WPF object owned by Revit's
        // main UI thread, so calling it from the REPL's background thread throws
        // InvalidOperationException ("calling thread cannot access this object"). Marshal the setup
        // onto the main thread (captured at shell launch) so InjectBuiltins completes normally and
        // the reserved builtins get their real values. Any failure is reported to the console.
        static void RunEngineSetupOnMainThread(PythonConsoleHost host, UIApplication uiapp, IList<string> searchPaths, Dispatcher mainDispatcher) {
            Exception setupError = null;
            if (mainDispatcher != null && !mainDispatcher.CheckAccess()) {
                mainDispatcher.Invoke(new Action(() => {
                    try { ConfigureEngineViaRuntime(host.Engine, uiapp, searchPaths); }
                    catch (Exception ex) { setupError = ex; }
                }));
            }
            else {
                // Already on the main thread (or no dispatcher captured): run inline.
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

        // InjectBuiltins can still abort before the reserved pyrevit builtins (e.g. __shiftclick__)
        // are set if setup runs off-thread or fails; provide safe defaults for any that are missing
        // so user scripts that rely on them work in the interactive shell. Existing values (set by
        // InjectBuiltins on the main thread) are left untouched.
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
                // Best effort: the REPL still works without these defaults; user scripts that
                // reference a missing reserved builtin will surface the NameError as before.
            }
        }

        // The full builtins live in the loaded per-version pyRevit runtime. This Revit-agnostic
        // shell can't reference a specific runtime version at compile time, so reach
        // InteractiveEngine by reflection; the engine object is the same DLR-fork identity as the
        // loaded runtime, so the call binds cleanly. Shared by the window-based and dockable shells.
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
            var operation = dispatcher.BeginInvoke(DispatcherPriority.Normal, command);
            while (operation.Status != DispatcherOperationStatus.Completed)
                operation.Wait(TimeSpan.FromSeconds(1));
        }
    }

    /// <summary>
    /// Runs queued REPL statements inside Revit's API context for the modeless and dockable
    /// shells. Reports failures back into the owning console control.
    /// </summary>
    public class ShellExternalEventDispatcher : IExternalEventHandler {
        readonly IronPythonConsoleControl _consoleControl;
        readonly Queue<Action> _commands = new Queue<Action>();
        readonly AutoResetEvent _commandCompleted;

        public ShellExternalEventDispatcher(IronPythonConsoleControl consoleControl, AutoResetEvent commandCompleted) {
            _consoleControl = consoleControl;
            _commandCompleted = commandCompleted;
        }

        public void Enqueue(Action command) {
            _commands.Enqueue(command);
        }

        public void Execute(UIApplication app) {
            while (_commands.Count > 0) {
                var command = _commands.Dequeue();
                try {
                    command();
                }
                catch (Exception ex) {
                    _consoleControl.WithConsoleHost(host => {
                        var formatter = host.Engine.GetService<ExceptionOperations>();
                        host.Console.WriteLine(formatter.FormatException(ex), Style.Error);
                    });
                }
                finally {
                    _commandCompleted.Set();
                }
            }
        }

        public string GetName() {
            return "pyRevit Interactive Shell";
        }
    }
}
