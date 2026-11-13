using System;
using System.IO;
using System.Threading;
using System.Collections.Generic;
using System.Text.RegularExpressions;

using Autodesk.Revit.UI;

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
        private const int PollIntervalMilliseconds = 250;
        private JournalTail _tail;
        private string JournalFile = "";
        private Thread jtail;
        private CancellationTokenSource _cancellationTokenSource;

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
            if (_cancellationTokenSource != null && !_cancellationTokenSource.IsCancellationRequested)
                return;

            _cancellationTokenSource = new CancellationTokenSource();
            var token = _cancellationTokenSource.Token;
            _tail = new JournalTail(JournalFile);
            jtail = new Thread(() => TailJournal(token)) { IsBackground = true };
            jtail.Start();
        }

        public void Stop() {
            _cancellationTokenSource?.Cancel();
        }

        private void TailJournal(CancellationToken token) {
            while (!token.WaitHandle.WaitOne(PollIntervalMilliseconds)) {
                Tail();
            }
        }

        private void Tail() {
            var newLines = _tail.ReadNewLines();
            if (newLines.Length == 0)
                return;

            if (OnJournalUpdate != null)
                OnJournalUpdate(this, new JournalUpdateArgs(JournalFile, newLines));

            if (OnJournalCommandExecuted != null)
                DetectCommandExecutions(newLines);
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
            foreach (var commandId in commands)
                OnJournalCommandExecuted(this, new CommandExecutedArgs(JournalFile, commandId));
        }

    }
}

