// Copyright (c) 2010 Joe Moorhouse

using System;
using System.Diagnostics;
using System.Text;
using System.Threading;
using IronPython.Hosting;
using IronPython.Runtime;
using Microsoft.Scripting.Hosting;
using Microsoft.Scripting.Hosting.Providers;
using Microsoft.Scripting.Hosting.Shell;

namespace PythonConsoleControl
{
    public delegate void ConsoleCreatedEventHandler(object sender, EventArgs e);


    /// <summary>
    /// Hosts the python console.
    /// </summary>
    public class PythonConsoleHost : ConsoleHost, IDisposable
    {
        Thread thread;
        PythonTextEditor textEditor;
        PythonConsole pythonConsole;
        int disposed;

        public event ConsoleCreatedEventHandler ConsoleCreated;

        public PythonConsoleHost(PythonTextEditor textEditor)
        {
            this.textEditor = textEditor;
        }

        public PythonConsole Console
        {
            get { return pythonConsole; }
        }

        public PythonTextEditor Editor
        {
            get { return textEditor; }
        }

        protected override Type Provider
        {
            get { return typeof(PythonContext); }
        }

        /// <summary>
        /// Runs the console host in its own thread.
        /// </summary>
        public void Run()
        {
            thread = new Thread(RunConsole);
            thread.IsBackground = true;
            thread.Start();
        }

        public void Dispose()
        {
            if (Interlocked.Exchange(ref disposed, 1) != 0) return;
            pythonConsole?.Dispose();
            textEditor.Dispose();
            new Thread(() =>
            {
                try
                {
                    var timeout = TimeSpan.FromSeconds(10);
                    var consoleExited = thread == null || thread.Join(timeout);
                    if (!consoleExited) Trace.TraceWarning("Python shell console worker did not exit within {0}.", timeout);
                    var dispatcherExited = consoleExited && (pythonConsole == null || pythonConsole.WaitForExit(timeout));
                    if (!dispatcherExited) Trace.TraceWarning("Python shell dispatcher cleanup did not finish; console exit: {0}, join limit: {1}.", consoleExited, timeout);
                    var completionExited = textEditor.WaitForExit(timeout);
                    if (!completionExited) Trace.TraceWarning("Python shell completion worker did not exit within {0}.", timeout);
                    if (consoleExited && dispatcherExited && completionExited) Runtime?.Shutdown();
                }
                catch (Exception exception)
                {
                    Trace.TraceError("Python shell cleanup failed: {0}", exception);
                }
            }) { IsBackground = true, Name = "Python shell cleanup" }.Start();
        }


        protected override CommandLine CreateCommandLine()
        {
            return new PythonCommandLine();
        }

        protected override OptionsParser CreateOptionsParser()
        {
            return new PythonOptionsParser();
        }

        /// <remarks>
        /// Replaces standard output only after the runtime is available.
        /// </remarks>
        protected override IConsole CreateConsole(ScriptEngine engine, CommandLine commandLine, ConsoleOptions options)
        {
            SetOutput(new PythonOutputStream(textEditor));
            pythonConsole = new PythonConsole(textEditor, commandLine);
            if (Volatile.Read(ref disposed) != 0) pythonConsole.Dispose();
            if (ConsoleCreated != null) ConsoleCreated(this, EventArgs.Empty);
            return pythonConsole;
        }

        public void WhenConsoleCreated(Action<PythonConsoleHost> action)
        {
            if (Volatile.Read(ref disposed) != 0) return;
            if (pythonConsole != null)
            {
                pythonConsole.WhenConsoleInitialized(() =>
                {
                    if (Volatile.Read(ref disposed) == 0) action(this);
                });
            }
            else
            {
                ConsoleCreated += (sender, args) => WhenConsoleCreated(action);
            }
        }

        protected virtual void SetOutput(PythonOutputStream stream)
        {
            Runtime.IO.SetOutput(stream, Encoding.UTF8);
        }

        /// <summary>
        /// Runs the console.
        /// </summary>
        void RunConsole()
        {
            this.Run(new string[] { "-X:FullFrames" });
        }

        protected override ScriptRuntimeSetup CreateRuntimeSetup()
        {
            ScriptRuntimeSetup srs = ScriptRuntimeSetup.ReadConfiguration();
            foreach (var langSetup in srs.LanguageSetups)
            {
                if (langSetup.FileExtensions.Contains(".py"))
                {
                    langSetup.Options["SearchPaths"] = new string[0];
                }
            }
            return srs;
        }

        protected override void ParseHostOptions(string/*!*/[]/*!*/ args)
        {
            // Python doesn't want any of the DLR base options.
            foreach (string s in args)
            {
                Options.IgnoredArgs.Add(s);
            }
        }

        protected override void ExecuteInternal()
        {
            var pc = HostingHelpers.GetLanguageContext(Engine) as PythonContext;
            pc.SetModuleState(typeof(ScriptEngine), Engine);
            base.ExecuteInternal();
        }
    }
}
