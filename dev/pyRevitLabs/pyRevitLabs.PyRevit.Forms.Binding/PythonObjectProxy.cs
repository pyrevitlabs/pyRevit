using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.Threading;
using System.Windows.Threading;
using Python.Runtime;
using Dispatcher = System.Windows.Threading.Dispatcher;

namespace PyRevitLabs.PyRevit.Forms.Binding {
    /// <summary>
    /// Presents a plain Python object to WPF as a property bag whose properties read and write
    /// the Python attributes live.
    /// </summary>
    /// <remarks>
    /// <para>
    /// Properties are a dict's string keys, or otherwise namedtuple fields, instance attributes and class
    /// <c>property</c>s; any other attribute, including ones served by <c>__getattr__</c>, is
    /// found when a binding path names it. Values are converted by type, so triggers, sorting
    /// and converters see CLR <see cref="bool"/>, <see cref="int"/>, <see cref="double"/> and
    /// <see cref="string"/> values. A binding's first read may reuse the value read to type its
    /// descriptor in the same dispatcher operation (see <see cref="GetProperties()"/>); later
    /// reads call the Python getter.
    /// </para>
    /// <para>
    /// Invariant: there is at most one live proxy per Python object. Proxies of hashable objects
    /// compare with Python <c>==</c> and hash with Python <c>hash()</c>, as pythonnet's own
    /// <c>PyObject</c> does, so equal values find each other in .NET collections. Proxies of
    /// unhashable objects compare and hash by identity, so they still work as WPF items.
    /// </para>
    /// </remarks>
    public sealed class PythonObjectProxy : ICustomTypeDescriptor, INotifyPropertyChanged, IPythonValue {
        private static readonly Dictionary<IntPtr, WeakReference<PythonObjectProxy>> Live =
            new Dictionary<IntPtr, WeakReference<PythonObjectProxy>>();
        private static int pruneAt = 256;

        private readonly PyObject source;
        private readonly IntPtr handle;
        private readonly bool isDict;
        private bool? hashable;

        private PythonObjectProxy(PyObject source) {
            this.source = source;
            handle = source.Handle;
            isDict = PyDict.IsDictType(source);
        }

        PyObject IPythonValue.Source => source;

        /// <summary>Raised after a binding writes an attribute through this proxy.</summary>
        /// <remarks>
        /// Implementing this interface makes WPF listen through <c>PropertyChangedEventManager</c>,
        /// which holds the proxy weakly, instead of <c>PropertyDescriptor.AddValueChanged</c>.
        /// Changes made from Python are not observed.
        /// </remarks>
        public event PropertyChangedEventHandler PropertyChanged;

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
            return TryGetAttribute(name, out var value) ? value : null;
        }

        /// <summary>
        /// Reads an attribute, false only when it is missing; a getter that raises anything else
        /// counts as present with a null value, so its binding is kept and can read it later.
        /// </summary>
        internal bool TryGetAttribute(string name, out object value) {
            using (Py.GIL()) {
                PyObject python;
                try {
                    python = isDict ? source.GetItem(name) : source.GetAttr(name);
                }
                catch (PythonException ex) {
                    value = null;
                    if (IsMissingAttribute(ex))
                        return false;
                    Trace.TraceWarning("Python binding read of '{0}' failed: {1}", name, ex.Message);
                    return true;
                }
                value = PythonBinding.ToClr(python);
                return true;
            }
        }

        private static bool IsMissingAttribute(PythonException error) {
            var type = error.Type?.Name;
            return type == "AttributeError" || type == "KeyError";
        }

        internal void SetAttribute(string name, object value) {
            using (Py.GIL()) {
                var python = PythonBinding.ToPython(value);
                try {
                    if (isDict)
                        source.SetItem(name, python);
                    else
                        source.SetAttr(name, python);
                }
                finally {
                    PythonBinding.Release(value, python);
                }
            }
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
        }

        /// <summary>Returns the Python <c>str()</c> of the object, which WPF shows by default.</summary>
        public override string ToString() {
            using (Py.GIL())
                return source.ToString();
        }

        /// <summary>
        /// True when <paramref name="obj"/> proxies the same Python object, or an equal one when
        /// both are hashable.
        /// </summary>
        public override bool Equals(object obj) {
            if (!(obj is PythonObjectProxy other))
                return false;
            if (other.handle == handle)
                return true;
            using (Py.GIL())
                return Matches(other.source);
        }

        /// <summary>True when this object and <paramref name="other"/> are both hashable and Python-equal.</summary>
        /// <remarks>Requires the GIL.</remarks>
        internal bool Matches(PyObject other) {
            if (!IsHashable() || !IsHashable(other))
                return false;
            try {
                return source.Equals(other);
            }
            catch (PythonException ex) {
                Trace.TraceWarning("Python equality failed: {0}", ex.Message);
                return false;
            }
        }

        /// <inheritdoc/>
        public override int GetHashCode() {
            using (Py.GIL()) {
                if (IsHashable()) {
                    try {
                        using (var hash = source.InvokeMethod("__hash__"))
                            return hash.As<long>().GetHashCode();
                    }
                    catch (PythonException ex) {
                        Trace.TraceWarning("Python hash failed: {0}", ex.Message);
                    }
                }
                return handle.GetHashCode();
            }
        }

        private bool IsHashable() {
            if (!hashable.HasValue)
                hashable = IsHashable(source);
            return hashable.Value;
        }

        private static bool IsHashable(PyObject value) {
            using (var hash = value.GetAttr("__hash__"))
                return !hash.IsNone();
        }

        /// <summary>
        /// Returns a descriptor per known attribute, typed by the runtime type of its current
        /// value as IronPython types them, so WPF converts an <see cref="int"/> for a
        /// <see cref="double"/> target.
        /// </summary>
        /// <remarks>
        /// Invariant: a binding runs the attribute's getter once. A descriptor types itself from its
        /// first read, whether its type or its value is asked first. A read made for the type is
        /// handed to the descriptor's next <see cref="PropertyDescriptor.GetValue"/> on this proxy
        /// only within the same dispatcher operation, so one-shot values such as generators bind
        /// whole and later reads are live; off a dispatcher thread nothing is held.
        /// </remarks>
        public PropertyDescriptorCollection GetProperties() {
            List<string> names;
            using (Py.GIL())
                names = PythonBinding.NamesOf(source);
            var known = new PropertyDescriptor[names.Count];
            for (var index = 0; index < names.Count; index++)
                known[index] = new PythonPropertyDescriptor(this, names[index]);
            return new PythonPropertyCollection(this, known);
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
            if (found != null || string.IsNullOrEmpty(name) || !owner.TryGetAttribute(name, out var value))
                return found;
            found = new PythonPropertyDescriptor(owner, name, value);
            Add(found);
            return found;
        }
    }

    internal sealed class PythonPropertyDescriptor : PropertyDescriptor {
        private readonly PythonObjectProxy owner;
        private Type propertyType;
        private object pending;
        private bool hasPending;

        internal PythonPropertyDescriptor(PythonObjectProxy owner, string name) : base(name, null) {
            this.owner = owner;
        }

        internal PythonPropertyDescriptor(PythonObjectProxy owner, string name, object value) : this(owner, name) {
            Hold(value);
        }

        public override Type ComponentType => typeof(PythonObjectProxy);

        public override bool IsReadOnly => false;

        public override Type PropertyType {
            get {
                if (propertyType == null)
                    Hold(owner.GetAttribute(Name));
                return propertyType;
            }
        }

        private void Hold(object value) {
            propertyType = TypeOf(value);
            var dispatcher = Dispatcher.FromThread(Thread.CurrentThread);
            if (dispatcher == null)
                return;
            pending = value;
            hasPending = true;
            dispatcher.BeginInvoke(DispatcherPriority.Send, new Action(Release));
        }

        private static Type TypeOf(object value) {
            return value?.GetType() ?? typeof(object);
        }

        public override bool CanResetValue(object component) {
            return false;
        }

        public override object GetValue(object component) {
            if (hasPending && ReferenceEquals(component, owner)) {
                var held = pending;
                Release();
                return held;
            }
            var value = (component as PythonObjectProxy)?.GetAttribute(Name);
            if (propertyType == null && ReferenceEquals(component, owner))
                propertyType = TypeOf(value);
            return value;
        }

        private void Release() {
            pending = null;
            hasPending = false;
        }

        public override void ResetValue(object component) {
        }

        public override void SetValue(object component, object value) {
            if (!(component is PythonObjectProxy proxy))
                return;
            if (ReferenceEquals(proxy, owner))
                Release();
            proxy.SetAttribute(Name, value);
            OnValueChanged(component, EventArgs.Empty);
        }

        public override bool ShouldSerializeValue(object component) {
            return false;
        }
    }
}
