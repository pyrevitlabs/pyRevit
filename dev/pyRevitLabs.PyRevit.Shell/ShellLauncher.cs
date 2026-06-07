using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Threading;
using System.Windows.Threading;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using IronPython.Hosting;
using Microsoft.Scripting.Hosting;
using Microsoft.Scripting.Hosting.Shell;
using PythonConsoleControl;

namespace PyRevitLabs.PyRevit.Shell {
    /// <summary>
    /// Builds and shows the interactive shell window and wires its REPL to a valid Revit API
    /// context. Reached through <see cref="Shell"/> so the assembly resolver is installed first.
    /// </summary>
    internal static class ShellLauncher {
        public static InteractiveShellWindow ShowModal(UIApplication uiapp) {
            var gui = new InteractiveShellWindow();
            AttachEnvironment(gui, uiapp);

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

        public static InteractiveShellWindow ShowModeless(UIApplication uiapp) {
            var gui = new InteractiveShellWindow();
            AttachEnvironment(gui, uiapp);

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

        // Configure the REPL engine to behave like a pyRevit script: pyRevit's IPY342 stdlib,
        // RevitAPI loaded, and __revit__ bound to the running UIApplication.
        static void AttachEnvironment(InteractiveShellWindow gui, UIApplication uiapp) {
            gui.ConsoleControl.WithConsoleHost(host => {
                var engine = host.Engine;
                AddPyRevitStdLib(engine);
                engine.Runtime.LoadAssembly(typeof(Autodesk.Revit.DB.Document).Assembly);
                engine.Runtime.LoadAssembly(typeof(Autodesk.Revit.UI.UIApplication).Assembly);
                Python.GetBuiltinModule(engine).SetVariable("__revit__", uiapp);
                host.Console.ScriptScope.SetVariable("__window__", gui);
            });
        }

        // Reuse pyRevit's bundled IPY342 standard library without depending on the active engine:
        // the matching python_342_lib.zip is embedded in the sibling pyRevitLoader.dll that ships
        // next to this assembly in engines/IPY342. Optional - the shell still works without it.
        static void AddPyRevitStdLib(ScriptEngine engine) {
            try {
                var shellDir = Path.GetDirectoryName(typeof(ShellLauncher).Assembly.Location);
                if (string.IsNullOrEmpty(shellDir))
                    return;
                var loaderPath = Path.Combine(shellDir, "pyRevitLoader.dll");
                if (!File.Exists(loaderPath))
                    return;

                var loaderAsm = Assembly.LoadFrom(loaderPath);
                var resName = loaderAsm.GetManifestResourceNames()
                    .FirstOrDefault(n => n.EndsWith("python_342_lib.zip", StringComparison.OrdinalIgnoreCase));
                if (resName == null)
                    return;

                var importer = new IronPython.Modules.ResourceMetaPathImporter(loaderAsm, resName);
                dynamic sys = Python.GetSysModule(engine);
                sys.meta_path.append(importer);
            }
            catch {
                // stdlib import support is best-effort; Revit API exploration works without it
            }
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
