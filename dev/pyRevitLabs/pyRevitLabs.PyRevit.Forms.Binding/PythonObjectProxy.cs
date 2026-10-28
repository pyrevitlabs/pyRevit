using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.ComponentModel;
using Python.Runtime;

namespace PyRevitLabs.PyRevit.Forms.Binding {
    /// <summary>
    /// Presents a plain Python object to WPF as a property bag whose properties read and write
    /// the Python attributes live.
    /// </summary>
    /// <remarks>
    /// <para>
    /// Properties are a dict's string keys, or otherwise namedtuple fields, instance attributes and class
    /// <c>property</c>s; any other attribute, including ones served by <c>__getattr__</c>, is
    /// found when a binding path names it. Values are converted by type on every read, so
    /// triggers, sorting and converters see CLR <see cref="bool"/>, <see cref="int"/>,
    /// <see cref="double"/> and <see cref="string"/> values.
    /// </para>
    /// <para>
    /// Invariant: there is at most one live proxy per Python object, and proxies compare and
    /// hash by the identity of that object, so unhashable Python objects work as WPF items.
    /// </para>
    /// </remarks>
    public sealed class PythonObjectProxy : ICustomTypeDescriptor, IPythonValue {
        private static readonly Dictionary<IntPtr, WeakReference<PythonObjectProxy>> Live =
            new Dictionary<IntPtr, WeakReference<PythonObjectProxy>>();
        private static int pruneAt = 256;

        private readonly PyObject source;
        private readonly IntPtr handle;
        private readonly bool isDict;
        private PythonPropertyCollection properties;

        private PythonObjectProxy(PyObject source) {
            this.source = source;
            handle = source.Handle;
            isDict = PyDict.IsDictType(source);
        }

        PyObject IPythonValue.Source => source;

        /// <summary>Returns the live proxy for <paramref name="source"/>, creating it if needed.</summary>
        /// <remarks>Requires the GIL. Takes ownership of <paramref name="source"/>.</remarks>
        internal static PythonObjectProxy For(PyObject source) {
            lock (Live) {
                var key = source.Handle;
                if (Live.TryGetValue(key, out var weak) && weak.TryGetTarget(out var existing)) {
                    source.Dispose();
                    return existing;
                }
                var proxy = new PythonObjectProxy(source);
                Live[key] = new WeakReference<PythonObjectProxy>(proxy);
                if (Live.Count >= pruneAt)
                    Prune();
                return proxy;
            }
        }

        private static void Prune() {
            var dead = new List<IntPtr>();
            foreach (var entry in Live) {
                if (!entry.Value.TryGetTarget(out _))
                    dead.Add(entry.Key);
            }
            foreach (var key in dead)
                Live.Remove(key);
            pruneAt = Math.Max(256, Live.Count * 2);
        }

        internal object GetAttribute(string name) {
            using (Py.GIL()) {
                PyObject value;
                try {
                    value = isDict ? source.GetItem(name) : source.GetAttr(name);
                }
                catch (PythonException) {
                    return null;
                }
                return PythonBinding.ToClr(value);
            }
        }

        internal void SetAttribute(string name, object value) {
            using (Py.GIL()) {
                if (isDict)
                    source.SetItem(name, PythonBinding.ToPython(value));
                else
                    source.SetAttr(name, PythonBinding.ToPython(value));
            }
        }

        internal bool HasAttribute(string name) {
            using (Py.GIL()) {
                if (!isDict)
                    return source.HasAttr(name);
                using (var key = new PyString(name))
                using (var found = source.InvokeMethod("__contains__", key))
                    return found.IsTrue();
            }
        }

        /// <summary>Returns the Python <c>str()</c> of the object, which WPF shows by default.</summary>
        public override string ToString() {
            using (Py.GIL())
                return source.ToString();
        }

        /// <summary>True when <paramref name="obj"/> proxies the same Python object.</summary>
        public override bool Equals(object obj) {
            return obj is PythonObjectProxy other && other.handle == handle;
        }

        /// <inheritdoc/>
        public override int GetHashCode() {
            return handle.GetHashCode();
        }

        /// <inheritdoc/>
        public PropertyDescriptorCollection GetProperties() {
            if (properties == null) {
                List<string> names;
                using (Py.GIL())
                    names = PythonBinding.NamesOf(source);
                var known = new PropertyDescriptor[names.Count];
                for (var index = 0; index < names.Count; index++)
                    known[index] = PythonPropertyDescriptor.Named(names[index]);
                properties = new PythonPropertyCollection(this, known);
            }
            return properties;
        }

        /// <inheritdoc/>
        public PropertyDescriptorCollection GetProperties(Attribute[] attributes) {
            return GetProperties();
        }

        /// <inheritdoc/>
        public AttributeCollection GetAttributes() {
            return AttributeCollection.Empty;
        }

        /// <inheritdoc/>
        public string GetClassName() {
            using (Py.GIL()) {
                using (var type = source.GetPythonType())
                    return type.Name;
            }
        }

        /// <inheritdoc/>
        public string GetComponentName() {
            return null;
        }

        /// <inheritdoc/>
        public TypeConverter GetConverter() {
            return null;
        }

        /// <inheritdoc/>
        public EventDescriptor GetDefaultEvent() {
            return null;
        }

        /// <inheritdoc/>
        public PropertyDescriptor GetDefaultProperty() {
            return null;
        }

        /// <inheritdoc/>
        public object GetEditor(Type editorBaseType) {
            return null;
        }

        /// <inheritdoc/>
        public EventDescriptorCollection GetEvents() {
            return EventDescriptorCollection.Empty;
        }

        /// <inheritdoc/>
        public EventDescriptorCollection GetEvents(Attribute[] attributes) {
            return EventDescriptorCollection.Empty;
        }

        /// <inheritdoc/>
        public object GetPropertyOwner(PropertyDescriptor pd) {
            return this;
        }
    }

    internal sealed class PythonPropertyCollection : PropertyDescriptorCollection {
        private readonly PythonObjectProxy owner;

        internal PythonPropertyCollection(PythonObjectProxy owner, PropertyDescriptor[] known)
            : base(known, false) {
            this.owner = owner;
        }

        public override PropertyDescriptor this[string name] => Find(name, false);

        public override PropertyDescriptor Find(string name, bool ignoreCase) {
            var found = base.Find(name, ignoreCase);
            if (found != null || string.IsNullOrEmpty(name) || !owner.HasAttribute(name))
                return found;
            found = PythonPropertyDescriptor.Named(name);
            Add(found);
            return found;
        }
    }

    internal sealed class PythonPropertyDescriptor : PropertyDescriptor {
        private static readonly ConcurrentDictionary<string, PythonPropertyDescriptor> Shared =
            new ConcurrentDictionary<string, PythonPropertyDescriptor>();

        private PythonPropertyDescriptor(string name) : base(name, null) {
        }

        internal static PythonPropertyDescriptor Named(string name) {
            return Shared.GetOrAdd(name, key => new PythonPropertyDescriptor(key));
        }

        public override Type ComponentType => typeof(PythonObjectProxy);

        public override bool IsReadOnly => false;

        public override Type PropertyType => typeof(object);

        public override bool CanResetValue(object component) {
            return false;
        }

        public override object GetValue(object component) {
            return (component as PythonObjectProxy)?.GetAttribute(Name);
        }

        public override void ResetValue(object component) {
        }

        public override void SetValue(object component, object value) {
            if (!(component is PythonObjectProxy proxy))
                return;
            proxy.SetAttribute(Name, value);
            OnValueChanged(component, EventArgs.Empty);
        }

        public override bool ShouldSerializeValue(object component) {
            return false;
        }
    }
}
