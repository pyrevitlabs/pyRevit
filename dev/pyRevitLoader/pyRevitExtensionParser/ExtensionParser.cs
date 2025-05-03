using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace pyRevitExtensionParser
{
    public static class ExtensionParser
    {
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

            var configPath = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                "pyRevit",
                "pyRevit_config.ini");

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

        private static List<ParsedComponent> ParseComponents(
            string baseDir,
            string extensionName,
            string parentPath = null)
        {
            var components = new List<ParsedComponent>();

            foreach (var dir in Directory.GetDirectories(baseDir))
            {
                var ext = Path.GetExtension(dir);
                var componentType = CommandComponentTypeExtensions.FromExtension(ext);
                if (componentType == CommandComponentType.Unknown)
                    continue;

                var namePart = Path.GetFileNameWithoutExtension(dir).Replace(" ", "");
                var fullPath = string.IsNullOrEmpty(parentPath)
                    ? $"{extensionName}_{namePart}"
                    : $"{parentPath}_{namePart}";

                string scriptPath = null;

                if (componentType == CommandComponentType.UrlButton)
                {
                    var yaml = Path.Combine(dir, "bundle.yaml");
                    if (File.Exists(yaml))
                        scriptPath = yaml;
                }

                if (scriptPath == null)
                {
                    scriptPath = Directory
                        .EnumerateFiles(dir, "*", SearchOption.TopDirectoryOnly)
                        .FirstOrDefault(f => f.EndsWith("script.py", StringComparison.OrdinalIgnoreCase));
                }

                if (scriptPath == null &&
                   (componentType == CommandComponentType.PushButton ||
                    componentType == CommandComponentType.SmartButton))
                {
                    var yaml = Path.Combine(dir, "bundle.yaml");
                    if (File.Exists(yaml))
                        scriptPath = yaml;
                }

                var children = ParseComponents(dir, extensionName, fullPath);

                components.Add(new ParsedComponent
                {
                    Name = namePart,
                    ScriptPath = scriptPath,
                    Tooltip = $"Command: {namePart}",
                    UniqueId = fullPath.ToLowerInvariant(),
                    Type = componentType,
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

        public string GetHash() => Directory.GetHashCode().ToString("X");

        private static readonly CommandComponentType[] _allowedTypes = new[]
        {
            CommandComponentType.PushButton,
            CommandComponentType.SmartButton,
            CommandComponentType.UrlButton
        };

        public IEnumerable<ParsedComponent> CollectCommandComponents()
            => Collect(this.Children);

        private IEnumerable<ParsedComponent> Collect(IEnumerable<ParsedComponent> list)
        {
            if (list == null) yield break;

            foreach (var comp in list)
            {
                if (comp.Children != null)
                {
                    foreach (var child in Collect(comp.Children))
                        yield return child;
                }

                if (_allowedTypes.Contains(comp.Type))
                    yield return comp;
            }
        }
    }

    public class ParsedComponent
    {
        public string Name { get; set; }
        public string ScriptPath { get; set; }
        public string Tooltip { get; set; }
        public string UniqueId { get; set; }
        public CommandComponentType Type { get; set; }
        public List<ParsedComponent> Children { get; set; }
    }

    public class ParsedExtensionMetadata
    {
        public string Author { get; set; }
        public string Version { get; set; }
        public string Description { get; set; }
    }

    public enum CommandComponentType
    {
        Unknown,
        Tab,
        Panel,
        PushButton,
        PullDown,
        SplitButton,
        SplitPushButton,
        Stack,
        SmartButton,
        PanelButton,
        LinkButton,
        InvokeButton,
        UrlButton,
        ContentButton,
        NoButton
    }

    public static class CommandComponentTypeExtensions
    {
        public static CommandComponentType FromExtension(string ext)
        {
            switch (ext.ToLowerInvariant())
            {
                case ".tab": return CommandComponentType.Tab;
                case ".panel": return CommandComponentType.Panel;
                case ".pushbutton": return CommandComponentType.PushButton;
                case ".pulldown": return CommandComponentType.PullDown;
                case ".splitbutton": return CommandComponentType.SplitButton;
                case ".splitpushbutton": return CommandComponentType.SplitPushButton;
                case ".stack": return CommandComponentType.Stack;
                case ".smartbutton": return CommandComponentType.SmartButton;
                case ".panelbutton": return CommandComponentType.PanelButton;
                case ".linkbutton": return CommandComponentType.LinkButton;
                case ".invokebutton": return CommandComponentType.InvokeButton;
                case ".urlbutton": return CommandComponentType.UrlButton;
                case ".content": return CommandComponentType.ContentButton;
                case ".nobutton": return CommandComponentType.NoButton;
                default: return CommandComponentType.Unknown;
            }
        }

        public static string ToExtension(this CommandComponentType type)
        {
            switch (type)
            {
                case CommandComponentType.Tab: return ".tab";
                case CommandComponentType.Panel: return ".panel";
                case CommandComponentType.PushButton: return ".pushbutton";
                case CommandComponentType.PullDown: return ".pulldown";
                case CommandComponentType.SplitButton: return ".splitbutton";
                case CommandComponentType.SplitPushButton: return ".splitpushbutton";
                case CommandComponentType.Stack: return ".stack";
                case CommandComponentType.SmartButton: return ".smartbutton";
                case CommandComponentType.PanelButton: return ".panelbutton";
                case CommandComponentType.LinkButton: return ".linkbutton";
                case CommandComponentType.InvokeButton: return ".invokebutton";
                case CommandComponentType.UrlButton: return ".urlbutton";
                case CommandComponentType.ContentButton: return ".content";
                case CommandComponentType.NoButton: return ".nobutton";
                default: return string.Empty;
            }
        }
    }
}
