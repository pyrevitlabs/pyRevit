using System.Collections.Generic;
using DocoptNet;

namespace pyRevitCLI {
    internal static class PyRevitCLIArguments {
        /// <summary>
        /// Returns the text docopt parsed for <paramref name="key"/>, or <paramref name="defaultValue"/> when the
        /// key is not in <paramref name="arguments"/> or was not given on the command line.
        /// </summary>
        /// <remarks>
        /// docopt lists every option of the usage patterns, with a null value when the option was not given, so
        /// the default has to apply to a listed option too. Without that, <c>pyrevit env path list</c> sent an
        /// empty scope instead of <c>user</c>.
        /// </remarks>
        internal static string Value(IDictionary<string, ValueObject> arguments, string key, string defaultValue = null) {
            if (arguments is null || !arguments.TryGetValue(key, out var value) || value is null)
                return defaultValue;
            return value.Value as string ?? defaultValue;
        }
    }
}
