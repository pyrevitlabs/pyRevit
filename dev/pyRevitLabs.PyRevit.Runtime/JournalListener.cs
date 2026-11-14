using System;
using System.IO;
using System.Threading;
using System.Collections.Generic;
using System.Text.RegularExpressions;

using Autodesk.Revit.UI;
using pyRevitLabs.NLog;

namespace PyRevitLabs.PyRevit.Runtime {
    public class JournalUpdateArgs : EventArgs {
        public string JournalFile;
        public string[] NewJournalLines;

        public JournalUpdateArgs(string journalFile, string[] newLines) {
            JournalFile = journalFile;
            NewJournalLines = newLines;
        }
    }

    public class CommandExecutedArgs : EventArgs {
        public string JournalFile;
        public string CommandId;

        public CommandExecutedArgs(string journalFile, string commandId) {
            JournalFile = journalFile;
            CommandId = commandId;
        }
    }

    public delegate void JournalUpdate(object source, JournalUpdateArgs e);
    public delegate void CommandExecuted(object source, CommandExecutedArgs e);

    public class JournalListener {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();
        private const int PollIntervalMilliseconds = 250;
        private const int WorkerJoinMilliseconds = 2000;
        private string JournalFile = "";
        private Thread jtail;
        private CancellationTokenSource _cancellationTokenSource;
        private readonly object lifecycleLock = new object();
        private static readonly TimeSpan FailureLogInterval = TimeSpan.FromSeconds(60);
        private string lastFailure;
        private DateTime nextFailureLog;

        private static List<Regex> JournalCommandExtractors = new List<Regex> {
                new Regex(@".*Jrn\.RibbonEvent\s""Execute external command\:(?<command_id>.+)\:(.+)"""),
                new Regex(@".*Jrn.Command "".+""\s\,\s"".*\s\,\s(?<command_id>.+)"""),
        };

        public bool JournalUpdateEvents = false;
        public event JournalUpdate OnJournalUpdate;

        public bool JournalCommandExecutedEvents = false;
        public event CommandExecuted OnJournalCommandExecuted;

        public JournalListener(UIApplication uiapp) {
            JournalFile = uiapp.Application.RecordingJournalFilename;
        }

        public void Start() {
            lock (lifecycleLock) {
                if (_cancellationTokenSource != null)
                    return;

                var previous = jtail;
                if (previous != null && previous != Thread.CurrentThread && !previous.Join(WorkerJoinMilliseconds))
                    logger.Warn("Previous journal worker is still running; starting a new one.");

                var source = new CancellationTokenSource();
                _cancellationTokenSource = source;
                var tail = new JournalTail(JournalFile);
                jtail = new Thread(() => TailJournal(tail, source)) { IsBackground = true };
                jtail.Start();
            }
        }

        public void Stop() {
            lock (lifecycleLock) {
                _cancellationTokenSource?.Cancel();
                _cancellationTokenSource = null;
            }
        }

        private void TailJournal(JournalTail tail, CancellationTokenSource source) {
            try {
                var token = source.Token;
                while (!token.WaitHandle.WaitOne(PollIntervalMilliseconds)) {
                    if (token.IsCancellationRequested)
                        break;

                    try {
                        Tail(tail);
                        lastFailure = null;
                    }
                    catch (Exception ex) {
                        LogPollFailure(ex);
                    }
                }
            }
            finally {
                source.Dispose();
            }
        }

        private void LogPollFailure(Exception ex) {
            var failure = ex.GetType().FullName + ": " + ex.Message;
            var now = DateTime.UtcNow;
            if (failure == lastFailure && now < nextFailureLog)
                return;

            lastFailure = failure;
            nextFailureLog = now + FailureLogInterval;
            logger.Error(ex, "Journal polling failed.");
        }

        private void Tail(JournalTail tail) {
            var newLines = tail.ReadNewLines();
            if (newLines.Length == 0)
                return;

            var updateHandlers = OnJournalUpdate;
            if (updateHandlers != null) {
                var args = new JournalUpdateArgs(JournalFile, newLines);
                foreach (JournalUpdate handler in updateHandlers.GetInvocationList())
                    InvokeHook(() => handler(this, args));
            }

            if (OnJournalCommandExecuted != null)
                DetectCommandExecutions(newLines);
        }

        private static void InvokeHook(Action hook) {
            try {
                hook();
            }
            catch (Exception ex) {
                logger.Error(ex, "Journal hook failed.");
            }
        }

        private void DetectCommandExecutions(string[] newLines) {
            // find the commands in new journal lines
            var commands = new List<string>();
            foreach (var line in newLines) {
                foreach (var finder in JournalCommandExtractors) {
                    var m = finder.Match(line);
                    if (m.Success) {
                        commands.Add(m.Groups["command_id"].Value);
                        break;
                    }
                }
            }
            // now call the handlers
            var executedHandlers = OnJournalCommandExecuted;
            if (executedHandlers == null)
                return;

            foreach (var commandId in commands) {
                var args = new CommandExecutedArgs(JournalFile, commandId);
                foreach (CommandExecuted handler in executedHandlers.GetInvocationList())
                    InvokeHook(() => handler(this, args));
            }
        }

    }
}

