using System;

namespace pyRevitAssemblyBuilder.AssemblyMaker
{
    /// <summary>
    /// Reads the extension name out of generated assembly names of the form
    /// <c>pyRevit_{revitVersion}_{hash}_{extensionName}</c>.
    /// </summary>
    internal static class ExtensionAssemblyName
    {
        private const string Prefix = "pyRevit_";
        private const int PartCount = 4;

        /// <summary>
        /// True when the name part of <paramref name="assemblyName"/> equals
        /// <paramref name="extensionName"/> exactly (case-insensitive), so
        /// <c>MyTools</c> never matches <c>Tools</c>.
        /// </summary>
        public static bool BelongsTo(string assemblyName, string extensionName)
        {
            if (assemblyName == null || extensionName == null
                || !assemblyName.StartsWith(Prefix, StringComparison.Ordinal))
                return false;

            var parts = assemblyName.Split(new[] { '_' }, PartCount);
            return parts.Length == PartCount
                && string.Equals(parts[PartCount - 1], extensionName, StringComparison.OrdinalIgnoreCase);
        }
    }
}
