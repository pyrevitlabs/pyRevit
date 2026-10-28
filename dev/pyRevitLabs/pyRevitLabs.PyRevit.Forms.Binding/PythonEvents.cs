using System.Collections.Generic;
using System.Windows;
using Python.Runtime;

namespace PyRevitLabs.PyRevit.Forms.Binding {
    /// <summary>
    /// Lets XAML hand every instance of an element to a Python callback as WPF creates it, so
    /// Python can attach event handlers directly to elements created later from templates.
    /// </summary>
    /// <remarks>
    /// <para>
    /// pyRevit's CPython forms mark template elements whose events can never reach the window,
    /// such as items of a <c>ContextMenu</c> or <c>ToolTip</c> inside a <c>DataTemplate</c>,
    /// with <c>PythonEvents.Hook="key"</c>. WPF sets the property on each instance it builds,
    /// which runs the callback registered for <c>key</c>, the way IronPython attaches template
    /// handlers to each instance.
    /// </para>
    /// <para>
    /// The callbacks live here rather than in a Python module so they survive a reload of
    /// <c>pyrevit.forms</c> while their windows stay open. Every callback takes the GIL itself
    /// and must not raise.
    /// </para>
    /// </remarks>
    public static class PythonEvents {
        private static readonly object Gate = new object();
        private static readonly Dictionary<string, PyObject> Callbacks = new Dictionary<string, PyObject>();
        private static bool shutdownRegistered;

        /// <summary>Key of the callback that receives each instance of the marked element.</summary>
        public static readonly DependencyProperty HookProperty = DependencyProperty.RegisterAttached(
            "Hook", typeof(string), typeof(PythonEvents), new PropertyMetadata(null, OnHookChanged));

        /// <summary>XAML accessor for <see cref="HookProperty"/>.</summary>
        public static string GetHook(DependencyObject element) {
            return (string)element.GetValue(HookProperty);
        }

        /// <summary>XAML accessor for <see cref="HookProperty"/>.</summary>
        public static void SetHook(DependencyObject element, string value) {
            element.SetValue(HookProperty, value);
        }

        /// <summary>Calls <paramref name="callback"/> with every element WPF marks with <paramref name="key"/>.</summary>
        /// <remarks>Replaces an earlier callback for the same key.</remarks>
        public static void Attach(string key, PyObject callback) {
            lock (Gate) {
                if (!shutdownRegistered) {
                    PythonEngine.AddShutdownHandler(Reset);
                    shutdownRegistered = true;
                }
                Callbacks[key] = callback;
            }
        }

        /// <summary>Stops delivering elements marked with <paramref name="key"/>.</summary>
        public static void Detach(string key) {
            lock (Gate) {
                Callbacks.Remove(key);
            }
        }

        private static void Reset() {
            lock (Gate) {
                Callbacks.Clear();
                shutdownRegistered = false;
            }
        }

        private static void OnHookChanged(DependencyObject element, DependencyPropertyChangedEventArgs args) {
            if (!(args.NewValue is string key))
                return;
            PyObject callback;
            lock (Gate) {
                if (!Callbacks.TryGetValue(key, out callback))
                    return;
            }
            using (Py.GIL())
            using (var target = element.ToPython())
                callback.Invoke(target).Dispose();
        }
    }
}
