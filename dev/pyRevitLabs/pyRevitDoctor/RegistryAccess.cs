using System;
using System.Security;
using Microsoft.Win32;

namespace pyRevitDoctor {
    /// <summary>
    /// Opens the registry keys <c>purge-installs</c> scans, turning every failure into a reported one.
    /// </summary>
    /// <remarks>
    /// Invariant: a key that cannot be opened is never silently skipped. It counts as a failure of the
    /// <see cref="PurgeSession"/>, so the command exits non-zero and later targets are still scanned.
    /// A key that does not exist is not a failure.
    /// </remarks>
    static class RegistryAccess {
        /// <summary>
        /// Opens a key for writing, or read-only when writing is denied or the session is a dry run.
        /// </summary>
        /// <param name="description">Names the key in the failure report.</param>
        /// <param name="openSubKey">Opens the key, with <c>true</c> for write access. Returns <c>null</c> when the key is missing.</param>
        /// <returns>The key, or <c>null</c> when it is missing or could not be opened.</returns>
        public static RegistryKey TryOpenForPurge(PurgeSession session, string description, Func<bool, RegistryKey> openSubKey) {
            try {
                return OpenWithReadFallback(session.Options.DryRun, openSubKey);
            }
            catch (Exception ex) {
                session.ReportFailed(description, ex, "Opening");
                return null;
            }
        }

        static RegistryKey OpenWithReadFallback(bool dryRun, Func<bool, RegistryKey> openSubKey) {
            try {
                return openSubKey(!dryRun);
            }
            catch (Exception ex) when (ex is UnauthorizedAccessException or SecurityException) {
                return openSubKey(false);
            }
        }
    }
}
