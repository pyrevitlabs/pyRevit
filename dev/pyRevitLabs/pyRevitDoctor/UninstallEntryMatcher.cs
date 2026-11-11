using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace pyRevitDoctor {
    /// <summary>
    /// The values of one subkey under a registry <c>Uninstall</c> key that matching needs.
    /// </summary>
    public sealed class UninstallEntry {
        public string SubKeyName { get; init; }
        public string DisplayName { get; init; }
        public string UninstallString { get; init; }
        public string InstallLocation { get; init; }
    }

    /// <summary>
    /// What <see cref="UninstallEntryMatcher.Classify"/> decided for an uninstall entry.
    /// </summary>
    public enum UninstallVerdict {
        NotPyRevit,
        Purge,
        SkipInstallPresent,
    }

    /// <summary>
    /// Decides which registry <c>Uninstall</c> entries belong to pyRevit installers and may be purged.
    /// </summary>
    /// <remarks>
    /// Inno Setup writes <c>{AppId}_is1</c> and every pyRevit Inno installer of one kind shares an AppId,
    /// so the key alone cannot tell a leftover entry from the current install. Such entries, and those
    /// matched only by display name, are purged only when stale or when forced.
    /// </remarks>
    public static class UninstallEntryMatcher {
        const string InnoSuffix = "_is1";
        const string ProductNamePrefix = "pyRevit";

        /// <summary>
        /// Classifies one uninstall entry against the catalog.
        /// </summary>
        /// <param name="pathExists">File system probe, replaced by tests.</param>
        /// <param name="force">Purge entries whose install is still present too.</param>
        /// <remarks>
        /// Braced MSI product codes and the legacy <c>{Name} {Version}</c> subkey names are purged without
        /// the staleness check, as before. An entry that records no verifiable path counts as present, so a
        /// live install is never purged on a guess; <paramref name="force"/> removes it.
        /// </remarks>
        public static UninstallVerdict Classify(
            UninstallEntry entry,
            IReadOnlyCollection<Product> products,
            Func<string, bool> pathExists,
            bool force) {
            var subKeyName = entry.SubKeyName ?? string.Empty;
            var isInno = subKeyName.EndsWith(InnoSuffix, StringComparison.OrdinalIgnoreCase);
            var normalizedId = NormalizeId(isInno ? subKeyName.Substring(0, subKeyName.Length - InnoSuffix.Length) : subKeyName);

            if (!isInno && products.Any(product => NormalizeId(product.Key) == normalizedId))
                return UninstallVerdict.Purge;

            if (products.Any(product => subKeyName == $"{product.Name} {product.Version}"))
                return UninstallVerdict.Purge;

            var matchesInnoAppId = isInno && products.Any(product => NormalizeId(product.Key) == normalizedId);
            var matchesDisplayName = entry.DisplayName?.StartsWith(ProductNamePrefix, StringComparison.OrdinalIgnoreCase) == true;
            if (!matchesInnoAppId && !matchesDisplayName)
                return UninstallVerdict.NotPyRevit;

            return force || IsStale(entry, pathExists)
                ? UninstallVerdict.Purge
                : UninstallVerdict.SkipInstallPresent;
        }

        /// <summary>
        /// True when the entry records an uninstaller or install location that no longer exists.
        /// </summary>
        public static bool IsStale(UninstallEntry entry, Func<string, bool> pathExists) {
            var recordedPaths = new[] { ExtractExecutablePath(entry.UninstallString), TrimQuotes(entry.InstallLocation)?.TrimEnd('\\', '/') }
                .Where(path => !string.IsNullOrWhiteSpace(path) && Path.IsPathRooted(path));
            return recordedPaths.Any(path => !pathExists(path));
        }

        /// <summary>
        /// Returns the executable of an <c>UninstallString</c> such as <c>"C:\dir\unins000.exe" /SILENT</c>.
        /// </summary>
        public static string ExtractExecutablePath(string uninstallString) {
            var command = uninstallString?.Trim();
            if (string.IsNullOrEmpty(command))
                return null;
            if (command[0] == '"') {
                var closingQuote = command.IndexOf('"', 1);
                return closingQuote > 0 ? command.Substring(1, closingQuote - 1) : command.Substring(1);
            }
            var exeEnd = command.IndexOf(".exe", StringComparison.OrdinalIgnoreCase);
            return exeEnd >= 0 ? command.Substring(0, exeEnd + ".exe".Length) : command;
        }

        static string TrimQuotes(string value) => value?.Trim().Trim('"');

        static string NormalizeId(string id) => id?.Trim().Trim('{', '}').ToLowerInvariant();
    }
}
