using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;

using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI {
    /// <summary>
    /// Masks personally identifying and internal-infrastructure values in the
    /// <c>pyrevit env --redact</c> report so it can be pasted into a public issue.
    /// </summary>
    /// <remarks>
    /// Redaction is pattern based and best effort: it covers user account names,
    /// user-profile folders, UNC server names and Git/lookup URLs. It cannot know
    /// that an arbitrary PATH entry or directory name is confidential, so the
    /// report should still be skimmed before it is shared.
    /// </remarks>
    internal static class PyRevitEnvRedactor {
        internal const string Placeholder = "***redacted***";
        private const string Mask = "***";

        private static readonly HashSet<string> AccountKeys =
            new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "execUser", "activeUser" };

        private static readonly string[] PublicHosts = {
            "github.com",
            "githubusercontent.com",
            "gitlab.com",
            "bitbucket.org"
        };

        private static readonly TimeSpan RegexTimeout = TimeSpan.FromSeconds(1);

        private static readonly Regex UrlPattern = new Regex(
            @"(?<scheme>[A-Za-z][A-Za-z0-9+.\-]*)://(?<auth>[^/\s""<>?#]*@)?(?<host>\[[^\]\s""'<>/]+\]|[^/\s""'<>:@?#]+)(?<port>:\d+)?(?<path>/(?:[^\s""<>?#']|'(?=[^\s""<>]))*)?(?<query>[?#](?:[^\s""<>']|'(?=[^\s""<>]))*)?",
            RegexOptions.Compiled);

        private static readonly Regex ScpUrlPattern = new Regex(
            @"(?<![\w@.\-/:])(?<user>[\w.\-]+)@(?<host>[A-Za-z0-9][A-Za-z0-9.\-]*):(?<path>(?!//)[^\s""'<>]+)",
            RegexOptions.Compiled);

        private static readonly Regex ScpHostOnlyPattern = new Regex(
            @"(?<![\w@.\-/:*])(?<host>[A-Za-z0-9][A-Za-z0-9\-]*(?:\.[A-Za-z0-9\-]+)+):(?<path>(?!//|\d+(?:/|\s|$)|\\)[^\s""'<>]+)",
            RegexOptions.Compiled);

        private static readonly Regex ProfileFolderPattern = new Regex(
            @"(?<=[\\/]Users[\\/])[^\\/""<>:*?|]*[^\\/\s""<>:*?|]",
            RegexOptions.Compiled | RegexOptions.IgnoreCase);

        private static readonly Regex UncServerPattern = new Regex(
            @"(?<![\\\w])\\\\(?![?.]\\)[^\\/\s""'<>]+",
            RegexOptions.Compiled);

        internal static string RedactText(string text, string userProfilePath = null, string userName = null) {
            if (string.IsNullOrEmpty(text))
                return text;

            text = RedactUrls(text);
            text = RedactScpUrls(text);
            text = RedactScpHostOnlyUrls(text);
            text = RedactUserProfile(text, userProfilePath);
            text = ProfileFolderPattern.Replace(text, Mask);
            text = UncServerPattern.Replace(text, @"\\" + Mask);
            return RedactUserNameSegments(text, userName);
        }

        /// <summary>
        /// Redacts every string value of a <c>pyrevit env --json</c> document and
        /// replaces the account names under <c>execUser</c> and <c>activeUser</c>
        /// with <see cref="Placeholder"/>. The document structure is preserved.
        /// </summary>
        internal static string RedactJson(string json, string userProfilePath = null, string userName = null) {
            var root = JsonConvert.DeserializeObject<JContainer>(
                json,
                new JsonSerializerSettings { DateParseHandling = DateParseHandling.None });

            foreach (var value in root.Descendants().OfType<JValue>().Where(v => v.Type == JTokenType.String).ToList()) {
                var isAccount = value.Parent is JProperty property && AccountKeys.Contains(property.Name);
                value.Value = isAccount ? Placeholder : RedactText((string)value.Value, userProfilePath, userName);
            }

            return root.ToString(Formatting.None);
        }

        /// <summary>
        /// Runs <paramref name="report"/> with standard output filtered through
        /// <see cref="RedactText"/>, then restores the original writer.
        /// </summary>
        /// <remarks>
        /// Each write call is redacted on its own, immediately, so the colour the
        /// console wrapper applies around a write still covers the text. A value
        /// split over several calls, such as a URL written in two parts, is not
        /// matched; the report printers format each line into one string.
        /// </remarks>
        internal static void RunRedacted(Action report, string userProfilePath = null, string userName = null) {
            var original = Console.Out;
            var filter = new RedactingWriter(original, userProfilePath, userName);
            Console.SetOut(filter);
            try {
                report();
            }
            finally {
                Console.SetOut(original);
            }
        }

        private static string RedactUrls(string text) =>
            UrlPattern.Replace(text, match => {
                var scheme = match.Groups["scheme"].Value;
                var host = match.Groups["host"].Value;
                var port = match.Groups["port"].Value;
                var path = match.Groups["path"].Value;
                var query = match.Groups["query"].Value;
                var hasAuth = match.Groups["auth"].Success;
                var authMask = hasAuth ? Mask + "@" : string.Empty;
                var queryMask = query.Length == 0 ? string.Empty : query[0] + Mask;

                if (IsPublicHost(host))
                    return string.Format("{0}://{1}{2}{3}{4}{5}", scheme, authMask, host, port, path, queryMask);

                var maskedPath = path.Length == 0
                    ? string.Empty
                    : "/" + Mask + (path.EndsWith(".git", StringComparison.OrdinalIgnoreCase) ? ".git" : string.Empty);
                return string.Format("{0}://{1}{2}{3}{4}", scheme, authMask, Mask, maskedPath, queryMask);
            });

        private static string RedactScpUrls(string text) =>
            ScpUrlPattern.Replace(text, match => {
                var host = match.Groups["host"].Value;
                var path = match.Groups["path"].Value;
                if (IsPublicHost(host))
                    return string.Format("{0}@{1}:{2}", Mask, host, path);

                var gitSuffix = path.EndsWith(".git", StringComparison.OrdinalIgnoreCase) ? ".git" : string.Empty;
                return string.Format("{0}@{0}:{0}{1}", Mask, gitSuffix);
            });

        private static string RedactScpHostOnlyUrls(string text) =>
            ScpHostOnlyPattern.Replace(text, match => {
                var host = match.Groups["host"].Value;
                var path = match.Groups["path"].Value;
                if (IsPublicHost(host))
                    return match.Value;

                var gitSuffix = path.EndsWith(".git", StringComparison.OrdinalIgnoreCase) ? ".git" : string.Empty;
                return string.Format("{0}:{0}{1}", Mask, gitSuffix);
            });

        private static string RedactUserNameSegments(string text, string userName) {
            if (string.IsNullOrWhiteSpace(userName))
                return text;

            var segment = @"(?<=[\\/:])" + Regex.Escape(userName) + @"(?=[\\/\s""'<>]|$)";
            return Regex.Replace(text, segment, Mask, RegexOptions.IgnoreCase, RegexTimeout);
        }

        private static bool IsPublicHost(string host) =>
            PublicHosts.Any(publicHost =>
                host.Equals(publicHost, StringComparison.OrdinalIgnoreCase)
                || host.EndsWith("." + publicHost, StringComparison.OrdinalIgnoreCase));

        private static string RedactUserProfile(string text, string userProfilePath) {
            if (string.IsNullOrWhiteSpace(userProfilePath))
                return text;

            var trimmed = userProfilePath.TrimEnd('\\', '/');
            var parent = Path.GetDirectoryName(trimmed);
            if (string.IsNullOrEmpty(parent))
                return text;

            var masked = Path.Combine(parent, Mask);
            text = MaskFolder(text, trimmed, masked);
            return MaskFolder(text, trimmed.Replace('\\', '/'), masked.Replace('\\', '/'));
        }

        private static string MaskFolder(string text, string folder, string masked) =>
            Regex.Replace(
                text,
                Regex.Escape(folder) + @"(?:[^\\/""<>:*?|]*[^\\/\s""<>:*?|])?",
                masked.Replace("$", "$$"),
                RegexOptions.IgnoreCase,
                RegexTimeout);

        private sealed class RedactingWriter : TextWriter {
            private readonly TextWriter inner;
            private readonly string userProfilePath;
            private readonly string userName;

            internal RedactingWriter(TextWriter inner, string userProfilePath, string userName) {
                this.inner = inner;
                this.userProfilePath = userProfilePath;
                this.userName = userName;
            }

            public override Encoding Encoding => inner.Encoding;

            public override void Write(char value) => inner.Write(value);

            public override void Write(string value) => inner.Write(RedactText(value, userProfilePath, userName));

            public override void Write(char[] buffer, int index, int count) =>
                Write(new string(buffer, index, count));

            public override void Flush() => inner.Flush();
        }
    }
}
