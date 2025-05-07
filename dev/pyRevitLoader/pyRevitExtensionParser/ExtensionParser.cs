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
                    var children = ParseComponents(extDir, extName);

                    // Parse bundle.yaml if present in the extension folder
                    var bundlePath = Path.Combine(extDir, "bundle.yaml");
                    ParsedBundle parsedBundle = File.Exists(bundlePath)
                        ? BundleYamlParser.Parse(bundlePath)
                        : null;

                    yield return new ParsedExtension
                    {
                        Name = extName,
                        Directory = extDir,
                        Children = children,
                        LayoutOrder = parsedBundle?.LayoutOrder,
                        Titles = parsedBundle?.Titles,
                        Tooltips = parsedBundle?.Tooltips,
                        MinRevitVersion = parsedBundle?.MinRevitVersion,
                        Engine = parsedBundle?.Engine
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
                var displayName = Path.GetFileNameWithoutExtension(dir);
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

                var bundleFile = Path.Combine(dir, "bundle.yaml");
                var children = ParseComponents(dir, extensionName, fullPath);

                var bundleInComponent = File.Exists(bundleFile) ? BundleYamlParser.Parse(bundleFile) : null;

                components.Add(new ParsedComponent
                {
                    Name = namePart,
                    DisplayName = displayName,
                    ScriptPath = scriptPath,
                    Tooltip = $"Command: {namePart}",
                    UniqueId = fullPath.ToLowerInvariant(),
                    Type = componentType,
                    Children = children,
                    BundleFile = File.Exists(bundleFile) ? bundleFile : null,
                    LayoutOrder = bundleInComponent?.LayoutOrder // Save layout as a property
                });
            }

            return components;
        }
    }

    public class ParsedExtension
    {
        public string Name { get; set; }
        public string DisplayName { get; set; }
        public string Directory { get; set; }
        public List<ParsedComponent> Children { get; set; }
        public List<string> LayoutOrder { get; set; }
        public Dictionary<string, string> Titles { get; set; }
        public Dictionary<string, string> Tooltips { get; set; }
        public string MinRevitVersion { get; set; }
        public EngineConfig Engine { get; set; }

        public string GetHash() => Directory.GetHashCode().ToString("X");

        private static readonly CommandComponentType[] _allowedTypes = new[] {
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
        public string DisplayName { get; set; }
        public string ScriptPath { get; set; }
        public string Tooltip { get; set; }
        public string UniqueId { get; set; }
        public CommandComponentType Type { get; set; }
        public List<ParsedComponent> Children { get; set; }
        public string BundleFile { get; set; }
        public List<string> LayoutOrder { get; set; }
    }

    public class ParsedBundle
    {
        public List<string> LayoutOrder { get; set; } = new List<string>();
        public Dictionary<string, string> Titles { get; set; } = new Dictionary<string, string>();
        public Dictionary<string, string> Tooltips { get; set; } = new Dictionary<string, string>();
        public string Author { get; set; }
        public string MinRevitVersion { get; set; }
        public EngineConfig Engine { get; set; } = new EngineConfig();
    }

    public class EngineConfig
    {
        public bool Clean { get; set; }
        public bool FullFrame { get; set; }
        public bool Persistent { get; set; }
    }

    public static class BundleYamlParser
    {
        public static ParsedBundle Parse(string filePath)
        {
            var parsed = new ParsedBundle();
            var lines = File.ReadAllLines(filePath);
            string currentSection = null;

            foreach (var raw in lines)
            {
                var line = raw.TrimEnd();
                if (string.IsNullOrWhiteSpace(line)) continue;

                if (!line.StartsWith(" ") && line.Contains(":"))
                {
                    var parts = line.Split(new[] { ':' }, 2);
                    currentSection = parts[0].Trim().ToLowerInvariant();
                    var value = parts[1].Trim();

                    switch (currentSection)
                    {
                        case "author":
                            parsed.Author = value; break;
                        case "min_revit_version":
                            parsed.MinRevitVersion = value; break;
                        case "engine":
                        case "title":
                        case "tooltip":
                        case "layout": 
                            break;
                    }
                }
                else if (line.StartsWith("  ") && currentSection == "layout" && line.TrimStart().StartsWith("-"))
                {
                    parsed.LayoutOrder.Add(line.TrimStart().Substring(1).Trim());
                }
                else if (line.StartsWith("  ") && (currentSection == "title" || currentSection == "tooltip"))
                {
                    var parts = line.Trim().Split(new[] { ':' }, 2);
                    if (parts.Length == 2)
                    {
                        var lang = parts[0].Trim();
                        var text = parts[1].Trim();
                        if (currentSection == "title")
                            parsed.Titles[lang] = text;
                        else
                            parsed.Tooltips[lang] = text;
                    }
                }
                else if (line.StartsWith("  ") && currentSection == "engine" && line.Contains(":"))
                {
                    var parts = line.Trim().Split(new[] { ':' }, 2);
                    var key = parts[0].Trim().ToLowerInvariant();
                    var val = parts[1].Trim().ToLowerInvariant();

                    switch (key)
                    {
                        case "clean": parsed.Engine.Clean = val == "true"; break;
                        case "full_frame": parsed.Engine.FullFrame = val == "true"; break;
                        case "persistent": parsed.Engine.Persistent = val == "true"; break;
                    }
                }
            }

            return parsed;
        }
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
