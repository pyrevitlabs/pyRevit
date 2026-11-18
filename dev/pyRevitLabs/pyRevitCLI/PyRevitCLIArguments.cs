using System.Collections.Generic;
using System.IO;
using DocoptNet;

using pyRevitLabs.Common;

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

        /// <summary>
        /// Parses a Revit year argument.
        /// </summary>
        /// <exception cref="PyRevitException">The text is not a whole number.</exception>
        internal static int RevitYear(string text) {
            if (int.TryParse(text, out var year))
                return year;
            throw new PyRevitException(string.Format("Invalid Revit year \"{0}\"", text));
        }

        /// <summary>
        /// Parses a <c>--limit</c> argument, falling back to <paramref name="defaultLimit"/> when it was not given.
        /// </summary>
        /// <exception cref="PyRevitException">The text is not a positive whole number.</exception>
        internal static int Limit(string text, int defaultLimit) {
            if (text is null)
                return defaultLimit;
            if (int.TryParse(text, out var limit) && limit > 0)
                return limit;
            throw new PyRevitException(string.Format("Invalid limit \"{0}\": expected a positive whole number", text));
        }

        /// <summary>
        /// Returns <paramref name="path"/> after checking that it names an existing file.
        /// </summary>
        /// <param name="path">The path given on the command line.</param>
        /// <param name="description">What the file is, for the error message.</param>
        /// <exception cref="PyRevitException">No file exists at the path.</exception>
        internal static string ExistingFile(string path, string description) {
            if (File.Exists(path))
                return path;
            throw new PyRevitException(string.Format("The {0} \"{1}\" does not exist", description, path));
        }

        /// <summary>
        /// Returns <paramref name="path"/> after checking that it names an existing folder.
        /// </summary>
        /// <param name="path">The path given on the command line.</param>
        /// <param name="description">What the folder is, for the error message.</param>
        /// <exception cref="PyRevitException">No folder exists at the path.</exception>
        internal static string ExistingDirectory(string path, string description) {
            if (Directory.Exists(path))
                return path;
            throw new PyRevitException(string.Format("The {0} \"{1}\" does not exist", description, path));
        }
    }
}
