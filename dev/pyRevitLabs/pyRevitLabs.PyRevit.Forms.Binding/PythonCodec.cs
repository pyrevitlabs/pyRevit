using System;
using System.Collections;
using Python.Runtime;

namespace PyRevitLabs.PyRevit.Forms.Binding {
    internal interface IPythonValue {
        PyObject Source { get; }
    }

    internal sealed class PythonCodec : IPyObjectDecoder, IPyObjectEncoder {
        public bool CanDecode(PyType objectType, Type targetType) {
            if (targetType == typeof(object))
                return (PythonBinding.Classify(objectType) & (PythonBinding.ObjectKind | PythonBinding.IntegerKind)) != 0;
            if (IsCollectionTarget(targetType))
                return (PythonBinding.Classify(objectType) & PythonBinding.ItemsKind) != 0;
            if (targetType.IsValueType)
                return false;
            var rootType = PythonBinding.RootTypeOf(objectType);
            return rootType != null && targetType.IsAssignableFrom(rootType);
        }

        public bool TryDecode<T>(PyObject pyObj, out T value) {
            if (typeof(T) != typeof(object) && !IsCollectionTarget(typeof(T))) {
                if (PythonBinding.RootOf(pyObj) is T root) {
                    pyObj.Dispose();
                    value = root;
                    return true;
                }
                value = default;
                return false;
            }
            if (typeof(T) == typeof(object) && PyInt.IsIntType(pyObj)) {
                if (!PythonBinding.TryToClrInteger(pyObj, out var number)) {
                    value = default;
                    return false;
                }
                pyObj.Dispose();
                value = (T)number;
                return true;
            }
            object result = typeof(T) == typeof(object)
                ? PythonBinding.AdaptObject(pyObj)
                : PythonListProxy.For(pyObj);
            value = (T)result;
            return true;
        }

        public bool CanEncode(Type type) {
            return type == typeof(object) || IsCollectionTarget(type);
        }

        public PyObject TryEncode(object value) {
            switch (value) {
                case IPythonValue python:
                    return python.Source;
                case BindingModel model:
                    return PythonBinding.FindModel(model);
                default:
                    return null;
            }
        }

        private static bool IsCollectionTarget(Type type) {
            return type == typeof(IEnumerable) || type == typeof(IList) || type == typeof(ICollection);
        }
    }
}
