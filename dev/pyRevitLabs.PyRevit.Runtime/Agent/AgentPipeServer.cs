using System;
using System.IO;
using System.IO.Pipes;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

using pyRevitLabs.NLog;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Newline-delimited JSON server on a named pipe that only the current Windows user can
    /// open. Serves one client at a time; each request line gets exactly one response line.
    /// </summary>
    /// <remarks>
    /// Invariant: the pipe DACL allows the current user and denies network logons. Since
    /// agent requests execute arbitrary code in Revit, this ACL is the access control.
    /// Denying network logons deliberately refuses SSH sessions too, whose tokens carry the
    /// Network SID; Remote Desktop sessions are interactive logons and are allowed.
    /// Invariant: a connection that sends no line for <see cref="IdleTimeout"/> is closed, so a
    /// stalled client can't hold the only server instance and lock every other client out.
    /// The timeout covers waiting for a request only, never the time a request takes to run.
    /// After <see cref="MaxCreateFailures"/> failed attempts in a row to create the pipe, the
    /// server stops and <see cref="IsListening"/> turns false, instead of retrying forever.
    /// The wait between attempts doubles from half a second up to
    /// <see cref="MaxCreateRetryDelay"/>, so a fault has to last about two minutes to stop it.
    /// Stopping then calls the <c>stoppedListening</c> callback, so the host can stop advertising the pipe.
    /// </remarks>
    internal sealed class AgentPipeServer : IDisposable {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();
        private static readonly Encoding Utf8 = new UTF8Encoding(false);
        private static readonly TimeSpan IdleTimeout = TimeSpan.FromSeconds(30);
        private const int MaxCreateFailures = 10;
        private static readonly TimeSpan FirstCreateRetryDelay = TimeSpan.FromMilliseconds(500);
        private static readonly TimeSpan MaxCreateRetryDelay = TimeSpan.FromSeconds(30);

        private readonly string pipeName;
        private readonly Func<string, string> handleLine;
        private readonly Action<AgentPipeServer> stoppedListening;
        private readonly TimeSpan firstCreateRetryDelay;
        private readonly CancellationTokenSource stopping = new CancellationTokenSource();
        private readonly object pipeLock = new object();
        private NamedPipeServerStream currentPipe;
        private Thread thread;
        private volatile bool listening = true;

        public AgentPipeServer(string pipeName, Func<string, string> handleLine, Action<AgentPipeServer> stoppedListening)
            : this(pipeName, handleLine, stoppedListening, FirstCreateRetryDelay) {
        }

        internal AgentPipeServer(
            string pipeName, Func<string, string> handleLine, Action<AgentPipeServer> stoppedListening, TimeSpan firstCreateRetryDelay) {
            this.pipeName = pipeName;
            this.handleLine = handleLine;
            this.stoppedListening = stoppedListening;
            this.firstCreateRetryDelay = firstCreateRetryDelay;
        }

        public bool IsListening => listening;

        public void Start() {
            thread = new Thread(Listen) {
                IsBackground = true,
                Name = "pyRevit Agent Pipe",
            };
            thread.Start();
        }

        public void Dispose() {
            stopping.Cancel();
            lock (pipeLock) {
                currentPipe?.Dispose();
                currentPipe = null;
            }
        }

        private void Listen() {
            var createFailures = 0;
            while (!stopping.IsCancellationRequested) {
                NamedPipeServerStream created;
                try {
                    created = CreatePipe();
                    createFailures = 0;
                }
                catch (Exception ex) {
                    if (stopping.IsCancellationRequested)
                        return;
                    if (++createFailures >= MaxCreateFailures) {
                        logger.Error("Agent pipe server stopped: could not create pipe '{0}': {1}", pipeName, ex.Message);
                        listening = false;
                        ReportStopped();
                        return;
                    }
                    logger.Warn("Could not create agent pipe: {0}", ex.Message);
                    if (stopping.Token.WaitHandle.WaitOne(CreateRetryDelay(createFailures, firstCreateRetryDelay)))
                        return;
                    continue;
                }
                try {
                    using (var pipe = created) {
                        lock (pipeLock)
                            currentPipe = pipe;
                        pipe.WaitForConnectionAsync(stopping.Token).GetAwaiter().GetResult();
                        Serve(pipe);
                    }
                }
                catch (OperationCanceledException) {
                    return;
                }
                catch (ObjectDisposedException) when (stopping.IsCancellationRequested) {
                    return;
                }
                catch (Exception ex) {
                    if (stopping.IsCancellationRequested)
                        return;
                    logger.Warn("Agent pipe error: {0}", ex.Message);
                    Thread.Sleep(500);
                }
                finally {
                    lock (pipeLock)
                        currentPipe = null;
                }
            }
        }

        private void ReportStopped() {
            try {
                stoppedListening?.Invoke(this);
            }
            catch (Exception ex) {
                logger.Error("Agent pipe server could not report that it stopped: {0}", ex.Message);
            }
        }

        internal static TimeSpan CreateRetryDelay(int failures, TimeSpan firstDelay) {
            var doubled = firstDelay.TotalMilliseconds * Math.Pow(2, failures - 1);
            return TimeSpan.FromMilliseconds(Math.Min(doubled, MaxCreateRetryDelay.TotalMilliseconds));
        }

        private void Serve(NamedPipeServerStream pipe) {
            var reader = new StreamReader(pipe, Utf8);
            var writer = new StreamWriter(pipe, Utf8) { AutoFlush = true, NewLine = "\n" };
            string line;
            while (!stopping.IsCancellationRequested && (line = ReadLineUnlessIdle(reader)) != null) {
                if (string.IsNullOrWhiteSpace(line))
                    continue;
                writer.WriteLine(handleLine(line));
            }
        }

        private string ReadLineUnlessIdle(StreamReader reader) {
            var read = reader.ReadLineAsync();
            var finished = Task.WhenAny(read, Task.Delay(IdleTimeout, stopping.Token)).GetAwaiter().GetResult();
            if (finished == read)
                return read.GetAwaiter().GetResult();

            read.ContinueWith(abandoned => abandoned.Exception, TaskContinuationOptions.OnlyOnFaulted);
            if (!stopping.IsCancellationRequested)
                logger.Debug("Closing an agent pipe connection idle for {0} seconds", IdleTimeout.TotalSeconds);
            return null;
        }

        private NamedPipeServerStream CreatePipe() {
            var security = BuildPipeSecurity();
#if NETFRAMEWORK
            return new NamedPipeServerStream(
                pipeName, PipeDirection.InOut, 1, PipeTransmissionMode.Byte,
                PipeOptions.Asynchronous, 0, 0, security);
#else
            return NamedPipeServerStreamAcl.Create(
                pipeName, PipeDirection.InOut, 1, PipeTransmissionMode.Byte,
                PipeOptions.Asynchronous, 0, 0, security);
#endif
        }

        private static PipeSecurity BuildPipeSecurity() {
            var security = new PipeSecurity();
            var currentUser = WindowsIdentity.GetCurrent().User;
            security.AddAccessRule(
                new PipeAccessRule(currentUser, PipeAccessRights.FullControl, AccessControlType.Allow));
            security.AddAccessRule(
                new PipeAccessRule(
                    new SecurityIdentifier(WellKnownSidType.NetworkSid, null),
                    PipeAccessRights.FullControl,
                    AccessControlType.Deny));
            return security;
        }
    }
}
