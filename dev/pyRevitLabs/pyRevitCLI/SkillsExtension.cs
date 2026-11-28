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
    /// Invariant: <c>frontmatter</c> must equal the <c>SKILL.md</c> front matter, so only flat <c>key: value</c>
    /// scalar lines whose values the flat reader decodes exactly as YAML would are accepted (no indentation, lists,
    /// comments, block or flow values, tags, anchors, quote escapes); <c>name</c> and
    /// <c>description</c> must be present under exactly those keys.
    /// A skill is skipped whole, never served partly, with one line on standard error (standard output carries
    /// the protocol), when its directory name differs from its <c>name</c>, its front matter is not flat or lacks
    /// a description, it breaks a file limit, a file is not valid UTF-8, or its folder holds anything that is not a
    /// listed markdown file (the manifest must be complete).
    /// Construction reads the folder and the server builds one per request, so an answer is fresh when it is
    /// made; clients may still cache it for the <c>ttlMs</c> it carries.
    /// </remarks>
    internal sealed class SkillsExtension {
        private const string MarkdownMimeType = "text/markdown";
        private const char ByteOrderMark = '﻿';
        private static readonly Encoding StrictUtf8 = new UTF8Encoding(false, true);

        private sealed record ServedFile(string Uri, string Name, string Description, byte[] Bytes, string Text);

        private readonly List<JObject> skills = new List<JObject>();
        private readonly Dictionary<string, JObject> skillsByUri = new Dictionary<string, JObject>(StringComparer.Ordinal);
        private readonly List<ServedFile> files = new List<ServedFile>();
        private readonly Dictionary<string, ServedFile> filesByUri = new Dictionary<string, ServedFile>(StringComparer.Ordinal);

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
                var name = Path.GetFileName(directory);
                try {
                    var problem = Add(directory, name);
                    if (problem != null)
                        Skip(name, problem);
                }
                catch (Exception ex) when (SkillFiles.IsRecoverable(ex) || ex is DecoderFallbackException) {
                    Skip(name, ex.Message);
                }
            }
        }

        private static void Skip(string name, string reason) {
            Console.Error.WriteLine($"pyrevit mcp: skill '{SkillFiles.Printable(name)}' is not served: {SkillFiles.Printable(reason)}");
        }

        private string Add(string directory, string name) {
            if ((File.GetAttributes(directory) & FileAttributes.ReparsePoint) != 0)
                return "its folder is a link";
            if (!File.Exists(Path.Combine(directory, SkillFiles.SkillFile)))
                return null;

            var shipped = SkillFiles.LoadShipped(directory, name);
            var listed = new HashSet<string>(shipped.Files.Select(file => file.Path), StringComparer.OrdinalIgnoreCase);
            var unlisted = UnlistedEntry(directory, directory, listed);
            if (unlisted != null)
                return $"it holds '{unlisted}', which its manifest could not list";

            var loaded = ReadFiles(name, shipped.Files);
            var skillUri = $"skill://{name}/{SkillFiles.SkillFile}";
            var problem = FrontMatterProblem(loaded.Single(file => file.Uri == skillUri).Text, name, out var frontmatter);
            if (problem != null)
                return problem;

            var served = loaded
                .Select(file => file.Uri == skillUri ? file with { Name = name, Description = frontmatter.Value<string>("description") } : file)
                .ToList();
            var entry = new JObject { ["uri"] = skillUri, ["frontmatter"] = frontmatter, ["resources"] = Manifest(served, skillUri) };
            skills.Add(entry);
            skillsByUri[skillUri] = entry;
            foreach (var file in served) {
                files.Add(file);
                filesByUri[file.Uri] = file;
            }
            return null;
        }

        private static string UnlistedEntry(string root, string directory, HashSet<string> listed) {
            foreach (var entry in Directory.EnumerateFileSystemEntries(directory)) {
                var attributes = File.GetAttributes(entry);
                var isDirectory = (attributes & FileAttributes.Directory) != 0;
                if ((attributes & FileAttributes.ReparsePoint) != 0 || (!isDirectory && !listed.Contains(entry)))
                    return Path.GetRelativePath(root, entry);
                var nested = isDirectory ? UnlistedEntry(root, entry, listed) : null;
                if (nested != null)
                    return nested;
            }
            return null;
        }

        private static List<ServedFile> ReadFiles(string name, List<(string Relative, string Path)> shippedFiles) {
            var loaded = new List<ServedFile>();
            foreach (var (relative, path) in shippedFiles) {
                var bytes = File.ReadAllBytes(path);
                if (bytes.Length > SkillFiles.MaxFileBytes)
                    throw new IOException($"{relative} is over the {SkillFiles.MaxFileBytes / 1024} KiB limit");
                var uriPath = string.Join("/", relative.Split('/').Select(Uri.EscapeDataString));
                loaded.Add(new ServedFile($"skill://{name}/{uriPath}", name + "/" + relative, null, bytes, StrictUtf8.GetString(bytes)));
            }
            return loaded;
        }

        private static JArray Manifest(List<ServedFile> served, string skillUri) {
            return new JArray(served
                .OrderBy(file => file.Uri == skillUri ? 0 : 1)
                .ThenBy(file => file.Uri, StringComparer.Ordinal)
                .Select(file => new JObject {
                    ["uri"] = file.Uri,
                    ["digest"] = "sha256:" + Convert.ToHexString(SHA256.HashData(file.Bytes)).ToLowerInvariant(),
                    ["size"] = file.Bytes.Length,
                }));
        }

        /// <summary>
        /// Checks that <paramref name="text"/> has front matter the flat reader reads without loss and
        /// returns it as <paramref name="frontmatter"/>; otherwise says what is wrong.
        /// </summary>
        private static string FrontMatterProblem(string text, string directoryName, out JObject frontmatter) {
            frontmatter = null;
            var lines = text.TrimStart(ByteOrderMark).Split(new[] { "\r\n", "\n", "\r" }, StringSplitOptions.None);
            if (lines[0].Trim() != "---")
                return "SKILL.md has no front matter";
            var keys = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var closed = false;
            for (var index = 1; index < lines.Length && !closed; index++) {
                var line = lines[index];
                closed = line.Trim() == "---";
                if (closed || line.Trim().Length == 0)
                    continue;
                var problem = LineProblem(line, keys);
                if (problem != null)
                    return $"front matter line {index} {problem}";
            }
            if (!closed)
                return "front matter is not closed";

            frontmatter = new JObject();
            foreach (var pair in PyRevitAgentSkills.ParseFrontMatter(lines))
                frontmatter[pair.Key] = pair.Value;
            if (frontmatter.Value<string>("name") != directoryName || !SkillFiles.IsValidName(directoryName))
                return "its name is missing or differs from its folder name";
            if (string.IsNullOrWhiteSpace(frontmatter.Value<string>("description")))
                return "its description is missing or empty";
            return null;
        }

        private static string LineProblem(string line, HashSet<string> keys) {
            var separator = line.IndexOf(':');
            var value = separator > 0 ? line.Substring(separator + 1).Trim() : string.Empty;
            if (char.IsWhiteSpace(line[0]))
                return "is indented";
            if (line[0] == '-' || line[0] == '#')
                return "is a list item or a comment";
            if (separator <= 0)
                return "is not 'key: value'";
            if (value.Length == 0)
                return "has an empty value";
            var valueProblem = ValueProblem(value);
            if (valueProblem != null)
                return valueProblem;
            return keys.Add(line.Substring(0, separator).Trim()) ? null : "repeats a key";
        }

        /// <summary>
        /// Allowlist of the values the flat reader reads exactly as a YAML parser would: a plain scalar that starts
        /// with no YAML indicator and holds no comment or nested mapping, or a quoted scalar whose content has no
        /// escape, no doubled or embedded quote and nothing after the closing quote.
        /// </summary>
        private static string ValueProblem(string value) {
            const string indicators = "!&*%@`|>[{#-?:,]}'\"";
            if (value[0] == '"' || value[0] == '\'') {
                var quote = value[0];
                if (value.Length < 2 || value[value.Length - 1] != quote)
                    return "has an unclosed quote or text after the closing quote";
                var content = value.Substring(1, value.Length - 2);
                if (content.IndexOf(quote) >= 0 || (quote == '"' && content.Contains('\\')))
                    return "has a quoted value with an escape or an embedded quote";
                return null;
            }
            if (indicators.IndexOf(value[0]) >= 0)
                return "starts with a YAML indicator";
            if (value.Contains(" #"))
                return "has a trailing comment";
            if (value.Contains(": ") || value.EndsWith(":"))
                return "has a nested mapping";
            return null;
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
        /// <c>resources/list</c>: every served file, one page. A skill's <c>SKILL.md</c> entry is named and described
        /// after its front matter; other files are named by their path.
        /// </summary>
        /// <exception cref="McpRequestException">-32602 for a non-empty cursor.</exception>
        public JObject ResourcesList(JObject parameters = null) {
            RequireNoCursor(parameters);
            return McpProtocol.Complete(new JObject {
                ["resources"] = new JArray(files.Select(file => {
                    var resource = new JObject { ["uri"] = file.Uri, ["name"] = file.Name, ["mimeType"] = MarkdownMimeType, ["size"] = file.Bytes.Length };
                    if (file.Description != null)
                        resource["description"] = file.Description;
                    return resource;
                })),
            }, cacheable: true);
        }

        /// <summary>
        /// <c>resources/read</c>: the text of one served file, decoded from the bytes its manifest digest covers.
        /// </summary>
        /// <exception cref="McpRequestException">-32602 with the URI for anything not in a manifest.</exception>
        public JObject Read(string uri) {
            if (uri == null || !filesByUri.TryGetValue(uri, out var file))
                throw Unknown(uri);
            return McpProtocol.Complete(new JObject {
                ["contents"] = new JArray(new JObject { ["uri"] = uri, ["mimeType"] = MarkdownMimeType, ["text"] = file.Text }),
            }, cacheable: true);
        }
    }
}
