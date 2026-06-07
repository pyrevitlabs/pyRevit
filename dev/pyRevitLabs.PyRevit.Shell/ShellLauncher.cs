using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Threading;
using System.Windows.Threading;
using Autodesk.Revit.UI;
using Microsoft.Scripting.Hosting;
using Microsoft.Scripting.Hosting.Shell;
using PythonConsoleControl;

namespace PyRevitLabs.PyRevit.Shell {
    /// <summary>
    /// Builds and shows the interactive shell window and wires its REPL to a valid Revit API
    /// context. Reached through <see cref="Shell"/> so the assembly resolver is installed first.
    /// </summary>
    internal static class ShellLauncher {
        public static InteractiveShellWindow ShowModal(UIApplication uiapp, IList<string> searchPaths) {
            var gui = new InteractiveShellWindow();
            AttachEnvironment(gui, uiapp, searchPaths);

            // Modal: run typed code on this (the command's) thread. ShowDialog keeps pumping it,
            // so every statement executes in the live API context the shell was opened from.
            var dispatcher = Dispatcher.FromThread(Thread.CurrentThread);
            gui.ConsoleControl.WithConsoleHost(host => {
                host.Console.SetCommandDispatcher(command => RunOnDispatcher(dispatcher, command));
                host.Editor.SetCompletionDispatcher(command => RunOnDispatcher(dispatcher, command));
            });

            gui.SetRevitAsWindowOwner();
            gui.ShowDialog();
            return gui;
        }

        public static InteractiveShellWindow ShowModeless(UIApplication uiapp, IList<string> searchPaths) {
            var gui = new InteractiveShellWindow();
            AttachEnvironment(gui, uiapp, searchPaths);

            // Modeless: marshal each statement into a valid API context via an ExternalEvent so
            // Revit stays interactive while the shell is open.
            var commandCompleted = new AutoResetEvent(false);
            var handler = new ShellExternalEventDispatcher(gui, commandCompleted);
            var externalEvent = ExternalEvent.Create(handler);
            gui.ConsoleControl.WithConsoleHost(host => {
                Action<Action> dispatch = command => {
                    handler.Enqueue(command);
                    externalEvent.Raise();
                    commandCompleted.WaitOne();
                };
                host.Console.SetCommandDispatcher(dispatch);
                host.Editor.SetCompletionDispatcher(dispatch);
            });

            gui.Title += " (modeless)";
            gui.SetRevitAsWindowOwner();
            gui.Show();
            return gui;
        }

        // Give the console's engine the full pyRevit environment (configured-fork engine, all
        // builtins incl. __scriptruntime__, RevitAPI, stdlib and the caller's sys.path) so the REPL
        // behaves like a normal pyRevit script.
        static void AttachEnvironment(InteractiveShellWindow gui, UIApplication uiapp, IList<string> searchPaths) {
            gui.ConsoleControl.WithConsoleHost(host => {
                ConfigureEngineViaRuntime(host.Engine, uiapp, searchPaths);
                host.Console.ScriptScope.SetVariable("__window__", gui);
            });
        }

        // The full builtins live in the loaded per-version pyRevit runtime. This Revit-agnostic
        // shell can't reference a specific runtime version at compile time, so reach
        // InteractiveEngine by reflection; the engine object is the same DLR-fork identity as the
        // loaded runtime, so the call binds cleanly.
        static void ConfigureEngineViaRuntime(ScriptEngine engine, UIApplication uiapp, IList<string> searchPaths) {
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
    /// Runs queued REPL statements inside Revit's API context for the modeless shell.
    /// </summary>
    public class ShellExternalEventDispatcher : IExternalEventHandler {
        readonly InteractiveShellWindow _gui;
        readonly Queue<Action> _commands = new Queue<Action>();
        readonly AutoResetEvent _commandCompleted;

        public ShellExternalEventDispatcher(InteractiveShellWindow gui, AutoResetEvent commandCompleted) {
            _gui = gui;
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
                    _gui.ConsoleControl.WithConsoleHost(host => {
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
