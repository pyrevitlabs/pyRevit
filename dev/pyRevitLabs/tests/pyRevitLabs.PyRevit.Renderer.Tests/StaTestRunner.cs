using System;
using System.Runtime.ExceptionServices;
using System.Threading;

namespace PyRevitLabs.PyRevit.Renderer.Tests {
    /// <summary>
    /// Runs a test body on a single-threaded-apartment thread. WPF controls
    /// are built on STA threads, and the renderer builds one.
    /// </summary>
    internal static class StaTestRunner {
        internal static void Run(Action body) {
            Run<object>(() => {
                body();
                return null;
            });
        }

        internal static T Run<T>(Func<T> body) {
            var result = default(T);
            Exception failure = null;
            var thread = new Thread(() => {
                try {
                    result = body();
                }
                catch (Exception ex) {
                    failure = ex;
                }
            });

            thread.SetApartmentState(ApartmentState.STA);
            thread.IsBackground = true;
            thread.Start();
            thread.Join();

            if (failure != null)
                ExceptionDispatchInfo.Capture(failure).Throw();

            return result;
        }
    }
}
