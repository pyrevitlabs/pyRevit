using System;
using System.Collections.Generic;
using Microsoft.Scripting;
using Microsoft.Scripting.Hosting;

namespace PyRevitLoader {
    /// <summary>
    /// Error reporter for IronPython script compilation.
    /// Implements ErrorListener for ScriptSource.Compile().
    /// </summary>
    public class ErrorReporter : ErrorListener {
        private readonly List<string> _errors = new List<string>();

        /// <summary>
        /// Gets the list of error messages.
        /// </summary>
        public IList<string> Errors => _errors;

        /// <summary>
        /// Gets the errors as an array for backward compatibility.
        /// </summary>
        public Array ErrorsArray => _errors.ToArray();

        /// <summary>
        /// Returns a string representation of all errors.
        /// </summary>
        public override string ToString() {
            return string.Join(Environment.NewLine, _errors);
        }

        /// <summary>
        /// Called when an error occurs during compilation.
        /// </summary>
        public override void ErrorReported(ScriptSource source, string message, SourceSpan span, int errorCode, Severity severity) {
            var path = source?.Path ?? "unknown";
            _errors.Add(string.Format("{0} ({1},{2}): {3}", path, span.Start.Line, span.Start.Column, message));
        }

        /// <summary>
        /// Clears all collected errors.
        /// </summary>
        public void Clear() {
            _errors.Clear();
        }
    }
}
