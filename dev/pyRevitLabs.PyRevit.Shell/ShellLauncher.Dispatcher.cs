using System;
using System.Threading;
using System.Windows.Threading;
using Microsoft.Scripting;
using PythonConsoleControl;

namespace PyRevitLabs.PyRevit.Shell {
    internal static partial class ShellLauncher {
        // The modal command retains its API context until the dispatched action returns.
        internal static void RunOnDispatcher(Dispatcher dispatcher, Action command) {
            if (command == null) return;
            if (dispatcher == null) throw new ArgumentNullException(nameof(dispatcher));
            var request = new ShellExternalEventRequest(command);
            var operation = dispatcher.BeginInvoke(DispatcherPriority.Normal, new Action(request.Execute));
            var cancellationToken = PythonExecution.CurrentCancellationToken;
            while (operation.Status != DispatcherOperationStatus.Completed
                && operation.Status != DispatcherOperationStatus.Aborted) {
                if (cancellationToken.IsCancellationRequested && operation.Abort())
                    throw new KeyboardInterruptException("");
                operation.Wait(TimeSpan.FromMilliseconds(50));
            }
            if (operation.Status == DispatcherOperationStatus.Aborted)
                throw new KeyboardInterruptException("");
            request.Wait(CancellationToken.None, () => false);
        }
    }
}
