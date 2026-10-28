using System;
using System.Collections.Generic;
using System.Dynamic;
using Python.Runtime;

namespace PyRevitLabs.PyRevit.Forms.Binding {
    /// <summary>
    /// Shows plain Python data to WPF under pythonnet the way IronPython does: Python sequences
    /// become live <see cref="PythonListProxy"/> collections and plain Python objects become
    /// <see cref="PythonObjectProxy"/> property bags, while every value WPF hands back to Python
    /// is the original Python object.
    /// </summary>
    /// <remarks>
    /// <para>
    /// The conversions are pythonnet codecs, so once registered they apply to every CPython
    /// script in the process, not only to forms. They claim only the CLR targets
    /// <see cref="object"/> (plain class instances, namedtuples, and exact <c>int</c>s, which
    /// become <see cref="int"/> or <see cref="long"/> as under IronPython) and the non-generic
    /// <c>IEnumerable</c>, <c>IList</c> and <c>ICollection</c> (iterables other than strings),
    /// plus, once <see cref="RegisterRoots"/> is called, reference types that a Python form's
    /// native root satisfies. Python lists passed as <see cref="object"/> stay pythonnet
    /// <see cref="PyObject"/>s.
    /// </para>
    /// <para>
    /// Important: every proxy member takes the GIL itself, because WPF reaches them on the UI
    /// thread while pythonnet has released the GIL around the CLR call that triggered WPF.
    /// A thread that holds the GIL while blocking on the UI thread deadlocks against them.
    /// </para>
    /// </remarks>
    public static class PythonBinding {
        internal const int ItemsKind = 1;
        internal const int ObjectKind = 2;
        internal const int IntegerKind = 4;

        private const string HelperSource = @"
_HEAPTYPE = 1 << 9
_OPAQUE = (str, bytes, bytearray, int, float, complex, list, dict, set, frozenset, type, BaseException)


def _declares(cls, name):
    return any(name in vars(klass) for klass in cls.__mro__[:-1])


def classify(cls):
    if cls is int:
        return 4
    if issubclass(cls, (str, bytes, bytearray)):
        return 0
    kinds = 0
    if _declares(cls, '__iter__') or _declares(cls, '__getitem__'):
        kinds |= 1
    if cls.__flags__ & _HEAPTYPE and not _declares(cls, '__call__'):
        if issubclass(cls, tuple):
            if hasattr(cls, '_fields'):
                kinds |= 2
        elif not kinds & 1 and not issubclass(cls, _OPAQUE):
            kinds |= 2
    return kinds


def is_live_sequence(value):
    return isinstance(value, (list, tuple, range)) or (
        hasattr(type(value), '__len__') and hasattr(type(value), '__getitem__')
        and not isinstance(value, dict)
    )


def snapshot(value):
    return list(value)


def names(value):
    if isinstance(value, dict):
        return [name for name in value if isinstance(name, str) and not name.startswith('_')]
    found = {}
    kind = type(value)
    for name in getattr(kind, '_fields', ()):
        found[name] = None
    state = getattr(value, '__dict__', None)
    if isinstance(state, dict):
        for name in state:
            found[name] = None
    for klass in kind.__mro__:
        for name, member in vars(klass).items():
            if isinstance(member, property):
                found[name] = None
    return [name for name in found if isinstance(name, str) and not name.startswith('_')]
";

        private static readonly object Gate = new object();
        private static PythonCodec codec;
        private static PyObject helpers;
        private static PyObject adaptHook;
        private static PyObject modelHook;
        private static PyObject rootTypeHook;
        private static PyObject rootHook;
        private static PyObject boolType;

        /// <summary>
        /// Installs the codecs once per interpreter and replaces the Python hooks.
        /// </summary>
        /// <param name="adapt">
        /// Called with each plain Python object converted to <see cref="object"/>; returns a CLR
        /// object to use instead (pyRevit's Reactive models return their managed binding model),
        /// or <c>None</c> to use a <see cref="PythonObjectProxy"/>.
        /// </param>
        /// <param name="findModel">
        /// Called with an <see cref="ExpandoObject"/> going back to Python; returns the Python
        /// model it represents, or <c>None</c> to pass the managed object through.
        /// </param>
        /// <remarks>
        /// Safe to call again, for example when <c>pyrevit.forms</c> is re-imported after a
        /// Reload: the codecs stay registered and only the hooks change. Codecs registered
        /// after other conversions took place apply to them too, because registration clears
        /// pythonnet's conversion caches.
        /// </remarks>
        public static void Register(PyObject adapt, PyObject findModel) {
            using (Py.GIL()) {
                lock (Gate) {
                    adaptHook = Callable(adapt);
                    modelHook = Callable(findModel);
                    if (codec != null)
                        return;
                    helpers = PyModule.FromString("pyrevit_forms_binding", HelperSource);
                    using (var builtins = Py.Import("builtins"))
                        boolType = builtins.GetAttr("bool");
                    codec = new PythonCodec();
                    PyObjectConversions.RegisterDecoder(codec);
                    PyObjectConversions.RegisterEncoder(codec);
                    PythonEngine.AddShutdownHandler(Reset);
                }
            }
        }

        /// <summary>
        /// Lets a CLR parameter or property whose type a Python form's native root satisfies, such
        /// as <c>Window.Owner</c> or <c>WindowInteropHelper(Window)</c>, accept the Python form
        /// itself, as IronPython does for its CLR-derived windows.
        /// </summary>
        /// <param name="rootTypeOf">
        /// Called once per Python class and CLR target type; returns the CLR type of the native
        /// root its instances own, or <c>None</c> for classes that own none.
        /// </param>
        /// <param name="rootOf">Called with a form; returns its current native root, or <c>None</c>.</param>
        /// <remarks>
        /// Targets typed <see cref="object"/> and the collection interfaces keep the conversions
        /// described on this class, so a form stored in <c>Tag</c> or <c>DataContext</c> still comes
        /// back to Python as itself. Safe to call again; later hooks replace earlier ones, but
        /// pythonnet keeps the per-type answers of <paramref name="rootTypeOf"/> it already cached.
        /// </remarks>
        public static void RegisterRoots(PyObject rootTypeOf, PyObject rootOf) {
            using (Py.GIL()) {
                lock (Gate) {
                    rootTypeHook = Callable(rootTypeOf);
                    rootHook = Callable(rootOf);
                }
            }
        }

        private static PyObject Callable(PyObject hook) {
            return hook == null || hook.IsNone() ? null : hook;
        }

        private static void Reset() {
            lock (Gate) {
                codec = null;
                helpers = null;
                adaptHook = null;
                modelHook = null;
                rootTypeHook = null;
                rootHook = null;
                boolType = null;
            }
        }

        internal static int Classify(PyType type) {
            using (var kinds = helpers.InvokeMethod("classify", type))
                return kinds.As<int>();
        }

        /// <summary>Returns the CLR type of the native root owned by instances of <paramref name="type"/>, or null.</summary>
        /// <remarks>Requires the GIL.</remarks>
        internal static Type RootTypeOf(PyType type) {
            var hook = rootTypeHook;
            if (hook == null)
                return null;
            using (var rootType = hook.Invoke(type))
                return rootType.IsNone() ? null : rootType.AsManagedObject(typeof(Type)) as Type;
        }

        /// <summary>Returns the native root currently owned by <paramref name="value"/>, or null.</summary>
        /// <remarks>Requires the GIL.</remarks>
        internal static object RootOf(PyObject value) {
            var hook = rootHook;
            if (hook == null)
                return null;
            using (var root = hook.Invoke(value))
                return root.IsNone() ? null : root.AsManagedObject(typeof(object));
        }

        internal static bool IsLiveSequence(PyObject value) {
            using (var live = helpers.InvokeMethod("is_live_sequence", value))
                return live.IsTrue();
        }

        internal static PyObject Snapshot(PyObject value) {
            return helpers.InvokeMethod("snapshot", value);
        }

        internal static List<string> NamesOf(PyObject value) {
            var result = new List<string>();
            using (var names = helpers.InvokeMethod("names", value)) {
                var count = names.Length();
                for (var index = 0; index < count; index++) {
                    using (var name = names.GetItem(index))
                        result.Add(name.As<string>());
                }
            }
            return result;
        }

        /// <summary>Converts a plain Python object for a CLR <see cref="object"/> target.</summary>
        /// <remarks>Requires the GIL. Takes ownership of <paramref name="value"/>.</remarks>
        internal static object AdaptObject(PyObject value) {
            var hook = adaptHook;
            if (hook != null) {
                using (var adapted = hook.Invoke(value)) {
                    if (!adapted.IsNone() && adapted.Handle != value.Handle) {
                        var managed = adapted.AsManagedObject(typeof(object));
                        if (!(managed is PyObject)) {
                            value.Dispose();
                            return managed;
                        }
                    }
                }
            }
            return PythonObjectProxy.For(value);
        }

        /// <summary>Returns the Python model behind a managed binding model, or null.</summary>
        /// <remarks>Requires the GIL.</remarks>
        internal static PyObject FindModel(ExpandoObject model) {
            var hook = modelHook;
            if (hook == null)
                return null;
            using (var native = PyObject.FromManagedObject(model)) {
                var found = hook.Invoke(native);
                if (found.IsNone()) {
                    found.Dispose();
                    return null;
                }
                return found;
            }
        }

        /// <summary>
        /// Converts a Python value read by WPF into the CLR value bindings, triggers, sorting
        /// and converters expect.
        /// </summary>
        /// <remarks>
        /// Requires the GIL. Takes ownership of <paramref name="value"/>. <c>bool</c> becomes
        /// <see cref="bool"/>, <c>int</c> becomes <see cref="int"/> or, outside its range,
        /// <see cref="long"/>, <c>float</c> becomes <see cref="double"/>, <c>str</c> becomes
        /// <see cref="string"/>, <c>None</c> becomes null, lists and tuples become
        /// <see cref="PythonListProxy"/>, dicts become a <see cref="PythonObjectProxy"/> over
        /// their string keys, and everything else converts as a CLR
        /// <see cref="object"/> argument would.
        /// </remarks>
        internal static object ToClr(PyObject value) {
            if ((PyList.IsListType(value) || PyTuple.IsTupleType(value)) && !value.HasAttr("_fields"))
                return PythonListProxy.For(value);
            if (PyDict.IsDictType(value))
                return PythonObjectProxy.For(value);
            using (value) {
                if (value.IsNone())
                    return null;
                if (value.IsInstance(boolType))
                    return value.IsTrue();
                if (PyInt.IsIntType(value))
                    return ToClrInteger(value);
                if (PyFloat.IsFloatType(value))
                    return value.As<double>();
                if (PyString.IsStringType(value))
                    return value.As<string>();
                return value.AsManagedObject(typeof(object));
            }
        }

        private static object ToClrInteger(PyObject value) {
            return TryToClrInteger(value, out var result) ? result : value.AsManagedObject(typeof(object));
        }

        /// <summary>Converts a Python int to <see cref="int"/>, or <see cref="long"/> outside its range.</summary>
        /// <remarks>Requires the GIL. False when the value does not fit a <see cref="long"/>.</remarks>
        internal static bool TryToClrInteger(PyObject value, out object result) {
            using (var bits = value.InvokeMethod("bit_length")) {
                if (bits.As<int>() > 63) {
                    result = null;
                    return false;
                }
            }
            var number = value.As<long>();
            result = number >= int.MinValue && number <= int.MaxValue ? (object)(int)number : number;
            return true;
        }

        /// <summary>
        /// Converts a value WPF writes back into the Python value to store, unwrapping proxies
        /// and managed binding models to their original Python objects.
        /// </summary>
        /// <remarks>Requires the GIL.</remarks>
        internal static PyObject ToPython(object value) {
            switch (value) {
                case null:
                    return PyObject.FromManagedObject(null);
                case IPythonValue python:
                    return python.Source;
                case ExpandoObject model:
                    return FindModel(model) ?? PyObject.FromManagedObject(model);
                default:
                    return value.ToPython();
            }
        }
    }
}
