using System;
using System.Linq;

namespace pyRevitDoctor {
    /// <summary>
    /// The command name and options parsed from the doctor's command line.
    /// </summary>
    public static class DoctorArguments {
        /// <summary>
        /// Returns the first argument that is not an option, or <c>null</c> when there is none, so
        /// <c>--dryrun purge-installs</c> and <c>purge-installs --dryrun</c> name the same command.
        /// </summary>
        public static string FindCommandName(string[] args) =>
            args.FirstOrDefault(arg => !arg.StartsWith("-", StringComparison.Ordinal));
    }
}
