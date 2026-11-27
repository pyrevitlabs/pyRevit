using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;

using pyRevitLabs.Json.Linq;

namespace pyRevitCLI {
    /// <summary>
    /// Serves the skills shipped with pyRevit through the MCP Skills extension
    /// (<c>io.modelcontextprotocol/skills</c>): <c>skills/list</c>, <c>skills/get</c>, <c>resources/list</c>
    /// and <c>resources/read</c> on <c>skill://&lt;name&gt;/...</c> URIs.
    /// </summary>
    /// <remarks>
    /// Invariant: only the shipped skills folder is read, so user skills are never listed or reachable.
    /// Invariant: a file is read once; its digest, size and served text all come from the same bytes, and the
    /// text is decoded without altering a BOM or line endings. A URI resolves only by exact lookup in the
    /// manifest built here, so no path outside a skill's own markdown files can be requested.
    /// A skill is skipped, not served partly, when its directory name differs from its <c>name</c> front matter,
    /// when it is over the file limits or when a file is not valid UTF-8.
    /// Construction reads the folder; the server builds one per request, so answers are never stale.
    /// </remarks>
    internal sealed class SkillsExtension {
        private const string MarkdownMimeType = "text/markdown";
        private static readonly Encoding StrictUtf8 = new UTF8Encoding(false, true);

        private readonly List<JObject> skills = new List<JObject>();
        private readonly Dictionary<string, JObject> skillsByUri = new Dictionary<string, JObject>(StringComparer.Ordinal);
        private readonly List<(string Uri, string Name, long Size)> files = new List<(string, string, long)>();
        private readonly Dictionary<string, string> textsByUri = new Dictionary<string, string>(StringComparer.Ordinal);

        /// <param name="shippedRoot">The shipped skills folder; null or missing serves nothing.</param>
        public SkillsExtension(string shippedRoot) {
            if (shippedRoot == null || !Directory.Exists(shippedRoot))
                return;
            string[] directories;
            try {
                directories = Directory.GetDirectories(shippedRoot);
            }
            catch (Exception ex) when (SkillFiles.IsRecoverable(ex)) {
                return;
            }
            foreach (var directory in directories.OrderBy(path => path, StringComparer.Ordinal)) {
                try {
                    Add(directory);
                }
                catch (Exception ex) when (SkillFiles.IsRecoverable(ex) || ex is DecoderFallbackException) {
                }
            }
        }

        private void Add(string directory) {
            var name = Path.GetFileName(directory);
            if ((File.GetAttributes(directory) & FileAttributes.ReparsePoint) != 0 || !File.Exists(Path.Combine(directory, SkillFiles.SkillFile)))
                return;

            var shipped = SkillFiles.LoadShipped(directory, name);
            var loaded = new List<(string Uri, string Relative, byte[] Bytes, string Text)>();
            foreach (var (relative, path) in shipped.Files) {
                var bytes = File.ReadAllBytes(path);
                if (bytes.Length > SkillFiles.MaxFileBytes)
                    return;
                var uriPath = string.Join("/", relative.Split('/').Select(Uri.EscapeDataString));
                loaded.Add(($"skill://{name}/{uriPath}", relative, bytes, StrictUtf8.GetString(bytes)));
            }
            var skillFile = loaded.FirstOrDefault(file => file.Relative == SkillFiles.SkillFile);
            if (skillFile.Bytes == null)
                return;

            var frontMatter = PyRevitAgentSkills.ParseFrontMatter(FrontMatterLines(skillFile.Text));
            if (!frontMatter.TryGetValue("name", out var declared) || declared != name || !SkillFiles.IsValidName(name))
                return;

            var frontmatter = new JObject();
            foreach (var pair in frontMatter)
                frontmatter[pair.Key] = pair.Value;
            var manifest = new JArray(loaded
                .OrderBy(file => file.Relative == SkillFiles.SkillFile ? 0 : 1)
                .ThenBy(file => file.Relative, StringComparer.Ordinal)
                .Select(file => new JObject {
                    ["uri"] = file.Uri,
                    ["digest"] = "sha256:" + Convert.ToHexString(SHA256.HashData(file.Bytes)).ToLowerInvariant(),
                    ["size"] = file.Bytes.Length,
                }));
            var entry = new JObject { ["uri"] = skillFile.Uri, ["frontmatter"] = frontmatter, ["resources"] = manifest };
            skills.Add(entry);
            skillsByUri[skillFile.Uri] = entry;
            foreach (var file in loaded) {
                files.Add((file.Uri, name + "/" + file.Relative, file.Bytes.Length));
                textsByUri[file.Uri] = file.Text;
            }
        }

        private static string[] FrontMatterLines(string text) {
            return text.TrimStart('﻿').Split(new[] { "\r\n", "\n", "\r" }, StringSplitOptions.None);
        }

        private static void RequireNoCursor(JObject parameters) {
            var cursor = parameters?["cursor"];
            if (cursor == null || cursor.Type == JTokenType.Null)
                return;
            if (cursor is JValue value && value.Value is string text && text.Length == 0)
                return;
            throw new McpRequestException(McpProtocol.InvalidParams, "Invalid params: 'cursor' is not a cursor this server issued.");
        }

        private static McpRequestException Unknown(string uri) {
            return new McpRequestException(McpProtocol.InvalidParams, "Unknown skill or resource", new JObject { ["uri"] = uri });
        }

        /// <summary>
        /// <c>skills/list</c>: every served skill in one page.
        /// </summary>
        /// <exception cref="McpRequestException">-32602 for a non-empty cursor; no page ever has a next one.</exception>
        public JObject List(JObject parameters = null) {
            RequireNoCursor(parameters);
            return McpProtocol.Complete(new JObject { ["skills"] = new JArray(skills.Select(skill => skill.DeepClone())) }, cacheable: true);
        }

        /// <summary>
        /// <c>skills/get</c>: the list entry of the skill whose <c>SKILL.md</c> URI is <paramref name="uri"/>.
        /// </summary>
        /// <exception cref="McpRequestException">-32602 with the URI for an unknown skill.</exception>
        public JObject Get(string uri) {
            if (uri == null || !skillsByUri.TryGetValue(uri, out var skill))
                throw Unknown(uri);
            return McpProtocol.Complete(new JObject { ["skill"] = skill.DeepClone() }, cacheable: true);
        }

        /// <summary>
        /// <c>resources/list</c>: every served file, one page.
        /// </summary>
        /// <exception cref="McpRequestException">-32602 for a non-empty cursor.</exception>
        public JObject ResourcesList(JObject parameters = null) {
            RequireNoCursor(parameters);
            return McpProtocol.Complete(new JObject {
                ["resources"] = new JArray(files.Select(file => new JObject {
                    ["uri"] = file.Uri,
                    ["name"] = file.Name,
                    ["mimeType"] = MarkdownMimeType,
                    ["size"] = file.Size,
                })),
            }, cacheable: true);
        }

        /// <summary>
        /// <c>resources/read</c>: the text of one served file, decoded from the bytes its manifest digest covers.
        /// </summary>
        /// <exception cref="McpRequestException">-32602 with the URI for anything not in a manifest.</exception>
        public JObject Read(string uri) {
            if (uri == null || !textsByUri.TryGetValue(uri, out var text))
                throw Unknown(uri);
            return McpProtocol.Complete(new JObject {
                ["contents"] = new JArray(new JObject { ["uri"] = uri, ["mimeType"] = MarkdownMimeType, ["text"] = text }),
            }, cacheable: true);
        }
    }
}
