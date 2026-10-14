using System;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Scripting;

namespace PyRevitLabs.PyRevit.Shell {
    internal sealed class ShellExternalEventRequest {
        readonly TaskCompletionSource<bool> completed = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);

        public ShellExternalEventRequest(Action command) {
            Command = command ?? throw new ArgumentNullException(nameof(command));
        }

        public Action Command { get; }
        public void Complete() => completed.TrySetResult(true);
        public void Fail(Exception error) => completed.TrySetException(error);

        public void Execute() {
            try { Command(); }
            catch (Exception error) { Fail(error); }
            finally { Complete(); }
        }

        /// <summary>
        /// Waits for queued cancellation or for an executing API callback to return.
        /// </summary>
        public void Wait(CancellationToken cancellationToken, Func<bool> cancelPending) {
            try { completed.Task.Wait(cancellationToken); }
            catch (AggregateException) { }
            catch (OperationCanceledException) {
                if (cancelPending()) throw new KeyboardInterruptException("");
            }
            completed.Task.GetAwaiter().GetResult();
        }
    }
}
