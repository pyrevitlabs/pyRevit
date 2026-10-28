using System;
using System.Collections.Generic;
using System.ComponentModel;

namespace PyRevitLabs.PyRevit.Forms.Binding {
    /// <summary>
    /// Managed copy of a Python Reactive model's bindable values, with change notification.
    /// </summary>
    /// <remarks>
    /// <para>
    /// WPF sees each stored name as a property whose type is the runtime type of its current
    /// value, as IronPython reports Python attributes, so an <see cref="int"/> binds to a
    /// <see cref="double"/> target such as <c>ProgressBar.Maximum</c> and a two-way edit of an
    /// <see cref="int"/> property writes back an <see cref="int"/>.
    /// </para>
    /// <para>
    /// Holds no Python objects of its own and never takes the GIL. Setting a value raises
    /// <see cref="PropertyChanged"/> unless it is the same reference, as
    /// <see cref="System.Dynamic.ExpandoObject"/> does, on the calling thread.
    /// </para>
    /// </remarks>
    public sealed class BindingModel : ICustomTypeDescriptor, INotifyPropertyChanged {
        private readonly Dictionary<string, object> values = new Dictionary<string, object>();

        private BindingModel() { }

        /// <summary>Creates an empty model.</summary>
        /// <remarks>
        /// The constructor stays private: a public parameterless constructor would let WPF's
        /// collection views add new items, so a <c>DataGrid</c> listing Reactive models would show
        /// a new-row placeholder that IronPython's Python-typed items never get.
        /// </remarks>
        public static BindingModel Create() => new BindingModel();

        /// <inheritdoc/>
        public event PropertyChangedEventHandler PropertyChanged;

        /// <summary>Stored value of <paramref name="name"/>, or null when it was never set.</summary>
        public object this[string name] {
            get {
                lock (values)
                    return values.TryGetValue(name, out var value) ? value : null;
            }
            set {
                object previous;
                lock (values) {
                    values.TryGetValue(name, out previous);
                    values[name] = value;
                }
                if (!ReferenceEquals(previous, value))
                    PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
            }
        }

        /// <summary>True when <paramref name="name"/> was stored.</summary>
        public bool Contains(string name) {
            lock (values)
                return values.ContainsKey(name);
        }

        /// <inheritdoc/>
        public PropertyDescriptorCollection GetProperties() {
            List<PropertyDescriptor> found;
            lock (values) {
                found = new List<PropertyDescriptor>(values.Count);
                foreach (var entry in values)
                    found.Add(new ModelPropertyDescriptor(entry.Key, entry.Value?.GetType() ?? typeof(object)));
            }
            return new PropertyDescriptorCollection(found.ToArray(), true);
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
            return null;
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

        private sealed class ModelPropertyDescriptor : PropertyDescriptor {
            private readonly Type propertyType;

            internal ModelPropertyDescriptor(string name, Type propertyType) : base(name, null) {
                this.propertyType = propertyType;
            }

            public override Type ComponentType => typeof(BindingModel);

            public override bool IsReadOnly => false;

            public override Type PropertyType => propertyType;

            public override bool CanResetValue(object component) {
                return false;
            }

            public override object GetValue(object component) {
                return (component as BindingModel)?[Name];
            }

            public override void ResetValue(object component) {
            }

            public override void SetValue(object component, object value) {
                if (component is BindingModel model)
                    model[Name] = value;
            }

            public override bool ShouldSerializeValue(object component) {
                return false;
            }
        }
    }
}
