using System;

using pyRevitLabs.Json.Linq;

namespace pyRevitCLI {
    /// <summary>
    /// A JSON-RPC failure a modern-era request ends with: carries the code, message and optional
    /// <c>data</c> the server writes as the error response.
    /// </summary>
    internal sealed class McpRequestException : Exception {
        public McpRequestException(int code, string message, JObject details = null) : base(message) {
            Code = code;
            Details = details;
        }

        public int Code { get; }

        public JObject Details { get; }
    }

    /// <summary>
    /// The MCP 2026-07-28 revision's wire rules for <c>pyrevit mcp</c>: stateless requests carrying their
    /// protocol version in <c>params._meta</c>, <c>server/discover</c>, and the result envelope.
    /// </summary>
    /// <remarks>
    /// A request is modern-era when its <c>_meta</c> holds either of the two required protocol keys; every other
    /// request, including <c>initialize</c>, keeps the legacy semantics and output byte for byte.
    /// </remarks>
    internal static class McpProtocol {
        public const string Version = "2026-07-28";
        public const string VersionKey = "io.modelcontextprotocol/protocolVersion";
        public const string CapabilitiesKey = "io.modelcontextprotocol/clientCapabilities";
        public const string ServerInfoKey = "io.modelcontextprotocol/serverInfo";
        public const string SkillsExtensionKey = "io.modelcontextprotocol/skills";
        public const long CacheTtlMs = 300000;
        public const int InvalidParams = -32602;
        public const int UnsupportedVersion = -32022;

        /// <summary>
        /// True when <paramref name="parameters"/> carries modern-era protocol metadata.
        /// </summary>
        public static bool IsModern(JObject parameters) {
            return parameters["_meta"] is JObject meta && (meta.Property(VersionKey) != null || meta.Property(CapabilitiesKey) != null);
        }

        /// <summary>
        /// Checks the required <c>_meta</c> keys of a modern-era request.
        /// </summary>
        /// <exception cref="McpRequestException">
        /// -32602 when a required key is missing or malformed; -32022 when the version is not <see cref="Version"/>.
        /// </exception>
        public static void Validate(JObject parameters) {
            var meta = (JObject)parameters["_meta"];
            var requested = (meta[VersionKey] as JValue)?.Value as string;
            if (requested == null)
                throw new McpRequestException(InvalidParams, "Invalid params: '_meta' needs a string '" + VersionKey + "'.");
            if (meta[CapabilitiesKey] is not JObject)
                throw new McpRequestException(InvalidParams, "Invalid params: '_meta' needs an object '" + CapabilitiesKey + "'.");
            if (requested != Version) {
                throw new McpRequestException(UnsupportedVersion, "Unsupported protocol version", new JObject {
                    ["supported"] = new JArray(Version),
                    ["requested"] = requested,
                });
            }
        }

        /// <summary>
        /// Marks <paramref name="result"/> as a modern-era result and adds the server info to its <c>_meta</c>;
        /// <paramref name="cacheable"/> adds the <c>ttlMs</c> and <c>cacheScope</c> hints for results that are
        /// identical for every client.
        /// </summary>
        public static JObject Complete(JObject result, bool cacheable = false) {
            result.AddFirst(new JProperty("resultType", "complete"));
            var meta = result["_meta"] as JObject ?? new JObject();
            meta[ServerInfoKey] = new JObject { ["name"] = "pyrevit", ["version"] = PyRevitCLI.CLIInfoVersion };
            result["_meta"] = meta;
            if (cacheable) {
                result["ttlMs"] = CacheTtlMs;
                result["cacheScope"] = "public";
            }
            return result;
        }

        /// <summary>
        /// The <c>server/discover</c> result: the one supported version, the capabilities (the skills extension is
        /// always declared) and the same instructions legacy clients get from <c>initialize</c>.
        /// </summary>
        public static JObject Discover(string instructions) {
            return Complete(new JObject {
                ["supportedVersions"] = new JArray(Version),
                ["capabilities"] = new JObject {
                    ["tools"] = new JObject(),
                    ["resources"] = new JObject(),
                    ["extensions"] = new JObject { [SkillsExtensionKey] = new JObject() },
                },
                ["instructions"] = instructions,
            }, cacheable: true);
        }
    }
}
