using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace pyRevitExtensionParser
{
    public static class ExtensionParser
    {
        private static readonly string[] BundleTypes = new[]
        {
            ".tab", ".panel", ".stack", ".splitbutton", ".splitpushbutton", ".pulldown", ".smartbutton", ".pushbutton"
        };

        public static IEnumerable<ParsedExtension> ParseInstalledExtensions()
        {
            var extensionRoots = GetExtensionRoots();

            foreach (var root in extensionRoots)
            {
                if (!Directory.Exists(root))
                    continue;

                foreach (var extDir in Directory.GetDirectories(root, "*.extension"))
                {
                    var extName = Path.GetFileNameWithoutExtension(extDir);
                    var metadata = ParseMetadata(extDir);
                    var children = ParseComponents(extDir, extName);

                    yield return new ParsedExtension
                    {
                        Name = extName,
                        Directory = extDir,
                        Metadata = metadata,
                        Children = children
                    };
                }
            }
        }

        private static List<string> GetExtensionRoots()
        {
            var roots = new List<string>();

            var current = Path.GetDirectoryName(typeof(ExtensionParser).Assembly.Location);
            var defaultPath = Path.GetFullPath(Path.Combine(current, "..", "..", "..", "..", "extensions"));
            roots.Add(defaultPath);

            var configPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "pyRevit", "pyRevit_config.ini");
            if (File.Exists(configPath))
            {
                foreach (var line in File.ReadAllLines(configPath))
                {
                    if (line.StartsWith("userextensions =", StringComparison.OrdinalIgnoreCase))
                    {
                        var parts = line.Substring("userextensions =".Length).Split(';');
                        foreach (var part in parts)
                        {
                            var path = part.Trim();
                            if (!string.IsNullOrWhiteSpace(path))
                                roots.Add(path);
                        }
                    }
                }
            }

            return roots;
        }

        private static List<ParsedComponent> ParseComponents(string baseDir, string extensionName, string parentPath = null)
        {
            var components = new List<ParsedComponent>();

            foreach (var dir in Directory.GetDirectories(baseDir))
            {
                var type = Path.GetExtension(dir);
                if (!BundleTypes.Contains(type))
                    continue;

                var namePart = Path.GetFileNameWithoutExtension(dir)
                                    .Replace(" ", "");

                // Construct full ID path with hyphens
                var fullPath = string.IsNullOrEmpty(parentPath)
                    ? $"{extensionName}-{namePart}"
                    : $"{parentPath}-{namePart}";

                var children = ParseComponents(dir, extensionName, fullPath);
                var scriptPath = Path.Combine(dir, "script.py");

                components.Add(new ParsedComponent
                {
                    Name = namePart,
                    ScriptPath = File.Exists(scriptPath) ? scriptPath : null,
                    Tooltip = $"Command: {namePart}",
                    UniqueId = fullPath.ToLowerInvariant(),
                    Type = type,
                    Children = children
                });
            }

            return components;
        }

        private static ParsedExtensionMetadata ParseMetadata(string extPath)
        {
            var yamlPath = Path.Combine(extPath, "extension.yaml");
            if (!File.Exists(yamlPath))
                return null;

            var metadata = new ParsedExtensionMetadata();
            foreach (var line in File.ReadLines(yamlPath))
            {
                var trimmed = line.Trim();
                if (trimmed.StartsWith("author:"))
                    metadata.Author = trimmed.Substring("author:".Length).Trim();
                else if (trimmed.StartsWith("version:"))
                    metadata.Version = trimmed.Substring("version:".Length).Trim();
                else if (trimmed.StartsWith("description:"))
                    metadata.Description = trimmed.Substring("description:".Length).Trim();
            }

            return metadata;
        }
    }

    public class ParsedExtension
    {
        public string Name { get; set; }
        public string Directory { get; set; }
        public ParsedExtensionMetadata Metadata { get; set; }
        public List<ParsedComponent> Children { get; set; }
    }

    public class ParsedComponent
    {
        public string Name { get; set; }
        public string ScriptPath { get; set; }
        public string Tooltip { get; set; }
        public string UniqueId { get; set; }
        public string Type { get; set; }
        public List<ParsedComponent> Children { get; set; }
    }

    public class ParsedExtensionMetadata
    {
        public string Author { get; set; }
        public string Version { get; set; }
        public string Description { get; set; }
    }
}