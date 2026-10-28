using System.Collections;
using System.Collections.Generic;
using PyDict = Python.Runtime.PyDict;
using PyObject = Python.Runtime.PyObject;
using PySequence = Python.Runtime.PySequence;
using PyString = Python.Runtime.PyString;

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>
    /// Converts table arguments passed to <see cref="ScriptOutput"/> into rows and cells, whether
    /// they arrive as CLR collections (IronPython) or pythonnet wrappers (CPython).
    /// </summary>
    /// <remarks>
    /// Invariant: exceptions raised by the caller's Python objects while they are iterated
    /// propagate to the script; a table is never silently truncated. Strings are always one cell.
    /// </remarks>
    internal static class PythonTableData {
        /// <summary>Markdown printed instead of a table when the table data yields no rows.</summary>
        public const string NoRowsWarning = "### :warning: No table_data list";

        /// <summary>
        /// Returns the markdown to print instead of the table when <paramref name="rows"/> is empty,
        /// or <c>null</c> when the table should be rendered.
        /// </summary>
        public static string EmptyTableWarning(List<List<string>> rows) {
            return rows.Count == 0 ? NoRowsWarning : null;
        }

        public static List<List<string>> ToRows(object value) {
            var rows = new List<List<string>>();
            if (value == null || value is string)
                return rows;

            if (value is PyObject pythonValue) {
                if (!IsIterable(pythonValue))
                    return rows;
                foreach (var row in Iterate(pythonValue))
                    rows.Add(ToCells(row));
                return rows;
            }

            var enumerable = value as IEnumerable;
            if (enumerable == null)
                return rows;

            foreach (var rowObj in enumerable)
                rows.Add(ToCells(rowObj));
            return rows;
        }

        public static List<string> ToCells(object value) {
            var items = new List<string>();
            if (value == null)
                return items;
            if (value is string) {
                items.Add((string)value);
                return items;
            }

            if (value is PyObject pythonValue) {
                if (!IsIterable(pythonValue)) {
                    items.Add(ToCellText(pythonValue));
                    return items;
                }

                foreach (var item in Iterate(pythonValue))
                    items.Add(ToCellText(item));
                return items;
            }

            var enumerable = value as IEnumerable;
            if (enumerable == null) {
                items.Add(value.ToString());
                return items;
            }

            foreach (var item in enumerable)
                items.Add(item == null ? string.Empty : item.ToString());
            return items;
        }

        public static Dictionary<string, string> ToDictionary(object value) {
            var result = new Dictionary<string, string>();
            if (value == null)
                return result;

            if (value is PyObject pythonValue && PyDict.IsDictType(pythonValue)) {
                using (var pythonDictionary = new PyDict(pythonValue)) {
                    using (var entries = pythonDictionary.Items()) {
                        foreach (var entry in Iterate(entries)) {
                            using (var key = entry.GetItem(0)) {
                                using (var entryValue = entry.GetItem(1)) {
                                    result[key.ToString()] = entryValue.ToString();
                                }
                            }
                        }
                    }
                }
                return result;
            }

            var dictionary = value as IDictionary;
            if (dictionary != null) {
                foreach (DictionaryEntry entry in dictionary)
                    result[entry.Key.ToString()] = entry.Value?.ToString() ?? string.Empty;
            }

            return result;
        }

        /// <summary>
        /// Iterates <paramref name="iterable"/> like Python's <c>iter()</c>, disposing each item
        /// once the consumer moves past it.
        /// </summary>
        /// <exception cref="Python.Runtime.PythonException">
        /// Raised by the object's own iteration; it is not caught here.
        /// </exception>
        public static IEnumerable<PyObject> Iterate(PyObject iterable) {
            using (var iterator = iterable.GetIterator()) {
                while (iterator.MoveNext()) {
                    var item = iterator.Current;
                    try {
                        yield return item;
                    }
                    finally {
                        item.Dispose();
                    }
                }
            }
        }

        private static bool IsIterable(PyObject value) {
            if (PyString.IsStringType(value))
                return false;
            return value.IsIterable() || PySequence.IsSequenceType(value);
        }

        private static string ToCellText(PyObject value) {
            return value.IsNone() ? string.Empty : value.ToString();
        }
    }
}
