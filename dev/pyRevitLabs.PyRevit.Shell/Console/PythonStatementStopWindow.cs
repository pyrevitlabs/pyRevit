using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Threading;

namespace PythonConsoleControl {
    internal sealed class PythonStatementStopWindow : IDisposable {
        readonly object stateLock = new object();
        Dispatcher dispatcher;
        DispatcherTimer timer;
        readonly Thread thread;
        Window window;
        Action stop;
        CancellationToken cancellation;
        long started;
        IntPtr anchor;
        bool disposed;

        internal PythonStatementStopWindow() {
            using var ready = new ManualResetEventSlim();
            thread = new Thread(() => {
                dispatcher = Dispatcher.CurrentDispatcher;
                timer = new DispatcherTimer(TimeSpan.FromMilliseconds(50), DispatcherPriority.Normal, Tick, dispatcher);
                timer.Stop();
                ready.Set();
                try { Dispatcher.Run(); }
                catch (Exception exception) { Trace.TraceError("Python shell Stop window failed: {0}", exception); }
                finally { CloseWindow(); }
            }) { IsBackground = true, Name = "Python shell Stop window" };
            thread.SetApartmentState(ApartmentState.STA);
            thread.Start();
            ready.Wait();
        }

        internal void SetAnchor(IntPtr handle) {
            lock (stateLock) anchor = handle;
        }

        internal void Begin(CancellationToken token, Action interrupt) {
            lock (stateLock) {
                if (disposed) return;
                cancellation = token;
                stop = interrupt;
                started = Stopwatch.GetTimestamp();
                dispatcher.BeginInvoke(new Action(() => timer.Start()));
            }
        }

        internal void End() {
            lock (stateLock) {
                stop = null;
                if (!disposed) dispatcher.BeginInvoke(new Action(() => {
                    timer.Stop();
                    CloseWindow();
                }));
            }
        }

        void Tick(object sender, EventArgs args) { TickNow(); }

        void TickNow() {
            lock (stateLock) {
                if (disposed || stop == null || cancellation.IsCancellationRequested) {
                    timer.Stop();
                    CloseWindow();
                    return;
                }
                if (window != null || (Stopwatch.GetTimestamp() - started) / (double)Stopwatch.Frequency < 1) return;
                var button = new Button { Content = "Stop (Ctrl+C)", Margin = new Thickness(12), Padding = new Thickness(16, 5, 16, 5) };
                button.Click += (sender, args) => RequestStop();
                window = new Window {
                    Title = "Python shell: Running...",
                    Content = button,
                    SizeToContent = SizeToContent.WidthAndHeight,
                    ResizeMode = ResizeMode.NoResize,
                    WindowStyle = WindowStyle.ToolWindow,
                    ShowInTaskbar = false,
                    ShowActivated = false,
                    Topmost = true,
                    WindowStartupLocation = WindowStartupLocation.CenterScreen
                };
                window.PreviewKeyDown += (sender, args) => {
                    if (args.Key == Key.C && (Keyboard.Modifiers & ModifierKeys.Control) != 0) {
                        args.Handled = true;
                        RequestStop();
                    }
                };
                window.Closing += (sender, args) => {
                    lock (stateLock) {
                        if (!disposed && ReferenceEquals(window, sender) && stop != null) {
                            stop();
                            stop = null;
                        }
                    }
                };
                window.Show();
                if (anchor != IntPtr.Zero && GetWindowRect(anchor, out var bounds))
                    SetWindowPos(new WindowInteropHelper(window).Handle, IntPtr.Zero, bounds.Left + 24, bounds.Top + 48, 0, 0, 0x15);
            }
        }

        internal void RequestStop() {
            lock (stateLock) {
                if (disposed) return;
                stop?.Invoke();
                stop = null;
            }
            TickNow();
        }

        void CloseWindow() {
            var closingWindow = window;
            window = null;
            closingWindow?.Close();
        }

        public void Dispose() {
            lock (stateLock) {
                if (disposed) return;
                disposed = true;
                stop = null;
                dispatcher.BeginInvoke(new Action(() => {
                    timer.Stop();
                    CloseWindow();
                    dispatcher.InvokeShutdown();
                }));
            }
            if (Thread.CurrentThread != thread && !thread.Join(TimeSpan.FromSeconds(2)))
                Trace.TraceError("Python shell Stop window did not exit within 2 seconds.");
        }

        [DllImport("user32.dll")]
        static extern bool GetWindowRect(IntPtr handle, out WindowBounds bounds);

        [DllImport("user32.dll")]
        static extern bool SetWindowPos(IntPtr handle, IntPtr insertAfter, int left, int top, int width, int height, uint flags);

        [StructLayout(LayoutKind.Sequential)]
        struct WindowBounds {
            internal int Left;
            internal int Top;
            internal int Right;
            internal int Bottom;
        }
    }
}
