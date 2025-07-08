using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using static pyRevitExtensionParser.BundleParser;

namespace pyRevitExtensionParser
{
    public static class ExtensionParser
    {
        public static IEnumerable<ParsedExtension> ParseInstalledExtensions()
        {
            //TODO Parse config file to get custom extension roots

            //TODO : Add support for custom extension roots
            var extensionRoots = GetExtensionRoots();

            // TODO check if they are activated in the config
            //ParseExtensionByName

            foreach (var root in extensionRoots)
            {
                if (!Directory.Exists(root))
                    continue;

                foreach (var extDir in Directory.GetDirectories(root, "*.extension"))
                {
                    var extName = Path.GetFileNameWithoutExtension(extDir);
                    var children = ParseComponents(extDir, extName);

                    var bundlePath = Path.Combine(extDir, "bundle.yaml");
                    ParsedBundle parsedBundle = File.Exists(bundlePath)
                        ? BundleYamlParser.Parse(bundlePath)
                        : null;

                    var parsedExtension = new ParsedExtension
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

                    ReorderByLayout(parsedExtension);

                    yield return parsedExtension;
                }
            }
        }

        /// <summary>
        /// Recursively reorders the given component’s Children in-place
        /// according to its own LayoutOrder.  If LayoutOrder is null or empty,
        /// we skip sorting here but still recurse into children.
        /// </summary>
        private static void ReorderByLayout(ParsedComponent component)
        {
            if (component.LayoutOrder != null && component.LayoutOrder.Count > 0)
            {

                var nameIndexMap = component.LayoutOrder
                    .Select((name, index) => new { name, index })
                    .GroupBy(x => x.name)
                    .ToDictionary(g => g.Key, g => g.First().index);

                component.Children.Sort((a, b) =>
                {
                    int ix = nameIndexMap.TryGetValue(a.DisplayName, out int indexA) ? indexA : int.MaxValue;
                    int iy = nameIndexMap.TryGetValue(b.DisplayName, out int indexB) ? indexB : int.MaxValue;
                    return ix.CompareTo(iy);
                });

                var slideoutIndex = component.LayoutOrder.IndexOf(">>>>>");

                if (slideoutIndex >= 0)
                {
                    var nextelem = component.LayoutOrder[slideoutIndex + 1];
                    component.Children.Find(c => c.Name == nextelem).HasSlideout = true;
                }
            }

            foreach (var child in component.Children)
            {
                ReorderByLayout(child);
            }
        }

        private static List<string> GetExtensionRoots()
        {
            var roots = new List<string>();

            var current = Path.GetDirectoryName(typeof(ExtensionParser).Assembly.Location);
            var defaultPath = Path.GetFullPath(Path.Combine(current, "..", "..", "..", "..", "extensions"));

            // Monkey patch for testing bench
            if (!Directory.Exists(defaultPath))
            {
                defaultPath = Path.Combine(current, "..", "..", "..", "..", "..", "..", "extensions");
            }

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

                string title = null, author = null, doc = null;
                if (scriptPath != null)
                {
                    (title, author, doc) = ReadPythonScriptConstants(scriptPath);
                }

                var bundleInComponent = File.Exists(bundleFile) ? BundleYamlParser.Parse(bundleFile) : null;

                components.Add(new ParsedComponent
                {
                    Name = namePart,
                    DisplayName = displayName,
                    ScriptPath = scriptPath,
                    Tooltip = doc ?? $"Command: {namePart}", // Set Tooltip from __doc__ or fallback
                    UniqueId = SanitizeClassName(fullPath.ToLowerInvariant()),
                    Type = componentType,
                    Children = children,
                    BundleFile = File.Exists(bundleFile) ? bundleFile : null,
                    LayoutOrder = bundleInComponent?.LayoutOrder,
                    Title = title,
                    Author = author
                });
            }

            return components;
        }

        private static string SanitizeClassName(string name)
        {
            var sb = new StringBuilder();
            foreach (char c in name)
                sb.Append(char.IsLetterOrDigit(c) ? c : '_');
            return sb.ToString();
        }

        private static (string title, string author, string doc) ReadPythonScriptConstants(string scriptPath)
        {
            string title = null, author = null, doc = null;

            foreach (var line in File.ReadLines(scriptPath))
            {
                if (line.StartsWith("__title__"))
                {
                    title = ExtractPythonConstantValue(line);
                }
                else if (line.StartsWith("__author__"))
                {
                    author = ExtractPythonConstantValue(line);
                }
                else if (line.StartsWith("__doc__"))
                {
                    author = ExtractPythonConstantValue(line);
                }
            }

            return (title, author, doc);
        }

        private static string ExtractPythonConstantValue(string line)
        {
            var parts = line.Split(new[] { '=' }, 2, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length == 2)
            {
                var value = parts[1].Trim().Trim('\'', '"');
                return value;
            }
            return null;
        }

        public class ParsedExtension : ParsedComponent
        {
            public string Directory { get; set; }
            public Dictionary<string, string> Titles { get; set; }
            public Dictionary<string, string> Tooltips { get; set; }
            public string MinRevitVersion { get; set; }
            public EngineConfig Engine { get; set; }
            public ExtensionConfig Config { get; set; }
            public string GetHash() => Directory.GetHashCode().ToString("X");

            private static readonly CommandComponentType[] _allowedTypes = new[] {
            CommandComponentType.PushButton,
            CommandComponentType.PanelButton,
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
            public bool HasSlideout { get; set; } = false;
            public string Title { get; set; }
            public string Author { get; set; }
        }
        public class EngineConfig
        {
            public bool Clean { get; set; }
            public bool FullFrame { get; set; }
            public bool Persistent { get; set; }
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
        public class ExtensionConfig
        {
            public string Name { get; set; }
            public bool Disabled { get; set; }
            public bool PrivateRepo { get; set; }
            public string Username { get; set; }
            public string Password { get; set; }
        }
    }
}
