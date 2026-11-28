using System;
using System.IO;
using System.Text.RegularExpressions;

namespace pyRevitLabs.Common {
    /// <summary>
    /// Compares two git clone sources (remote URLs, scp-style addresses or local paths) without any
    /// network or repository access. Each source is parsed once into a comparison key.
    /// </summary>
    internal static class RemoteAddressComparer {
        private static readonly Regex DrivePathPattern = new Regex("^[a-z]:(/|$)", RegexOptions.IgnoreCase);
        private static readonly Regex UrlRemotePattern =
            new Regex("^[a-z][a-z0-9+.-]+://(?:[^/@]*@)?([^/]+)/?(.*)$", RegexOptions.IgnoreCase);
        private static readonly Regex ScpRemotePattern = new Regex(@"^(?:[^@/\s]+@)?([^/:@\s]+):(?!//)(.+)$");

        /// <summary>Tells whether both sources resolve to the same repository; false when either is blank.</summary>
        public static bool AreSame(string first, string second) {
            if (string.IsNullOrWhiteSpace(first) || string.IsNullOrWhiteSpace(second))
                return false;
            var firstAddress = Parse(first);
            var secondAddress = Parse(second);
            if (ScpPathRootDiffers(firstAddress, secondAddress) || ScpPathRootDiffers(secondAddress, firstAddress))
                return false;
            return firstAddress.Key == secondAddress.Key;
        }

        private sealed class Address {
            public string Key;
            public bool IsScp;
            public bool ScpPathIsAbsolute;
            public bool IsSshUrl;
        }

        private static bool ScpPathRootDiffers(Address scp, Address other) {
            if (!scp.IsScp)
                return false;
            if (other.IsScp)
                return scp.ScpPathIsAbsolute != other.ScpPathIsAbsolute;
            return other.IsSshUrl && !scp.ScpPathIsAbsolute;
        }

        private static Address Parse(string source) {
            var value = source.Trim().Replace('\\', '/');
            if (value.StartsWith("file:", StringComparison.OrdinalIgnoreCase)) {
                try {
                    value = new Uri(value).LocalPath.Replace('\\', '/');
                }
                catch (UriFormatException) {
                    return new Address { Key = "raw:" + value.ToLowerInvariant() };
                }
            }
            var isDrivePath = DrivePathPattern.IsMatch(value);
            var match = UrlRemotePattern.Match(value);
            var isScp = false;
            if (!match.Success) {
                match = ScpRemotePattern.Match(value);
                isScp = match.Success;
            }
            if (match.Success && !isDrivePath) {
                var rawPath = match.Groups[2].Value;
                var path = rawPath.Trim('/');
                if (path.EndsWith(".git", StringComparison.OrdinalIgnoreCase))
                    path = path.Substring(0, path.Length - 4).TrimEnd('/');
                return new Address {
                    Key = "remote:" + match.Groups[1].Value.ToLowerInvariant() + "/" + path,
                    IsScp = isScp,
                    IsSshUrl = !isScp && value.StartsWith("ssh://", StringComparison.OrdinalIgnoreCase),
                    ScpPathIsAbsolute = isScp && rawPath.StartsWith("/"),
                };
            }
            string fullPath;
            try {
                fullPath = Path.GetFullPath(value);
            }
            catch (Exception) {
                fullPath = value;
            }
            return new Address { Key = "local:" + fullPath.Replace('\\', '/').TrimEnd('/').ToLowerInvariant() };
        }
    }
}
