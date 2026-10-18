using System;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using IronPython.Hosting;
using IronPython.Runtime;
using Microsoft.Scripting.Hosting;
using Microsoft.Scripting.Hosting.Providers;
using Microsoft.Scripting.Hosting.Shell;
using PythonConsoleControl;

namespace pyRevitLabs.PyRevit.Shell.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Integration")]
    public class InteractiveCommandLineLifecycleTests {
        [Fact]
        public void ClosingInputEndsInteractiveLoopAndInvokesRuntimeShutdownHook() {
            using var execution = new PythonExecution();
            using var input = new ClosingConsole();
            using var languageShutdown = new ManualResetEventSlim();
            var host = new InteractiveHost(execution, input, languageShutdown);
            Exception error = null;
            var shutdownCompleted = false;
            var worker = new Thread(() => {
                try { host.Run(new[] { "-S", "-X:FullFrames" }); }
                catch (Exception exception) { error = exception; }
                finally {
                    host.Runtime?.Shutdown();
                    shutdownCompleted = true;
                }
            }) { IsBackground = true };
            worker.Start();
            try {
                Assert.True(input.Waiting.Wait(TimeSpan.FromSeconds(10)));
                execution.Dispose();
                input.Close();
                Assert.True(worker.Join(TimeSpan.FromSeconds(10)));
                Assert.Null(error);
                Assert.True(shutdownCompleted);
                Assert.True(languageShutdown.IsSet);
                Assert.DoesNotContain("KeyboardInterrupt", input.Transcript.ToString());
            }
            finally {
                input.Close();
                if (worker.IsAlive) host.Terminate(0);
                worker.Join(TimeSpan.FromSeconds(10));
            }
        }

        sealed class InteractiveHost : ConsoleHost {
            readonly PythonExecution execution;
            readonly ClosingConsole input;
            readonly ManualResetEventSlim languageShutdown;

            internal InteractiveHost(PythonExecution execution, ClosingConsole input, ManualResetEventSlim languageShutdown) {
                this.execution = execution;
                this.input = input;
                this.languageShutdown = languageShutdown;
            }

            protected override Type Provider => typeof(PythonContext);
            protected override ScriptRuntimeSetup CreateRuntimeSetup() => Python.CreateRuntimeSetup(new Dictionary<string, object>());
            protected override CommandLine CreateCommandLine() => new PythonCommandLine();
            protected override OptionsParser CreateOptionsParser() => new PythonOptionsParser();
            protected override void ParseHostOptions(string[] args) {
                foreach (var argument in args) Options.IgnoredArgs.Add(argument);
            }

            protected override IConsole CreateConsole(ScriptEngine engine, CommandLine commandLine, ConsoleOptions options) {
                var context = (PythonContext)HostingHelpers.GetLanguageContext(engine);
                context.GetSetCommandDispatcher(command => execution.Run(engine, command, action => action()));
                var sys = engine.GetSysModule();
                var onShutdown = new Action(languageShutdown.Set);
                sys.SetVariable("exitfunc", onShutdown);
                sys.SetVariable("_exitfunc", onShutdown);
                return input;
            }
        }

        sealed class ClosingConsole : IConsole, IDisposable {
            readonly ManualResetEventSlim closed = new ManualResetEventSlim();
            internal readonly ManualResetEventSlim Waiting = new ManualResetEventSlim();
            internal readonly StringWriter Transcript = new StringWriter();
            public TextWriter Output { get; set; } = TextWriter.Null;
            public TextWriter ErrorOutput { get; set; } = TextWriter.Null;

            public string ReadLine(int autoIndentSize) {
                Waiting.Set();
                closed.Wait();
                return null;
            }

            public void Write(string text, Style style) => Transcript.Write(text);
            public void WriteLine(string text, Style style) => Transcript.WriteLine(text);
            public void WriteLine() => Transcript.WriteLine();
            internal void Close() => closed.Set();
            public void Dispose() { closed.Dispose(); Waiting.Dispose(); Transcript.Dispose(); }
        }
    }
}
