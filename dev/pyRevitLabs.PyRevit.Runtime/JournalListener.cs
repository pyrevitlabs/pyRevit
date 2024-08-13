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
        private long prevLen = -1;
        private string JournalFile = "";
        private Thread jtail;

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
            FileInfo fi = new FileInfo(JournalFile);
            prevLen = fi.Length;
            jtail = new Thread(TailJournal);
            jtail.Start();
        }

        public void Stop() {
            if (jtail != null)
                jtail.Abort();
        }

        private void TailJournal() { while (true) { Tail(); } }

        private void Tail() {
            FileInfo fi = new FileInfo(JournalFile);
            if (fi.Exists) {
                if (fi.Length != prevLen) {
                    using (var stream = new FileStream(fi.FullName, FileMode.Open, FileAccess.Read, FileShare.Delete | FileShare.ReadWrite)) {
                        stream.Seek(prevLen, SeekOrigin.Begin);

                        var newlengh = stream.Length;
                        prevLen = newlengh;

                        using (StreamReader sr = new StreamReader(stream)) {
                            string all = sr.ReadToEnd();
                            string[] newLines = all.Split(Environment.NewLine.ToCharArray());
                            if (OnJournalUpdate != null)
                                OnJournalUpdate(this, new JournalUpdateArgs(JournalFile, newLines));

                            if (OnJournalCommandExecuted != null)
                                DetectCommandExecutions(newLines);
                        }
                    }
                }
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
            foreach (var commandId in commands)
                OnJournalCommandExecuted(this, new CommandExecutedArgs(JournalFile, commandId));
        }

    }
}

