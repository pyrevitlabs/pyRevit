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
        /// <summary>
        /// Default locale used for localization fallback
        /// </summary>
        public static string DefaultLocale { get; set; } = "en_us";

        public static IEnumerable<ParsedExtension> ParseInstalledExtensions()
        {
            PyRevitConfig config = PyRevitConfig.Load();
            List<string> extensionRoots = GetExtensionRoots();
            extensionRoots.AddRange(config.UserExtensionsList);

            // TODO check if they are activated in the config
            // ParseExtensionByName

            foreach (var root in extensionRoots)
            {
                if (!Directory.Exists(root))
                    continue;

                // Parse .extension directories (UI extensions)
                foreach (var extDir in Directory.GetDirectories(root, "*.extension"))
                {
                    yield return ParseExtension(extDir);
                }

                // Parse .lib directories (Library extensions)
                foreach (var libDir in Directory.GetDirectories(root, "*.lib"))
                {
                    yield return ParseExtension(libDir);
                }
            }
        }

        /// <summary>
        /// Parses a specific extension from the given extension path
        /// </summary>
        /// <param name="extensionPath">The full path to the .extension or .lib directory</param>
        /// <returns>A single ParsedExtension if the path is valid and contains an extension, otherwise empty</returns>
        public static IEnumerable<ParsedExtension> ParseInstalledExtensions(string extensionPath)
        {
            if (string.IsNullOrWhiteSpace(extensionPath) || !Directory.Exists(extensionPath))
                yield break;

            // Ensure the directory has .extension or .lib suffix
            if (!extensionPath.EndsWith(".extension", StringComparison.OrdinalIgnoreCase) &&
                !extensionPath.EndsWith(".lib", StringComparison.OrdinalIgnoreCase))
                yield break;

            yield return ParseExtension(extensionPath);
        }

        /// <summary>
        /// Parses specific extensions from the given extension paths
        /// </summary>
        /// <param name="extensionPaths">The full paths to the .extension or .lib directories</param>
        /// <returns>ParsedExtensions for valid paths that contain extensions</returns>
        public static IEnumerable<ParsedExtension> ParseInstalledExtensions(IEnumerable<string> extensionPaths)
        {
            if (extensionPaths == null)
                yield break;

            foreach (var extensionPath in extensionPaths)
            {
                if (string.IsNullOrWhiteSpace(extensionPath) || !Directory.Exists(extensionPath))
                    continue;

                // Ensure the directory has .extension or .lib suffix
                if (!extensionPath.EndsWith(".extension", StringComparison.OrdinalIgnoreCase) &&
                    !extensionPath.EndsWith(".lib", StringComparison.OrdinalIgnoreCase))
                    continue;

                yield return ParseExtension(extensionPath);
            }
        }

        /// <summary>
        /// Parses a single extension from the given extension directory path
        /// </summary>
        /// <param name="extDir">The path to the .extension directory</param>
        /// <returns>A ParsedExtension object</returns>
        private static ParsedExtension ParseExtension(string extDir)
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
                LayoutItemTitles = parsedBundle?.LayoutItemTitles,
                Titles = parsedBundle?.Titles,
                Tooltips = parsedBundle?.Tooltips,
                MinRevitVersion = parsedBundle?.MinRevitVersion,
                Context = parsedBundle?.Context,
                Engine = parsedBundle?.Engine
            };

            ReorderByLayout(parsedExtension);

            return parsedExtension;
        }

        /// <summary>
        /// Recursively reorders the given component's Children in-place
        /// according to its own LayoutOrder.  If LayoutOrder is null or empty,
        /// we skip sorting here but still recurse into children.
        /// </summary>
        private static void ReorderByLayout(ParsedComponent component)
        {
            if (component?.Children == null)
                return;

            if (component.LayoutOrder != null && component.LayoutOrder.Count > 0)
            {
                // Build reordered list (first pass: add matching components)
                var reorderedChildren = new List<ParsedComponent>();
                
                foreach (var layoutItem in component.LayoutOrder)
                {
                    // Skip separator and slideout markers in first pass
                    if (layoutItem.Contains("---") || layoutItem.Contains(">>>"))
                        continue;
                    
                    // Find matching component by DisplayName
                    var matchingComponent = component.Children.Find(c => c?.DisplayName == layoutItem);
                    if (matchingComponent != null && !reorderedChildren.Contains(matchingComponent))
                    {
                        // Apply custom title if specified in LayoutItemTitles
                        if (component.LayoutItemTitles != null && 
                            component.LayoutItemTitles.ContainsKey(layoutItem))
                        {
                            matchingComponent.Title = component.LayoutItemTitles[layoutItem];
                        }
                        
                        reorderedChildren.Add(matchingComponent);
                    }
                }
                
                // Second pass: insert separators and slideouts at their positions
                for (int idx = 0; idx < component.LayoutOrder.Count; idx++)
                {
                    var layoutItem = component.LayoutOrder[idx];
                    var insertIndex = Math.Min(idx, reorderedChildren.Count);
                    
                    // Check if this is a separator or slideout marker
                    if (layoutItem.Contains("---") && idx < component.LayoutOrder.Count - 1)
                    {
                        // Create a separator component and insert at position
                        var separator = new ParsedComponent
                        {
                            Name = "---",
                            DisplayName = "---",
                            Type = CommandComponentType.Separator,
                            Directory = component.Directory
                        };
                        reorderedChildren.Insert(insertIndex, separator);
                    }
                    else if (layoutItem.Contains(">>>") && idx < component.LayoutOrder.Count - 1)
                    {
                        // Create a slideout marker component and insert at position
                        var slideout = new ParsedComponent
                        {
                            Name = ">>>",
                            DisplayName = ">>>",
                            Type = CommandComponentType.Separator,  // Slideout acts like a separator
                            HasSlideout = true,  // Mark it as a slideout marker
                            Directory = component.Directory
                        };
                        reorderedChildren.Insert(insertIndex, slideout);
                    }
                }
                
                // Add any components not in layout order at the end
                foreach (var child in component.Children)
                {
                    if (child != null && !reorderedChildren.Contains(child))
                    {
                        reorderedChildren.Add(child);
                    }
                }
                
                component.Children = reorderedChildren;
            }

            foreach (var child in component.Children)
            {
                if (child != null)
                {
                    ReorderByLayout(child);
                }
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
                    componentType == CommandComponentType.SmartButton ||
                    componentType == CommandComponentType.PullDown ||
                    componentType == CommandComponentType.SplitButton ||
                    componentType == CommandComponentType.SplitPushButton ||
                    componentType == CommandComponentType.InvokeButton))
                {
                    var yaml = Path.Combine(dir, "bundle.yaml");
                    if (File.Exists(yaml))
                        scriptPath = yaml;
                }

                var bundleFile = Path.Combine(dir, "bundle.yaml");
                var children = ParseComponents(dir, extensionName, fullPath);

                // First, get values from Python script
                string title = null, author = null, doc = null;
                if (scriptPath != null && scriptPath.EndsWith(".py", StringComparison.OrdinalIgnoreCase))
                {
                    (title, author, doc) = ReadPythonScriptConstants(scriptPath);
                }

                // Then parse bundle and override with bundle values if they exist
                var bundleInComponent = File.Exists(bundleFile) ? BundleYamlParser.Parse(bundleFile) : null;
                
                // Override script values with bundle values (bundle takes precedence)
                if (bundleInComponent != null)
                {
                    // Use default locale for initial title/tooltip assignment
                    var bundleTitle = GetLocalizedValue(bundleInComponent.Titles);
                    var bundleTooltip = GetLocalizedValue(bundleInComponent.Tooltips);
                    
                    if (!string.IsNullOrEmpty(bundleTitle))
                        title = bundleTitle;
                    
                    if (!string.IsNullOrEmpty(bundleTooltip))
                        doc = bundleTooltip;
                        
                    if (!string.IsNullOrEmpty(bundleInComponent.Author))
                        author = bundleInComponent.Author;
                }

                components.Add(new ParsedComponent
                {
                    Name = namePart,
                    DisplayName = displayName,
                    ScriptPath = scriptPath,
                    Tooltip = doc ?? "",
                    UniqueId = SanitizeClassName(fullPath.ToLowerInvariant()),
                    Type = componentType,
                    Children = children,
                    BundleFile = File.Exists(bundleFile) ? bundleFile : null,
                    LayoutOrder = bundleInComponent?.LayoutOrder,
                    LayoutItemTitles = bundleInComponent?.LayoutItemTitles,
                    Title = title,
                    Author = author,
                    Context = bundleInComponent?.Context,
                    Hyperlink = bundleInComponent?.Hyperlink,
                    Highlight = bundleInComponent?.Highlight,
                    PanelBackground = bundleInComponent?.PanelBackground,
                    TitleBackground = bundleInComponent?.TitleBackground,
                    SlideoutBackground = bundleInComponent?.SlideoutBackground,
                    Icons = ParseIconsForComponent(dir),
                    TargetAssembly = bundleInComponent?.Assembly,
                    CommandClass = bundleInComponent?.CommandClass,
                    AvailabilityClass = bundleInComponent?.AvailabilityClass,
                    LocalizedTitles = bundleInComponent?.Titles,
                    LocalizedTooltips = bundleInComponent?.Tooltips,
                    Directory = dir
                });
            }

            return components;
        }

        /// <summary>
        /// Gets a localized value from a dictionary, falling back to the default locale, then to the first available value
        /// </summary>
        private static string GetLocalizedValue(Dictionary<string, string> localizedValues, string preferredLocale = null)
        {
            if (localizedValues == null || localizedValues.Count == 0)
                return null;

            // Use default locale if no preferred locale specified
            if (string.IsNullOrEmpty(preferredLocale))
                preferredLocale = DefaultLocale;

            // Try preferred locale first
            if (localizedValues.TryGetValue(preferredLocale, out string preferredValue))
                return preferredValue;

            // Fallback to default locale if different preferred locale was specified
            if (preferredLocale != DefaultLocale && localizedValues.TryGetValue(DefaultLocale, out string defaultValue))
                return defaultValue;

            // Fallback to first available value
            return localizedValues.Values.FirstOrDefault();
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
                    doc = ExtractPythonConstantValue(line);
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
                // Process escape sequences (e.g., \n, \t, \\)
                value = System.Text.RegularExpressions.Regex.Unescape(value);
                return value;
            }
            return null;
        }

        /// <summary>
        /// Parses and discovers icon files for a component directory
        /// </summary>
        /// <param name="componentDirectory">The directory containing the component</param>
        /// <returns>A collection of discovered icons</returns>
        private static ComponentIconCollection ParseIconsForComponent(string componentDirectory)
        {
            var icons = new ComponentIconCollection();

            if (!Directory.Exists(componentDirectory))
                return icons;

            try
            {
                // Get all files in the component directory
                var files = Directory.GetFiles(componentDirectory, "*", SearchOption.TopDirectoryOnly);

                foreach (var file in files)
                {
                    var extension = Path.GetExtension(file);
                    var fileName = Path.GetFileName(file).ToLowerInvariant();

                    // Check if this is a supported image file
                    if (ComponentIconCollection.IsSupportedImageExtension(extension))
                    {
                        // Check if the filename suggests it's an icon
                        if (IsLikelyIconFile(fileName))
                        {
                            var icon = new ComponentIcon(file);
                            icons.Add(icon);
                        }
                    }
                }

                // Sort icons by priority (standard icons first, then by size)
                icons.Sort(CompareIconsByPriority);
            }
            catch (Exception ex)
            {
                // Log error if needed, but don't fail the parsing
                System.Diagnostics.Debug.WriteLine($"Error parsing icons for {componentDirectory}: {ex.Message}");
            }

            return icons;
        }

        /// <summary>
        /// Determines if a filename is likely to be an icon file based on naming conventions
        /// </summary>
        /// <param name="fileName">The filename to check (should be lowercase)</param>
        /// <returns>True if the file is likely an icon</returns>
        private static bool IsLikelyIconFile(string fileName)
        {
            // Common icon file patterns
            var iconPatterns = new[]
            {
                "icon",
                "button_icon",
                "cmd_icon",
                "command_icon"
            };

            // Check if filename starts with or contains icon-related terms
            foreach (var pattern in iconPatterns)
            {
                if (fileName.StartsWith(pattern) || fileName.Contains(pattern))
                    return true;
            }

            // Check for size-specific icons (e.g., icon_16.png, icon32.ico)
            if (fileName.Contains("icon") && (fileName.Contains("16") || fileName.Contains("32") || fileName.Contains("64")))
                return true;

            // Check for dark icons specifically (e.g., icon.dark.png, icon_dark.png)
            if (fileName.Contains("dark") && fileName.Contains("icon"))
                return true;

            // Check for common icon naming patterns
            if (fileName.StartsWith("ico_") || fileName.EndsWith("_ico"))
                return true;

            // For very short filenames that are just the image extension, consider them icons
            // (this covers cases like "16.png", "32.ico", etc.)
            var nameWithoutExtension = Path.GetFileNameWithoutExtension(fileName);
            if (nameWithoutExtension.Length <= 3 && nameWithoutExtension.All(char.IsDigit))
                return true;

            return false;
        }

        /// <summary>
        /// Compares icons for sorting by priority
        /// </summary>
        /// <param name="icon1">First icon to compare</param>
        /// <param name="icon2">Second icon to compare</param>
        /// <returns>Comparison result for sorting</returns>
        private static int CompareIconsByPriority(ComponentIcon icon1, ComponentIcon icon2)
        {
            // Priority order: Standard > Size32 > Size16 > Size64 > Large > Small > Others
            // Dark variants have slightly lower priority than their light counterparts
            var priority1 = GetIconTypePriority(icon1.Type);
            var priority2 = GetIconTypePriority(icon2.Type);

            if (priority1 != priority2)
                return priority1.CompareTo(priority2);

            // If same priority, prefer smaller file names (shorter names usually indicate primary icons)
            return icon1.FileName.Length.CompareTo(icon2.FileName.Length);
        }

        /// <summary>
        /// Gets the priority value for an icon type (lower values = higher priority)
        /// </summary>
        /// <param name="iconType">The icon type</param>
        /// <returns>Priority value</returns>
        private static int GetIconTypePriority(IconType iconType)
        {
            switch (iconType)
            {
                case IconType.Standard:
                    return 1;
                case IconType.DarkStandard:
                    return 2;
                case IconType.Size32:
                    return 3;
                case IconType.DarkSize32:
                    return 4;
                case IconType.Size16:
                    return 5;
                case IconType.DarkSize16:
                    return 6;
                case IconType.Size64:
                    return 7;
                case IconType.DarkSize64:
                    return 8;
                case IconType.Large:
                    return 9;
                case IconType.DarkLarge:
                    return 10;
                case IconType.Small:
                    return 11;
                case IconType.DarkSmall:
                    return 12;
                case IconType.Button:
                    return 13;
                case IconType.DarkButton:
                    return 14;
                case IconType.Command:
                    return 15;
                case IconType.DarkCommand:
                    return 16;
                case IconType.Other:
                    return 17;
                case IconType.DarkOther:
                    return 18;
                default:
                    return 19;
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
            NoButton,
            Separator
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
    }
}
