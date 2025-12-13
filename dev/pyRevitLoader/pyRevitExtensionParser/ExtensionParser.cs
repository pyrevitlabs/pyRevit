using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;

namespace pyRevitExtensionParser
{
    public static class ExtensionParser
    {
        /// <summary>
        /// Default locale used for localization fallback
        /// </summary>
        public static string DefaultLocale { get; set; } = "en_us";
        
        // Cache file existence checks to avoid repeated file system calls
        private static Dictionary<string, bool> _fileExistsCache = new Dictionary<string, bool>();
        
        // Cache directory file listings to avoid repeated Directory.GetFiles calls
        private static Dictionary<string, string[]> _directoryFilesCache = new Dictionary<string, string[]>();
        
        // Cache icon parsing results per component directory
        private static Dictionary<string, ComponentIconCollection> _iconCache = new Dictionary<string, ComponentIconCollection>();
        
        private static bool FileExists(string path)
        {
            if (string.IsNullOrEmpty(path))
                return false;
                
            if (!_fileExistsCache.TryGetValue(path, out bool exists))
            {
                exists = File.Exists(path);
                _fileExistsCache[path] = exists;
            }
            return exists;
        }
        
        private static string[] GetFilesInDirectory(string directory, string searchPattern = "*", SearchOption searchOption = SearchOption.TopDirectoryOnly)
        {
            if (string.IsNullOrEmpty(directory) || !Directory.Exists(directory))
                return Array.Empty<string>();
                
            var cacheKey = $"{directory}|{searchPattern}|{searchOption}";
            if (!_directoryFilesCache.TryGetValue(cacheKey, out string[] files))
            {
                files = Directory.GetFiles(directory, searchPattern, searchOption);
                _directoryFilesCache[cacheKey] = files;
            }
            return files;
        }

        // Cache extension roots to avoid repeated directory traversal and config reading
        private static List<string> _cachedExtensionRoots;
        
        private static List<string> GetCachedExtensionRoots()
        {
            if (_cachedExtensionRoots == null)
            {
                var config = GetConfig();
                _cachedExtensionRoots = GetExtensionRoots();
                _cachedExtensionRoots.AddRange(config.UserExtensionsList);
            }
            return _cachedExtensionRoots;
        }

        public static IEnumerable<ParsedExtension> ParseInstalledExtensions()
        {
            var extensionRoots = GetCachedExtensionRoots();

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

        // Cache config instance to avoid reloading for each extension
        private static PyRevitConfig _cachedConfig;
        private static PyRevitConfig GetConfig()
        {
            if (_cachedConfig == null)
                _cachedConfig = PyRevitConfig.Load();
            return _cachedConfig;
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
            ParsedBundle parsedBundle = FileExists(bundlePath)
                ? BundleParser.BundleYamlParser.Parse(bundlePath)
                : null;

            // Read extension config from pyRevit config file (cached)
            var config = GetConfig();
            var extConfig = config.ParseExtensionByName(extName);

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
                Engine = parsedBundle?.Engine,
                Config = extConfig
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

            if (FileExists(configPath))
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
                    if (FileExists(yaml))
                        scriptPath = yaml;
                }

                if (scriptPath == null)
                {
                    // Look for script files in order of preference: .py, .cs, .vb, .rb, .dyn, .gh, .ghx, .rfa
                    // Use cached file listing instead of EnumerateFiles
                    var dirFiles = GetFilesInDirectory(dir, "script.*", SearchOption.TopDirectoryOnly);
                    
                    // Check for scripts in priority order
                    var scriptExtensions = new[] { ".py", ".cs", ".vb", ".rb", ".dyn", ".gh", ".ghx", ".rfa" };
                    foreach (var scriptExt in scriptExtensions)
                    {
                        var scriptFile = $"script{scriptExt}";
                        scriptPath = dirFiles.FirstOrDefault(f => 
                            f.EndsWith(scriptFile, StringComparison.OrdinalIgnoreCase));
                        if (scriptPath != null)
                            break;
                    }
                    
                    // If no script.* file found, look for any file with the target extensions
                    // This handles cases like BIM1_ArrowHeadSwitcher_script.dyn
                    if (scriptPath == null)
                    {
                        var allFiles = GetFilesInDirectory(dir, "*", SearchOption.TopDirectoryOnly);
                        foreach (var scriptExt in scriptExtensions)
                        {
                            // Look for any file ending with _script{ext} or just {ext}
                            scriptPath = allFiles.FirstOrDefault(f => 
                                (f.EndsWith($"_script{scriptExt}", StringComparison.OrdinalIgnoreCase) ||
                                 (f.EndsWith(scriptExt, StringComparison.OrdinalIgnoreCase) && 
                                  !f.EndsWith($"_config{scriptExt}", StringComparison.OrdinalIgnoreCase))));
                            if (scriptPath != null)
                                break;
                        }
                    }
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
                    if (FileExists(yaml))
                        scriptPath = yaml;
                }

                var bundleFile = Path.Combine(dir, "bundle.yaml");
                var children = ParseComponents(dir, extensionName, fullPath);

                // First, get values from Python script
                string title = null, author = null, doc = null;
                Dictionary<string, string> scriptLocalizedTitles = null;
                Dictionary<string, string> scriptLocalizedTooltips = null;
                
                if (scriptPath != null && scriptPath.EndsWith(".py", StringComparison.OrdinalIgnoreCase))
                {
                    (title, scriptLocalizedTitles, author, doc, scriptLocalizedTooltips) = ReadPythonScriptConstants(scriptPath);
                }

                // Then parse bundle and override with bundle values if they exist
                var bundleInComponent = FileExists(bundleFile) ? BundleParser.BundleYamlParser.Parse(bundleFile) : null;
                
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

                // Merge localized values: bundle takes precedence over script
                var finalLocalizedTitles = scriptLocalizedTitles ?? new Dictionary<string, string>();
                var finalLocalizedTooltips = scriptLocalizedTooltips ?? new Dictionary<string, string>();
                
                // If bundle has localized values, they override script values
                if (bundleInComponent?.Titles != null)
                {
                    foreach (var kvp in bundleInComponent.Titles)
                    {
                        finalLocalizedTitles[kvp.Key] = kvp.Value;
                    }
                }
                
                if (bundleInComponent?.Tooltips != null)
                {
                    foreach (var kvp in bundleInComponent.Tooltips)
                    {
                        finalLocalizedTooltips[kvp.Key] = kvp.Value;
                    }
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
                    BundleFile = FileExists(bundleFile) ? bundleFile : null,
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
                    Modules = bundleInComponent?.Modules ?? new List<string>(),
                    LocalizedTitles = finalLocalizedTitles.Count > 0 ? finalLocalizedTitles : null,
                    LocalizedTooltips = finalLocalizedTooltips.Count > 0 ? finalLocalizedTooltips : null,
                    Directory = dir,
                    Engine = bundleInComponent?.Engine
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

        // Cache Python script constant parsing to avoid re-reading files
        private static Dictionary<string, (string title, Dictionary<string, string> localizedTitles, string author, string doc, Dictionary<string, string> localizedTooltips)> _pythonScriptCache = 
            new Dictionary<string, (string title, Dictionary<string, string> localizedTitles, string author, string doc, Dictionary<string, string> localizedTooltips)>();

        private static (string title, Dictionary<string, string> localizedTitles, string author, string doc, Dictionary<string, string> localizedTooltips) ReadPythonScriptConstants(string scriptPath)
        {
            // Check cache first
            if (_pythonScriptCache.TryGetValue(scriptPath, out var cached))
                return cached;
                
            string title = null, author = null, doc = null;
            Dictionary<string, string> localizedTitles = null;
            Dictionary<string, string> localizedTooltips = null;

            foreach (var line in File.ReadLines(scriptPath))
            {
                if (line.StartsWith("__title__"))
                {
                    // Check if it's a dictionary
                    var dictValue = ExtractPythonDictionary(line);
                    if (dictValue != null)
                    {
                        localizedTitles = dictValue;
                        // Get default locale value for backward compatibility
                        title = GetLocalizedValue(localizedTitles);
                    }
                    else
                    {
                        title = ExtractPythonConstantValue(line);
                    }
                }
                else if (line.StartsWith("__author__"))
                {
                    author = ExtractPythonConstantValue(line);
                }
                else if (line.StartsWith("__doc__"))
                {
                    // Check if it's a dictionary for multi-language tooltip
                    var dictValue = ExtractPythonDictionary(line);
                    if (dictValue != null)
                    {
                        localizedTooltips = dictValue;
                        // Get default locale value for backward compatibility
                        doc = GetLocalizedValue(localizedTooltips);
                    }
                    else
                    {
                        doc = ExtractPythonConstantValue(line);
                    }
                }
            }

            var result = (title, localizedTitles, author, doc, localizedTooltips);
            _pythonScriptCache[scriptPath] = result;
            return result;
        }

        private static string ExtractPythonConstantValue(string line)
        {
            var parts = line.Split(new[] { '=' }, 2, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length == 2)
            {
                var value = parts[1].Trim().Trim('\'', '"');
                // Process Python escape sequences to match runtime behavior
                return ProcessPythonEscapeSequences(value);
            }
            return null;
        }

        private static string ProcessPythonEscapeSequences(string value)
        {
            if (string.IsNullOrEmpty(value))
                return value;

            var result = new StringBuilder();
            for (int i = 0; i < value.Length; i++)
            {
                if (value[i] == '\\' && i + 1 < value.Length)
                {
                    // Process Python escape sequences
                    switch (value[i + 1])
                    {
                        case 'n':
                            result.Append('\n');
                            i++; // Skip next character
                            break;
                        case 't':
                            result.Append('\t');
                            i++;
                            break;
                        case 'r':
                            result.Append('\r');
                            i++;
                            break;
                        case '\\':
                            result.Append('\\');
                            i++;
                            break;
                        case '\'':
                            result.Append('\'');
                            i++;
                            break;
                        case '"':
                            result.Append('"');
                            i++;
                            break;
                        default:
                            // For unrecognized escape sequences, keep the backslash
                            // This handles cases like paths (e.g., "C:\path")
                            result.Append(value[i]);
                            break;
                    }
                }
                else
                {
                    result.Append(value[i]);
                }
            }
            return result.ToString();
        }

        private static Dictionary<string, string> ExtractPythonDictionary(string line)
        {
            var parts = line.Split(new[] { '=' }, 2, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length == 2)
            {
                var value = parts[1].Trim();
                // Check if it's a dictionary literal
                if (value.StartsWith("{") && value.EndsWith("}"))
                {
                    var dict = new Dictionary<string, string>();
                    // Remove outer braces
                    value = value.Substring(1, value.Length - 2);
                    
                    // Split by comma, but handle commas within quoted strings
                    var items = new List<string>();
                    var currentItem = "";
                    var inQuote = false;
                    var quoteChar = '\0';
                    
                    for (int i = 0; i < value.Length; i++)
                    {
                        var ch = value[i];
                        
                        if (!inQuote && (ch == '"' || ch == '\''))
                        {
                            inQuote = true;
                            quoteChar = ch;
                            currentItem += ch;
                        }
                        else if (inQuote && ch == quoteChar && (i == 0 || value[i - 1] != '\\'))
                        {
                            inQuote = false;
                            quoteChar = '\0';
                            currentItem += ch;
                        }
                        else if (!inQuote && ch == ',')
                        {
                            if (!string.IsNullOrWhiteSpace(currentItem))
                                items.Add(currentItem.Trim());
                            currentItem = "";
                        }
                        else
                        {
                            currentItem += ch;
                        }
                    }
                    
                    if (!string.IsNullOrWhiteSpace(currentItem))
                        items.Add(currentItem.Trim());
                    
                    // Parse each key-value pair
                    foreach (var item in items)
                    {
                        var colonIndex = item.IndexOf(':');
                        if (colonIndex > 0)
                        {
                            var key = item.Substring(0, colonIndex).Trim().Trim('\'', '"');
                            var val = item.Substring(colonIndex + 1).Trim().Trim('\'', '"');
                            // Don't process escape sequences - Python already handles them when the script is parsed
                            dict[key] = val;
                        }
                    }
                    
                    return dict.Count > 0 ? dict : null;
                }
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
            // Check cache first
            if (_iconCache.TryGetValue(componentDirectory, out var cached))
                return cached;
                
            var icons = new ComponentIconCollection();

            if (!Directory.Exists(componentDirectory))
            {
                _iconCache[componentDirectory] = icons;
                return icons;
            }

            try
            {
                // Get all files in the component directory (cached)
                var files = GetFilesInDirectory(componentDirectory, "*", SearchOption.TopDirectoryOnly);

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

            // Cache the result
            _iconCache[componentDirectory] = icons;
            
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
