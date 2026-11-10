using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Pipes;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
#if NETFRAMEWORK
using System.ComponentModel;
using System.Runtime.InteropServices;

using Microsoft.Win32.SafeHandles;
#endif

using pyRevitLabs.NLog;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Newline-delimited JSON server on a named pipe that only the current Windows user can
    /// open. Serves up to <see cref="DefaultMaxConnections"/> clients at once, each on its own
    /// thread; each request line gets exactly one response line.
    /// </summary>
    /// <remarks>
    /// Invariant: the pipe DACL allows the current user and denies network logons. Since
    /// agent requests execute arbitrary code in Revit, this ACL is the access control.
    /// Denying network logons deliberately refuses SSH sessions too, whose tokens carry the
    /// Network SID; Remote Desktop sessions are interactive logons and are allowed.
    /// Invariant: a connection that sends no line for <see cref="IdleTimeout"/> is closed, so a
    /// stalled client can't hold a server instance and, with others, lock every other client out.
    /// The timeout covers waiting for a request only, never the time a request takes to run.
    /// After <see cref="MaxCreateFailures"/> failed attempts in a row to create the pipe, the
    /// server stops and <see cref="IsListening"/> turns false, instead of retrying forever.
    /// The wait between attempts doubles from half a second up to
    /// <see cref="MaxCreateRetryDelay"/>, so a fault has to last about two minutes to stop it.
    /// Stopping then calls the <c>stoppedListening</c> callback, so the host can stop advertising the pipe.
    /// Invariant: connections only receive and answer requests; the handler (through
    /// <see cref="AgentDispatcher"/>) is the only thing that orders work, so a connection whose
    /// request is still running, for example one its client cancelled, never keeps the next
    /// client from connecting and being answered or refused with <c>revit_busy</c>.
    /// </remarks>
    internal sealed class AgentPipeServer : IDisposable {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();
        private static readonly Encoding Utf8 = new UTF8Encoding(false);
        private static readonly TimeSpan IdleTimeout = TimeSpan.FromSeconds(30);
        private const int MaxCreateFailures = 10;
        private static readonly TimeSpan FirstCreateRetryDelay = TimeSpan.FromMilliseconds(500);
        private static readonly TimeSpan MaxCreateRetryDelay = TimeSpan.FromSeconds(30);
        private const int DefaultMaxConnections = 4;

        private readonly string pipeName;
        private readonly Func<string, string> handleLine;
        private readonly Action<AgentPipeServer> stoppedListening;
        private readonly TimeSpan firstCreateRetryDelay;
        private readonly int maxConnections;
        private readonly SemaphoreSlim connectionSlots;
        private readonly CancellationTokenSource stopping = new CancellationTokenSource();
        private readonly object pipeLock = new object();
        private readonly HashSet<NamedPipeServerStream> openPipes = new HashSet<NamedPipeServerStream>();
        private Thread thread;
        private volatile bool listening = true;

        public AgentPipeServer(string pipeName, Func<string, string> handleLine, Action<AgentPipeServer> stoppedListening)
            : this(pipeName, handleLine, stoppedListening, FirstCreateRetryDelay) {
        }

        internal AgentPipeServer(
            string pipeName, Func<string, string> handleLine, Action<AgentPipeServer> stoppedListening, TimeSpan firstCreateRetryDelay,
            int maxConnections = DefaultMaxConnections) {
            this.pipeName = pipeName;
            this.handleLine = handleLine;
            this.stoppedListening = stoppedListening;
            this.firstCreateRetryDelay = firstCreateRetryDelay;
            this.maxConnections = maxConnections;
            connectionSlots = new SemaphoreSlim(maxConnections, maxConnections);
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
                foreach (var pipe in openPipes)
                    pipe.Dispose();
                openPipes.Clear();
            }
        }

        private void Listen() {
            var createFailures = 0;
            while (!stopping.IsCancellationRequested) {
                try {
                    connectionSlots.Wait(stopping.Token);
                }
                catch (OperationCanceledException) {
                    return;
                }
                NamedPipeServerStream created;
                try {
                    created = CreateInstance();
                    createFailures = 0;
                }
                catch (Exception ex) {
                    connectionSlots.Release();
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
                if (!Track(created)) {
                    Close(created);
                    return;
                }
                try {
                    created.WaitForConnectionAsync(stopping.Token).GetAwaiter().GetResult();
                }
                catch (Exception ex) {
                    Close(created);
                    if (stopping.IsCancellationRequested)
                        return;
                    logger.Warn("Agent pipe error: {0}", ex.Message);
                    Thread.Sleep(500);
                    continue;
                }
                StartServing(created);
            }
        }

        private void StartServing(NamedPipeServerStream pipe) {
            new Thread(() => ServeAndClose(pipe)) {
                IsBackground = true,
                Name = "pyRevit Agent Pipe Connection",
            }.Start();
        }

        private void ServeAndClose(NamedPipeServerStream pipe) {
            try {
                Serve(pipe);
            }
            catch (Exception ex) {
                if (!stopping.IsCancellationRequested)
                    logger.Warn("Agent pipe error: {0}", ex.Message);
            }
            finally {
                Close(pipe);
            }
        }

        private bool Track(NamedPipeServerStream pipe) {
            lock (pipeLock) {
                if (stopping.IsCancellationRequested)
                    return false;
                openPipes.Add(pipe);
                return true;
            }
        }

        private void Close(NamedPipeServerStream pipe) {
            lock (pipeLock) {
                openPipes.Remove(pipe);
                pipe.Dispose();
            }
            connectionSlots.Release();
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

        private NamedPipeServerStream CreateInstance() {
            lock (pipeLock)
                return CreatePipe(firstInstance: openPipes.Count == 0);
        }

        /// <remarks>
        /// Important: the first instance must be created with <c>FILE_FLAG_FIRST_PIPE_INSTANCE</c>.
        /// Otherwise a pipe of the same name that another process created first would be joined,
        /// and its owner's access list, not <see cref="BuildPipeSecurity"/>, would guard the host.
        /// </remarks>
        private NamedPipeServerStream CreatePipe(bool firstInstance) {
            var security = BuildPipeSecurity();
#if NETFRAMEWORK
            return CreatePipeNative(security, firstInstance);
#else
            var options = firstInstance ? PipeOptions.Asynchronous | PipeOptions.FirstPipeInstance : PipeOptions.Asynchronous;
            return NamedPipeServerStreamAcl.Create(
                pipeName, PipeDirection.InOut, maxConnections, PipeTransmissionMode.Byte,
                options, 0, 0, security);
#endif
        }

#if NETFRAMEWORK
        private const uint PipeAccessDuplex = 0x3;
        private const uint FileFlagFirstPipeInstance = 0x80000;
        private const uint FileFlagOverlapped = 0x40000000;

        [StructLayout(LayoutKind.Sequential)]
        private struct SecurityAttributes {
            public int Length;
            public IntPtr SecurityDescriptor;
            public int InheritHandle;
        }

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern SafePipeHandle CreateNamedPipe(
            string name, uint openMode, uint pipeMode, uint maxInstances,
            uint outBufferSize, uint inBufferSize, uint defaultTimeout, ref SecurityAttributes securityAttributes);

        private NamedPipeServerStream CreatePipeNative(PipeSecurity security, bool firstInstance) {
            var descriptor = GCHandle.Alloc(security.GetSecurityDescriptorBinaryForm(), GCHandleType.Pinned);
            try {
                var attributes = new SecurityAttributes {
                    Length = Marshal.SizeOf(typeof(SecurityAttributes)),
                    SecurityDescriptor = descriptor.AddrOfPinnedObject(),
                };
                var openMode = PipeAccessDuplex | FileFlagOverlapped | (firstInstance ? FileFlagFirstPipeInstance : 0);
                var handle = CreateNamedPipe(@"\\.\pipe\" + pipeName, openMode, 0, (uint)maxConnections, 0, 0, 0, ref attributes);
                if (handle.IsInvalid)
                    throw new Win32Exception(Marshal.GetLastWin32Error());
                return new NamedPipeServerStream(PipeDirection.InOut, true, false, handle);
            }
            finally {
                descriptor.Free();
            }
        }
#endif

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
