using System;
using System.Collections.Generic;
using Microsoft.Scripting;

namespace PyRevitLabs.PyRevit.Shell {
    internal sealed class ShellExternalEventDispatcher : IDisposable {
        readonly object _requestsLock = new object();
        readonly List<ShellExternalEventRequest> _requests = new List<ShellExternalEventRequest>();
        bool _disposed;

        public ShellExternalEventRequest Enqueue(Action command) {
            var request = new ShellExternalEventRequest(command);
            lock (_requestsLock) {
                if (_disposed) throw new KeyboardInterruptException("");
                _requests.Add(request);
            }
            return request;
        }

        public bool Cancel(ShellExternalEventRequest request) {
            lock (_requestsLock) {
                if (!_requests.Remove(request)) return false;
                request.Fail(new KeyboardInterruptException(""));
                return true;
            }
        }

        bool TryDequeue(out ShellExternalEventRequest request) {
            lock (_requestsLock) {
                if (_requests.Count == 0) {
                    request = null;
                    return false;
                }
                request = _requests[0];
                _requests.RemoveAt(0);
                return true;
            }
        }

        internal void ExecutePendingRequests() {
            while (TryDequeue(out var request)) request.Execute();
        }

        public void Dispose() {
            lock (_requestsLock) {
                if (_disposed) return;
                _disposed = true;
                foreach (var request in _requests) request.Fail(new KeyboardInterruptException(""));
                _requests.Clear();
            }
        }
    }
}
