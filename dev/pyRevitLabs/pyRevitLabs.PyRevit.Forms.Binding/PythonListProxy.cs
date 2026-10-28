using System;
using System.Collections;
using Python.Runtime;

namespace PyRevitLabs.PyRevit.Forms.Binding {
    /// <summary>
    /// Presents a Python iterable to WPF as an <see cref="IList"/> that reads the Python
    /// sequence on every access, as IronPython's own lists do.
    /// </summary>
    /// <remarks>
    /// <para>
    /// Lists, tuples and other sized sequences are live: after the Python list changes,
    /// <c>Items.Refresh()</c> shows the change. Other iterables, such as sets, dicts and
    /// generators, are copied once when converted. Only a Python <c>list</c> is writable.
    /// Items are converted like <see cref="PythonObjectProxy"/> property values, and the
    /// proxy goes back to Python as the original object.
    /// </para>
    /// <para>
    /// Proxies compare and hash by the identity of the original Python object.
    /// </para>
    /// </remarks>
    public sealed class PythonListProxy : IList, IPythonValue {
        private readonly PyObject original;
        private readonly PyObject items;
        private readonly IntPtr handle;
        private readonly bool writable;

        private PythonListProxy(PyObject original, PyObject items) {
            this.original = original;
            this.items = items;
            handle = original.Handle;
            writable = ReferenceEquals(original, items) && PyList.IsListType(items);
        }

        PyObject IPythonValue.Source => original;

        /// <remarks>Requires the GIL. Takes ownership of <paramref name="source"/>.</remarks>
        internal static PythonListProxy For(PyObject source) {
            if (PythonBinding.IsLiveSequence(source))
                return new PythonListProxy(source, source);
            return new PythonListProxy(source, PythonBinding.Snapshot(source));
        }

        /// <inheritdoc/>
        public int Count {
            get {
                using (Py.GIL())
                    return (int)items.Length();
            }
        }

        /// <inheritdoc/>
        public bool IsReadOnly => !writable;

        /// <inheritdoc/>
        public bool IsFixedSize => !writable;

        /// <inheritdoc/>
        public bool IsSynchronized => false;

        /// <inheritdoc/>
        public object SyncRoot => this;

        /// <inheritdoc/>
        public object this[int index] {
            get {
                using (Py.GIL()) {
                    CheckIndex(index, Length());
                    return PythonBinding.ToClr(items.GetItem(index));
                }
            }
            set {
                RequireWritable();
                using (Py.GIL()) {
                    CheckIndex(index, Length());
                    items.SetItem(index, PythonBinding.ToPython(value));
                }
            }
        }

        /// <inheritdoc/>
        public int Add(object value) {
            RequireWritable();
            using (Py.GIL()) {
                items.InvokeMethod("append", PythonBinding.ToPython(value)).Dispose();
                return Length() - 1;
            }
        }

        /// <inheritdoc/>
        public void Insert(int index, object value) {
            RequireWritable();
            using (Py.GIL()) {
                using (var position = new PyInt(index))
                    items.InvokeMethod("insert", position, PythonBinding.ToPython(value)).Dispose();
            }
        }

        /// <inheritdoc/>
        public void RemoveAt(int index) {
            RequireWritable();
            using (Py.GIL()) {
                CheckIndex(index, Length());
                items.DelItem(index);
            }
        }

        /// <inheritdoc/>
        public void Remove(object value) {
            RequireWritable();
            using (Py.GIL()) {
                var index = IndexOfLocked(value);
                if (index >= 0)
                    items.DelItem(index);
            }
        }

        /// <inheritdoc/>
        public void Clear() {
            RequireWritable();
            using (Py.GIL())
                items.InvokeMethod("clear").Dispose();
        }

        /// <inheritdoc/>
        public bool Contains(object value) {
            return IndexOf(value) >= 0;
        }

        /// <summary>
        /// Returns the position of <paramref name="value"/>, matching proxied Python objects by
        /// identity and other values with <see cref="object.Equals(object, object)"/>.
        /// </summary>
        public int IndexOf(object value) {
            using (Py.GIL())
                return IndexOfLocked(value);
        }

        /// <inheritdoc/>
        public void CopyTo(Array array, int index) {
            Snapshot().CopyTo(array, index);
        }

        /// <summary>Enumerates the items the Python sequence holds when enumeration starts.</summary>
        public IEnumerator GetEnumerator() {
            return Snapshot().GetEnumerator();
        }

        /// <summary>True when <paramref name="obj"/> proxies the same Python object.</summary>
        public override bool Equals(object obj) {
            return obj is PythonListProxy other && other.handle == handle;
        }

        /// <inheritdoc/>
        public override int GetHashCode() {
            return handle.GetHashCode();
        }

        private object[] Snapshot() {
            using (Py.GIL()) {
                var count = Length();
                var result = new object[count];
                for (var index = 0; index < count; index++)
                    result[index] = PythonBinding.ToClr(items.GetItem(index));
                return result;
            }
        }

        private int IndexOfLocked(object value) {
            var count = Length();
            var python = value as IPythonValue;
            for (var index = 0; index < count; index++) {
                var item = items.GetItem(index);
                if (python != null) {
                    var same = item.Handle == python.Source.Handle;
                    item.Dispose();
                    if (same)
                        return index;
                }
                else if (Equals(PythonBinding.ToClr(item), value)) {
                    return index;
                }
            }
            return -1;
        }

        private int Length() {
            return (int)items.Length();
        }

        private static void CheckIndex(int index, int count) {
            if (index < 0 || index >= count)
                throw new ArgumentOutOfRangeException(nameof(index));
        }

        private void RequireWritable() {
            if (!writable)
                throw new NotSupportedException("Only a Python list can be changed through WPF.");
        }
    }
}
