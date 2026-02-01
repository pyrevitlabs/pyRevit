using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using pyRevitLabs.Json.Linq;
using pyRevitLabs.NLog;

namespace pyRevitExtensionParser
{
    public static class ExtensionParser
    {
        /// <summary>
        /// Default locale used for localization fallback
        /// </summary>
        public static string DefaultLocale { get; set; } = "en_us";

        private static readonly Logger logger = LogManager.GetCurrentClassLogger();
        
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
        
        /// <summary>
        /// Flag to track if locale has been initialized from config
        /// </summary>
        private static bool _localeInitialized = false;
        
        /// <summary>
        /// Cached locale value for cache invalidation when locale changes
        /// </summary>
        private static string _cachedLocale = null;
        
        /// <summary>
        /// Clears all static caches to force re-parsing of extensions.
        /// This should be called before reloading pyRevit to ensure newly installed
        /// or enabled extensions are discovered.
        /// </summary>
        public static void ClearAllCaches()
        {
            _fileExistsCache.Clear();
            _directoryFilesCache.Clear();
            _iconCache.Clear();
            _cachedExtensionRoots = null;
            _cachedConfig = null;
            _pythonScriptCache.Clear();
            _localeInitialized = false;
            
            // Also clear the BundleParser cache
            BundleParser.BundleYamlParser.ClearCache();
        }
        
        /// <summary>
        /// Initializes the DefaultLocale from user configuration if not already set.
        /// Should be called before parsing extensions to ensure locale-aware localization.
        /// If locale has changed since last initialization, all caches are cleared.
        /// </summary>
        private static void InitializeLocaleFromConfig()
        {
            var config = GetConfig();
            var userLocale = config.UserLocale;
            
            // Check if locale has changed since last initialization
            // If locale changed, we need to invalidate all caches to force re-parsing
            if (_localeInitialized && userLocale != _cachedLocale)
            {
                logger.Debug("Locale changed from '{0}' to '{1}'. Clearing caches...", _cachedLocale, userLocale);
                ClearAllCaches();
            }
            
            if (!string.IsNullOrEmpty(userLocale))
            {
                DefaultLocale = userLocale;
            }
            _cachedLocale = userLocale;
            _localeInitialized = true;
        }
        
        private static List<string> GetCachedExtensionRoots()
        {
            if (_cachedExtensionRoots == null)
            {
                // Initialize locale from config before parsing
                InitializeLocaleFromConfig();
                // GetExtensionRoots already reads userextensions from config file,
                // so we don't need to add UserExtensionsList again (which would cause duplicates)
                _cachedExtensionRoots = GetExtensionRoots();
            }
            return _cachedExtensionRoots;
        }

        public static IEnumerable<ParsedExtension> ParseInstalledExtensions()
        {
            var extensionRoots = GetCachedExtensionRoots();

            // Track discovered extension directories to avoid duplicates
            // This can happen when the same extension is in multiple roots or
            // when userextensions paths overlap with default paths
            var discoveredExtensions = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            foreach (var root in extensionRoots)
            {
                if (!Directory.Exists(root))
                    continue;

                // Parse .extension directories (UI extensions)
                foreach (var extDir in Directory.GetDirectories(root, "*.extension"))
                {
                    // Use full path for deduplication
                    var fullPath = Path.GetFullPath(extDir);
                    if (discoveredExtensions.Add(fullPath))
                    {
                        yield return ParseExtension(extDir);
                    }
                }

                // Parse .lib directories (Library extensions)
                foreach (var libDir in Directory.GetDirectories(root, "*.lib"))
                {
                    var fullPath = Path.GetFullPath(libDir);
                    if (discoveredExtensions.Add(fullPath))
                    {
                        yield return ParseExtension(libDir);
                    }
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
            
            var bundlePath = Path.Combine(extDir, "bundle.yaml");
            ParsedBundle parsedBundle = FileExists(bundlePath)
                ? BundleParser.BundleYamlParser.Parse(bundlePath)
                : null;

            // Pass extension-level templates to child components
            // Include author as a template if it exists
            var extensionTemplates = parsedBundle?.Templates != null 
                ? new Dictionary<string, string>(parsedBundle.Templates)
                : new Dictionary<string, string>();
            
            // If extension has an author, add it as a template for children to inherit
            if (!string.IsNullOrEmpty(parsedBundle?.Author))
            {
                extensionTemplates["author"] = parsedBundle.Author;
            }
            
            // Read extension.json for additional templates
            var extensionJsonPath = Path.Combine(extDir, "extension.json");
            if (FileExists(extensionJsonPath))
            {
                try
                {
                    var jsonContent = File.ReadAllText(extensionJsonPath);
                    var json = JObject.Parse(jsonContent);
                    
                    // Read templates section if present
                    var templates = json["templates"] as JObject;
                    if (templates != null)
                    {
                        foreach (var prop in templates.Properties())
                        {
                            // extension.json templates override bundle.yaml templates
                            extensionTemplates[prop.Name] = prop.Value.ToString();
                        }
                    }
                    
                    // Also read top-level author if templates.author doesn't exist
                    if (!extensionTemplates.ContainsKey("author"))
                    {
                        var author = json["author"]?.ToString();
                        if (!string.IsNullOrEmpty(author))
                        {
                            extensionTemplates["author"] = author;
                        }
                    }
                }
                catch
                {
                    // If JSON parsing fails, continue without extension.json templates
                }
            }
            
            var children = ParseComponents(extDir, extName, null, extensionTemplates.Count > 0 ? extensionTemplates : null);

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
                MaxRevitVersion = parsedBundle?.MaxRevitVersion,
                Context = parsedBundle?.GetFormattedContext(),
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

            // Add third-party extensions default directory (%APPDATA%\pyRevit\Extensions)
            var thirdPartyExtensionsPath = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                "pyRevit",
                "Extensions");
            
            if (Directory.Exists(thirdPartyExtensionsPath))
            {
                roots.Add(thirdPartyExtensionsPath);
            }

            var userExtensions = GetConfig().UserExtensionsList;
            foreach (var extPath in userExtensions)
            {
                if (string.IsNullOrWhiteSpace(extPath))
                {
                    logger.Debug("Skipping empty userextensions path");
                    continue;
                }

                try
                {
                    var normalizedPath = Path.GetFullPath(extPath);
                    if (Directory.Exists(normalizedPath))
                        roots.Add(normalizedPath);
                    else
                        logger.Debug("Skipping non-existent userextensions path: {0}", normalizedPath);
                }
                catch (ArgumentException ex)
                {
                    logger.Debug("Skipping invalid userextensions path '{0}': {1}", extPath, ex.Message);
                }
                catch (PathTooLongException ex)
                {
                    logger.Debug("Skipping too long userextensions path '{0}': {1}", extPath, ex.Message);
                }
                catch (NotSupportedException ex)
                {
                    logger.Debug("Skipping unsupported userextensions path '{0}': {1}", extPath, ex.Message);
                }
            }

            return roots;
        }

        /// <summary>
        /// Substitutes liquid template tags ({{variable}}) in a string with values from the templates dictionary.
        /// </summary>
        /// <param name="input">The input string containing template tags.</param>
        /// <param name="templates">Dictionary of template variable names and their values.</param>
        /// <returns>The string with all template tags substituted.</returns>
        private static string SubstituteTemplates(string input, Dictionary<string, string> templates)
        {
            if (string.IsNullOrEmpty(input) || templates == null || templates.Count == 0)
                return input;

            var result = input;
            foreach (var kvp in templates)
            {
                var tag = "{{" + kvp.Key + "}}";
                if (result.Contains(tag))
                {
                    result = result.Replace(tag, kvp.Value);
                }
            }
            return result;
        }

        /// <summary>
        /// Substitutes liquid template tags in a dictionary of localized values.
        /// </summary>
        private static Dictionary<string, string> SubstituteTemplatesInDict(
            Dictionary<string, string> localizedValues, 
            Dictionary<string, string> templates)
        {
            if (localizedValues == null || templates == null || templates.Count == 0)
                return localizedValues;

            var result = new Dictionary<string, string>();
            foreach (var kvp in localizedValues)
            {
                result[kvp.Key] = SubstituteTemplates(kvp.Value, templates);
            }
            return result;
        }

        private static List<ParsedComponent> ParseComponents(
            string baseDir,
            string extensionName,
            string parentPath = null,
            Dictionary<string, string> inheritedTemplates = null)
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

                // Look for config script (config.py, config.cs, etc.)
                string configScriptPath = null;
                var configExtensions = new[] { ".py", ".cs", ".vb", ".rb", ".dyn", ".gh", ".ghx" };
                var allDirFiles = GetFilesInDirectory(dir, "*", SearchOption.TopDirectoryOnly);
                foreach (var configExt in configExtensions)
                {
                    var configFile = $"config{configExt}";
                    configScriptPath = allDirFiles.FirstOrDefault(f => 
                        Path.GetFileName(f).Equals(configFile, StringComparison.OrdinalIgnoreCase));
                    if (configScriptPath != null)
                        break;
                }
                // If no separate config script found, use the main script path
                if (configScriptPath == null)
                    configScriptPath = scriptPath;

                // Handle .content bundles - special logic for Revit family (.rfa) files
                // Content bundles load RFA files, with scriptPath being the primary content
                // and configScriptPath being the alternative content (CTRL+Click)
                if (componentType == CommandComponentType.ContentButton)
                {
                    var bundleYaml = Path.Combine(dir, "bundle.yaml");
                    var tempBundle = FileExists(bundleYaml) ? BundleParser.BundleYamlParser.Parse(bundleYaml) : null;
                    
                    // Try to get content from bundle.yaml metadata first
                    if (tempBundle != null && !string.IsNullOrEmpty(tempBundle.Content))
                    {
                        scriptPath = ResolveContentPath(dir, tempBundle.Content);
                    }
                    
                    // If no content in metadata, use naming convention
                    if (scriptPath == null)
                    {
                        // Look for version-specific content first: content_{version}.rfa
                        var versionedContent = GetFilesInDirectory(dir, "content_*.rfa", SearchOption.TopDirectoryOnly)
                            .FirstOrDefault();
                        if (versionedContent != null)
                        {
                            scriptPath = versionedContent;
                        }
                        else
                        {
                            // Look for default content.rfa
                            var defaultContent = Path.Combine(dir, "content.rfa");
                            if (FileExists(defaultContent))
                            {
                                scriptPath = defaultContent;
                            }
                            else
                            {
                                // Look for any .rfa file in the directory
                                var anyRfa = GetFilesInDirectory(dir, "*.rfa", SearchOption.TopDirectoryOnly)
                                    .FirstOrDefault();
                                if (anyRfa != null)
                                {
                                    scriptPath = anyRfa;
                                }
                            }
                        }
                    }
                    
                    // Handle alternative content (CTRL+Click)
                    if (tempBundle != null && !string.IsNullOrEmpty(tempBundle.ContentAlt))
                    {
                        configScriptPath = ResolveContentPath(dir, tempBundle.ContentAlt);
                    }
                    else
                    {
                        // Look for version-specific alternative content: other_{version}.rfa
                        var versionedAltContent = GetFilesInDirectory(dir, "other_*.rfa", SearchOption.TopDirectoryOnly)
                            .FirstOrDefault();
                        if (versionedAltContent != null)
                        {
                            configScriptPath = versionedAltContent;
                        }
                        else
                        {
                            // Look for default other.rfa
                            var defaultAltContent = Path.Combine(dir, "other.rfa");
                            if (FileExists(defaultAltContent))
                            {
                                configScriptPath = defaultAltContent;
                            }
                            else
                            {
                                // Fall back to main content path
                                configScriptPath = scriptPath;
                            }
                        }
                    }
                }
                
                // Look for on/off icons for smartbuttons and toggle buttons
                string onIconPath = null, onIconDarkPath = null, offIconPath = null, offIconDarkPath = null;
                if (componentType == CommandComponentType.SmartButton || 
                    componentType == CommandComponentType.PushButton)
                {
                    // Parse on/off icons with theme support
                    (onIconPath, onIconDarkPath, offIconPath, offIconDarkPath) = ParseToggleIcons(dir);
                }

                // Look for tooltip media file (tooltip.mp4, tooltip.swf, tooltip.png)
                var mediaFile = FindMediaFile(dir);

                var bundleFile = Path.Combine(dir, "bundle.yaml");
                
                // Then parse bundle and override with bundle values if they exist
                var bundleInComponent = FileExists(bundleFile) ? BundleParser.BundleYamlParser.Parse(bundleFile) : null;

                // Merge templates: inherited templates + current bundle templates
                // Current bundle templates override inherited ones
                var mergedTemplates = new Dictionary<string, string>();
                if (inheritedTemplates != null)
                {
                    foreach (var kvp in inheritedTemplates)
                    {
                        mergedTemplates[kvp.Key] = kvp.Value;
                    }
                }
                if (bundleInComponent?.Templates != null)
                {
                    foreach (var kvp in bundleInComponent.Templates)
                    {
                        mergedTemplates[kvp.Key] = kvp.Value;
                    }
                }

                // Get author from bundle to add to templates for child components
                // This allows children to use {{author}} to inherit from parent
                string bundleAuthor = bundleInComponent?.Author;
                if (!string.IsNullOrEmpty(bundleAuthor) && !bundleAuthor.Contains("{{"))
                {
                    // Only add if it's a concrete value, not a template reference itself
                    mergedTemplates["author"] = bundleAuthor;
                }

                // Pass merged templates to child components
                var children = ParseComponents(dir, extensionName, fullPath, mergedTemplates);

                // First, get values from Python script
                string title = null, author = null, doc = null;
                string scriptContext = null, scriptHelpUrl = null, scriptHighlight = null;
                string scriptMinRevitVersion = null, scriptMaxRevitVersion = null;
                bool scriptIsBeta = false, scriptCleanEngine = false, scriptFullFrameEngine = false, scriptPersistentEngine = false;
                Dictionary<string, string> scriptLocalizedTitles = null;
                Dictionary<string, string> scriptLocalizedTooltips = null;
                Dictionary<string, string> scriptLocalizedHelpUrls = null;
                
                if (scriptPath != null && scriptPath.EndsWith(".py", StringComparison.OrdinalIgnoreCase))
                {
                    var scriptConstants = ReadPythonScriptConstants(scriptPath);
                    title = scriptConstants.Title;
                    scriptLocalizedTitles = scriptConstants.LocalizedTitles;
                    author = scriptConstants.Author;
                    doc = scriptConstants.Doc;
                    scriptLocalizedTooltips = scriptConstants.LocalizedTooltips;
                    scriptContext = scriptConstants.Context;
                    scriptHelpUrl = scriptConstants.HelpUrl;
                    scriptLocalizedHelpUrls = scriptConstants.LocalizedHelpUrls;
                    scriptHighlight = scriptConstants.Highlight;
                    scriptMinRevitVersion = scriptConstants.MinRevitVersion;
                    scriptMaxRevitVersion = scriptConstants.MaxRevitVersion;
                    scriptIsBeta = scriptConstants.IsBeta;
                    scriptCleanEngine = scriptConstants.CleanEngine;
                    scriptFullFrameEngine = scriptConstants.FullFrameEngine;
                    scriptPersistentEngine = scriptConstants.PersistentEngine;
                }

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
                var finalLocalizedHelpUrls = scriptLocalizedHelpUrls ?? new Dictionary<string, string>();
                
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
                
                if (bundleInComponent?.HelpUrls != null)
                {
                    foreach (var kvp in bundleInComponent.HelpUrls)
                    {
                        finalLocalizedHelpUrls[kvp.Key] = kvp.Value;
                    }
                }

                // Apply template substitution to string values
                title = SubstituteTemplates(title, mergedTemplates);
                doc = SubstituteTemplates(doc, mergedTemplates);
                author = SubstituteTemplates(author, mergedTemplates);
                var hyperlink = SubstituteTemplates(bundleInComponent?.Hyperlink, mergedTemplates);
                scriptHelpUrl = SubstituteTemplates(scriptHelpUrl, mergedTemplates);
                
                // Apply template substitution to localized values
                finalLocalizedTitles = SubstituteTemplatesInDict(finalLocalizedTitles, mergedTemplates);
                finalLocalizedTooltips = SubstituteTemplatesInDict(finalLocalizedTooltips, mergedTemplates);
                finalLocalizedHelpUrls = SubstituteTemplatesInDict(finalLocalizedHelpUrls, mergedTemplates);

                // Determine final context: bundle takes precedence over script
                // bundleInComponent?.GetFormattedContext() returns "(zero-doc)" when no context in bundle
                // so we need to check if there's actually a context defined in the bundle
                string finalContext;
                var bundleContext = bundleInComponent?.GetFormattedContext();
                if (bundleInComponent != null && 
                    (bundleInComponent.ContextItems?.Count > 0 || 
                     bundleInComponent.ContextRules?.Count > 0 ||
                     !string.IsNullOrEmpty(bundleInComponent.Context)))
                {
                    // Bundle has explicit context defined
                    finalContext = bundleContext;
                }
                else if (!string.IsNullOrEmpty(scriptContext))
                {
                    // Use script context
                    finalContext = scriptContext;
                }
                else
                {
                    // No context defined - button will always be available (no availability class)
                    finalContext = null;
                }

                // Determine final highlight: bundle takes precedence over script
                string finalHighlight = !string.IsNullOrEmpty(bundleInComponent?.Highlight) 
                    ? bundleInComponent.Highlight 
                    : scriptHighlight;

                // Determine final help URL: bundle helpurl takes precedence over script helpurl
                string finalHelpUrl = !string.IsNullOrEmpty(bundleInComponent?.HelpUrl)
                    ? bundleInComponent.HelpUrl
                    : scriptHelpUrl;

                // Determine final help URL: bundle hyperlink takes precedence over script helpurl
                string finalHyperlink = !string.IsNullOrEmpty(hyperlink) ? hyperlink : scriptHelpUrl;

                // Determine final min Revit version: bundle takes precedence over script
                string finalMinRevitVersion = !string.IsNullOrEmpty(bundleInComponent?.MinRevitVersion)
                    ? bundleInComponent.MinRevitVersion
                    : scriptMinRevitVersion;

                // Determine final max Revit version: bundle takes precedence over script
                string finalMaxRevitVersion = !string.IsNullOrEmpty(bundleInComponent?.MaxRevitVersion)
                    ? bundleInComponent.MaxRevitVersion
                    : scriptMaxRevitVersion;

                // Determine final beta status: bundle takes precedence over script
                bool finalIsBeta = bundleInComponent != null && bundleInComponent.IsBeta 
                    ? bundleInComponent.IsBeta 
                    : scriptIsBeta;

                // Determine final engine config: bundle takes precedence, but script can add flags
                var finalEngine = bundleInComponent?.Engine ?? new EngineConfig();
                if (scriptCleanEngine) finalEngine.Clean = true;
                if (scriptFullFrameEngine) finalEngine.FullFrame = true;
                if (scriptPersistentEngine) finalEngine.Persistent = true;

                components.Add(new ParsedComponent
                {
                    Name = namePart,
                    DisplayName = displayName,
                    ScriptPath = scriptPath,
                    ConfigScriptPath = configScriptPath,
                    Tooltip = doc ?? "",
                    UniqueId = SanitizeClassName(fullPath.ToLowerInvariant()),
                    Type = componentType,
                    Children = children,
                    BundleFile = FileExists(bundleFile) ? bundleFile : null,
                    LayoutOrder = bundleInComponent?.LayoutOrder,
                    LayoutItemTitles = bundleInComponent?.LayoutItemTitles,
                    Title = title,
                    Author = author,
                    Context = finalContext,
                    Hyperlink = finalHyperlink,
                    HelpUrl = finalHelpUrl,
                    Highlight = finalHighlight,
                    MinRevitVersion = finalMinRevitVersion,
                    MaxRevitVersion = finalMaxRevitVersion,
                    IsBeta = finalIsBeta,
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
                    LocalizedHelpUrls = finalLocalizedHelpUrls.Count > 0 ? finalLocalizedHelpUrls : null,
                    Directory = dir,
                    Engine = finalEngine,
                    Members = bundleInComponent?.Members ?? new List<ComboBoxMember>(),
                    OnIconPath = onIconPath,
                    OnIconDarkPath = onIconDarkPath,
                    OffIconPath = offIconPath,
                    OffIconDarkPath = offIconDarkPath,
                    MediaFile = mediaFile
                });
            }

            return components;
        }

        /// <summary>
        /// Gets a localized value from a dictionary, falling back to the default locale, then to the first available value.
        /// This is the public API for getting localized values.
        /// </summary>
        /// <param name="localizedValues">Dictionary of locale codes to values.</param>
        /// <param name="preferredLocale">Optional preferred locale to use. If null, uses DefaultLocale.</param>
        /// <returns>The localized value or null if not found.</returns>
        public static string GetLocalizedString(Dictionary<string, string> localizedValues, string preferredLocale = null)
        {
            return GetLocalizedValue(localizedValues, preferredLocale);
        }

        /// <summary>
        /// Gets the localized title for a component, with fallback to DisplayName.
        /// </summary>
        /// <param name="component">The component to get the title for.</param>
        /// <returns>The localized title or DisplayName.</returns>
        public static string GetComponentTitle(ParsedComponent component)
        {
            if (component == null)
                return string.Empty;
                
            // First try localized titles
            if (component.LocalizedTitles != null && component.LocalizedTitles.Count > 0)
            {
                var localizedTitle = GetLocalizedValue(component.LocalizedTitles);
                if (!string.IsNullOrEmpty(localizedTitle))
                    return localizedTitle;
            }
            
            // Fall back to pre-resolved Title or DisplayName
            return !string.IsNullOrEmpty(component.Title) ? component.Title : component.DisplayName;
        }

        /// <summary>
        /// Gets the localized tooltip for a component.
        /// </summary>
        /// <param name="component">The component to get the tooltip for.</param>
        /// <returns>The localized tooltip or empty string.</returns>
        public static string GetComponentTooltip(ParsedComponent component)
        {
            if (component == null)
                return string.Empty;
                
            // First try localized tooltips
            if (component.LocalizedTooltips != null && component.LocalizedTooltips.Count > 0)
            {
                var localizedTooltip = GetLocalizedValue(component.LocalizedTooltips);
                if (!string.IsNullOrEmpty(localizedTooltip))
                    return localizedTooltip;
            }
            
            // Fall back to pre-resolved Tooltip
            return component.Tooltip ?? string.Empty;
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

        /// <summary>
        /// Resolves a content path for .content bundles.
        /// Handles both absolute and relative paths, including parent directory navigation.
        /// </summary>
        /// <param name="bundleDir">The directory of the content bundle</param>
        /// <param name="contentPath">The content path from bundle.yaml (can be relative or absolute)</param>
        /// <returns>The resolved absolute path if it exists, null otherwise</returns>
        private static string ResolveContentPath(string bundleDir, string contentPath)
        {
            if (string.IsNullOrEmpty(contentPath))
                return null;

            // Check if it's an absolute path
            if (Path.IsPathRooted(contentPath))
            {
                if (FileExists(contentPath) && 
                    contentPath.EndsWith(".rfa", StringComparison.OrdinalIgnoreCase))
                {
                    return contentPath;
                }
                return null;
            }

            // Treat as relative to bundle directory
            // Normalize the path to handle .. and . properly
            var resolvedPath = Path.GetFullPath(Path.Combine(bundleDir, contentPath));
            if (FileExists(resolvedPath) && 
                resolvedPath.EndsWith(".rfa", StringComparison.OrdinalIgnoreCase))
            {
                return resolvedPath;
            }

            return null;
        }

        private static string SanitizeClassName(string name)
        {
            var sb = new StringBuilder();
            foreach (char c in name)
                sb.Append(char.IsLetterOrDigit(c) ? c : '_');
            return sb.ToString();
        }

        /// <summary>
        /// Struct to hold all Python script constants
        /// </summary>
        private struct PythonScriptConstants
        {
            public string Title;
            public Dictionary<string, string> LocalizedTitles;
            public string Author;
            public string Doc;
            public Dictionary<string, string> LocalizedTooltips;
            public string HelpUrl;
            public Dictionary<string, string> LocalizedHelpUrls;
            public string Context;
            public List<string> ContextItems;
            public string Highlight;
            public string MinRevitVersion;
            public string MaxRevitVersion;
            public bool IsBeta;
            public bool CleanEngine;
            public bool FullFrameEngine;
            public bool PersistentEngine;
        }

        // Cache Python script constant parsing to avoid re-reading files
        private static Dictionary<string, PythonScriptConstants> _pythonScriptCache = 
            new Dictionary<string, PythonScriptConstants>();

        private static PythonScriptConstants ReadPythonScriptConstants(string scriptPath)
        {
            // Check cache first
            if (_pythonScriptCache.TryGetValue(scriptPath, out var cached))
                return cached;
                
            var result = new PythonScriptConstants();

            // Read all lines to handle multiline strings properly
            var allLines = File.ReadAllLines(scriptPath);
            var lineIndex = 0;
            
            foreach (var line in allLines)
            {
                var trimmedLine = line.TrimStart();
                
                if (trimmedLine.StartsWith("__title__"))
                {
                    // Check if it's a dictionary
                    var dictValue = ExtractPythonDictionary(trimmedLine);
                    if (dictValue != null)
                    {
                        result.LocalizedTitles = LocaleSupport.NormalizeLocaleDict(dictValue);
                        // Get default locale value for backward compatibility
                        result.Title = GetLocalizedValue(result.LocalizedTitles);
                    }
                    else
                    {
                        // Check if it's a multiline triple-quoted string
                        if (trimmedLine.Contains("\"\"\""))
                        {
                            var remainingLines = allLines.Skip(lineIndex + 1).ToList();
                            result.Title = ExtractPythonMultilineString(trimmedLine, remainingLines);
                        }
                        else
                        {
                            result.Title = ExtractPythonConstantValue(trimmedLine);
                        }
                    }
                }
                else if (trimmedLine.StartsWith("__authors__"))
                {
                    // __authors__ is a list, join with newline like Python does
                    var listValue = ExtractPythonList(trimmedLine);
                    if (listValue != null && listValue.Count > 0)
                    {
                        result.Author = string.Join("\n", listValue);
                    }
                }
                else if (trimmedLine.StartsWith("__author__"))
                {
                    // Only use __author__ if __authors__ wasn't found
                    if (string.IsNullOrEmpty(result.Author))
                    {
                        result.Author = ExtractPythonConstantValue(trimmedLine);
                    }
                }
                else if (trimmedLine.StartsWith("__doc__"))
                {
                    // Check if it's a dictionary for multi-language tooltip
                    var dictValue = ExtractPythonDictionary(trimmedLine);
                    if (dictValue != null)
                    {
                        result.LocalizedTooltips = LocaleSupport.NormalizeLocaleDict(dictValue);
                        // Get default locale value for backward compatibility
                        result.Doc = GetLocalizedValue(result.LocalizedTooltips);
                    }
                    else
                    {
                        // Check if it's a multiline triple-quoted string
                        if (trimmedLine.Contains("\"\"\""))
                        {
                            var remainingLines = allLines.Skip(lineIndex + 1).ToList();
                            result.Doc = ExtractPythonMultilineString(trimmedLine, remainingLines);
                        }
                        else
                        {
                            result.Doc = ExtractPythonConstantValue(trimmedLine);
                        }
                    }
                }
                else if (trimmedLine.StartsWith("__helpurl__"))
                {
                    // Check if it's a dictionary for multi-language help URL
                    var dictValue = ExtractPythonDictionary(trimmedLine);
                    if (dictValue != null)
                    {
                        result.LocalizedHelpUrls = LocaleSupport.NormalizeLocaleDict(dictValue);
                        // Get default locale value for backward compatibility
                        result.HelpUrl = GetLocalizedValue(result.LocalizedHelpUrls);
                    }
                    else
                    {
                        result.HelpUrl = ExtractPythonConstantValue(trimmedLine);
                    }
                }
                else if (trimmedLine.StartsWith("__context__"))
                {
                    // Check if it's a list
                    var listValue = ExtractPythonList(trimmedLine);
                    if (listValue != null && listValue.Count > 0)
                    {
                        result.ContextItems = listValue;
                        // Format as context string (ALL must match)
                        result.Context = "(" + string.Join("&", listValue) + ")";
                    }
                    else
                    {
                        result.Context = NormalizeContextString(ExtractPythonConstantValue(trimmedLine));
                    }
                }
                else if (trimmedLine.StartsWith("__highlight__"))
                {
                    result.Highlight = ExtractPythonConstantValue(trimmedLine);
                }
                else if (trimmedLine.StartsWith("__min_revit_ver__"))
                {
                    result.MinRevitVersion = ExtractPythonValue(trimmedLine);
                }
                else if (trimmedLine.StartsWith("__max_revit_ver__"))
                {
                    result.MaxRevitVersion = ExtractPythonValue(trimmedLine);
                }
                else if (trimmedLine.StartsWith("__beta__"))
                {
                    result.IsBeta = ExtractPythonBoolValue(trimmedLine);
                }
                else if (trimmedLine.StartsWith("__cleanengine__"))
                {
                    result.CleanEngine = ExtractPythonBoolValue(trimmedLine);
                }
                else if (trimmedLine.StartsWith("__fullframeengine__"))
                {
                    result.FullFrameEngine = ExtractPythonBoolValue(trimmedLine);
                }
                else if (trimmedLine.StartsWith("__persistentengine__"))
                {
                    result.PersistentEngine = ExtractPythonBoolValue(trimmedLine);
                }
                
                lineIndex++;
            }

            _pythonScriptCache[scriptPath] = result;
            return result;
        }

        /// <summary>
        /// Extracts a Python list from a line like: __context__ = ['OST_Walls', 'OST_TextNotes']
        /// </summary>
        private static List<string> ExtractPythonList(string line)
        {
            var parts = line.Split(new[] { '=' }, 2, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length == 2)
            {
                var value = parts[1].Trim();
                // Check if it's a list literal
                if (value.StartsWith("[") && value.EndsWith("]"))
                {
                    var items = new List<string>();
                    // Remove outer brackets
                    value = value.Substring(1, value.Length - 2);
                    
                    // Split by comma, handling quoted strings
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
                        }
                        else if (inQuote && ch == quoteChar && (i == 0 || value[i - 1] != '\\'))
                        {
                            inQuote = false;
                            quoteChar = '\0';
                        }
                        else if (!inQuote && ch == ',')
                        {
                            var trimmed = currentItem.Trim().Trim('\'', '"');
                            if (!string.IsNullOrWhiteSpace(trimmed))
                                items.Add(trimmed);
                            currentItem = "";
                        }
                        else if (!inQuote || (ch != '"' && ch != '\''))
                        {
                            currentItem += ch;
                        }
                    }
                    
                    // Add last item
                    var lastTrimmed = currentItem.Trim().Trim('\'', '"');
                    if (!string.IsNullOrWhiteSpace(lastTrimmed))
                        items.Add(lastTrimmed);
                    
                    return items.Count > 0 ? items : null;
                }
            }
            return null;
        }

        private static string NormalizeContextString(string context)
        {
            if (string.IsNullOrWhiteSpace(context))
                return context;

            var trimmed = context.Trim();
            if (trimmed.IndexOf('(') >= 0 || trimmed.IndexOf(')') >= 0)
                return trimmed;

            return "(" + trimmed + ")";
        }

        /// <summary>
        /// Extracts a multiline Python string literal (triple-quoted) from the remaining lines.
        /// Handles docstrings and other multiline string content.
        /// </summary>
        private static string ExtractPythonMultilineString(string firstLine, IEnumerable<string> remainingLines)
        {
            // Find the opening triple quote position in the first line
            var firstLineTrimmed = firstLine.TrimStart();
            int firstQuotePos = firstLineTrimmed.IndexOf("\"\"\"");
            if (firstQuotePos == -1)
                return null;
            
            int contentStart = firstQuotePos + 3;
            string partialContent = firstLineTrimmed.Substring(contentStart);
            
            // Check if the closing quote is on the same line
            int closingQuotePos = partialContent.IndexOf("\"\"\"");
            if (closingQuotePos != -1)
            {
                // Single-line multiline string
                return partialContent.Substring(0, closingQuotePos);
            }
            
            // Need to read more lines to find the closing triple quote
            var content = new StringBuilder();
            content.Append(partialContent);
            content.Append("\n");
            
            foreach (var line in remainingLines)
            {
                content.Append(line);
                content.Append("\n");
                
                // Check if this line contains the closing triple quote
                if (line.Contains("\"\"\""))
                {
                    // Find the last occurrence of triple quotes in this line
                    var lastQuotePos = line.LastIndexOf("\"\"\"");
                    if (lastQuotePos > 0)
                    {
                        // Remove the content after the closing triple quote (including the quote itself)
                        var beforeClosing = line.Substring(0, lastQuotePos);
                        // Remove the content we just added and replace with proper content
                        content.Length -= line.Length + 1; // Remove the last line + newline
                        content.Append(beforeClosing);
                    }
                    break;
                }
            }
            
            // Process escape sequences in the collected content
            return ProcessPythonEscapeSequences(content.ToString());
        }

        private static string ExtractPythonConstantValue(string line)
        {
            var parts = line.Split(new[] { '=' }, 2, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length == 2)
            {
                var value = ExtractPythonStringContent(parts[1]);
                // Process Python escape sequences to match runtime behavior
                return ProcessPythonEscapeSequences(value);
            }
            return null;
        }

        /// <summary>
        /// Extracts a Python value that can be either quoted string or unquoted (like numbers).
        /// For example: '__min_revit_ver__ = 2021' returns '2021'
        /// </summary>
        private static string ExtractPythonValue(string line)
        {
            var parts = line.Split(new[] { '=' }, 2, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length == 2)
            {
                var value = parts[1].Trim();
                
                // Try to extract quoted string first
                var quotedValue = ExtractPythonStringContent(value);
                if (quotedValue != null)
                    return ProcessPythonEscapeSequences(quotedValue);
                
                // If no quotes, return the value as-is (for unquoted numbers, etc.)
                // Remove any trailing comments
                var commentIndex = value.IndexOf('#');
                if (commentIndex >= 0)
                    value = value.Substring(0, commentIndex).Trim();
                
                return string.IsNullOrEmpty(value) ? null : value;
            }
            return null;
        }

        /// <summary>
        /// Extracts a Python boolean value (True/False) from a line like: __beta__ = True
        /// </summary>
        private static bool ExtractPythonBoolValue(string line)
        {
            var parts = line.Split(new[] { '=' }, 2, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length == 2)
            {
                var value = parts[1].Trim().ToLowerInvariant();
                if (value == "true")
                    return true;
                if (value == "false")
                    return false;
            }
            return false;
        }

        /// <summary>
        /// Extracts the content of a Python string literal, properly handling quotes, escape sequences, and trailing comments.
        /// For example: '"Hello World"   # comment' returns 'Hello World'
        /// </summary>
        private static string ExtractPythonStringContent(string value)
        {
            if (string.IsNullOrEmpty(value))
                return null;

            var trimmedValue = value.TrimStart();
            
            // Find the first quote (either single or double)
            int startIndex = -1;
            char quoteChar = '\0';
            
            for (int i = 0; i < trimmedValue.Length; i++)
            {
                if (trimmedValue[i] == '"' || trimmedValue[i] == '\'')
                {
                    startIndex = i;
                    quoteChar = trimmedValue[i];
                    break;
                }
            }

            if (startIndex == -1)
                return null;

            // Find the closing quote, handling escaped quotes
            int endIndex = startIndex + 1;
            while (endIndex < trimmedValue.Length)
            {
                if (trimmedValue[endIndex] == '\\' && endIndex + 1 < trimmedValue.Length)
                {
                    // Skip the escaped character
                    endIndex += 2;
                    continue;
                }
                
                if (trimmedValue[endIndex] == quoteChar)
                {
                    // Found the closing quote
                    return trimmedValue.Substring(startIndex + 1, endIndex - startIndex - 1);
                }
                
                endIndex++;
            }

            // No closing quote found, return null
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
                logger.Debug("Error parsing icons for {0}: {1}", componentDirectory, ex.Message);
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

        /// <summary>
        /// Parses on/off toggle icons for smartbuttons and toggle buttons.
        /// Looks for on.png, on.dark.png, off.png, off.dark.png in the component directory.
        /// </summary>
        /// <param name="componentDirectory">The directory containing the component</param>
        /// <returns>Tuple of (onIconPath, onIconDarkPath, offIconPath, offIconDarkPath)</returns>
        private static (string onIconPath, string onIconDarkPath, string offIconPath, string offIconDarkPath) ParseToggleIcons(string componentDirectory)
        {
            string onIconPath = null, onIconDarkPath = null, offIconPath = null, offIconDarkPath = null;

            if (!Directory.Exists(componentDirectory))
                return (null, null, null, null);

            try
            {
                var files = GetFilesInDirectory(componentDirectory, "*", SearchOption.TopDirectoryOnly);
                
                foreach (var file in files)
                {
                    var fileName = Path.GetFileName(file).ToLowerInvariant();
                    
                    // Check for on icons
                    if (fileName == "on.png" || fileName == "on.ico")
                        onIconPath = file;
                    else if (fileName == "on.dark.png" || fileName == "on.dark.ico")
                        onIconDarkPath = file;
                    // Check for off icons
                    else if (fileName == "off.png" || fileName == "off.ico")
                        offIconPath = file;
                    else if (fileName == "off.dark.png" || fileName == "off.dark.ico")
                        offIconDarkPath = file;
                }
            }
            catch
            {
                // If we can't read the directory, just return nulls
            }

            return (onIconPath, onIconDarkPath, offIconPath, offIconDarkPath);
        }

        /// <summary>
        /// Finds the tooltip media file (tooltip.mp4, tooltip.swf, or tooltip.png) in the component directory.
        /// Matches the Python implementation in genericcomps.py where media_file is discovered by name 'tooltip'.
        /// </summary>
        /// <param name="componentDirectory">The directory containing the component</param>
        /// <returns>Full path to the media file if found, null otherwise</returns>
        private static string FindMediaFile(string componentDirectory)
        {
            if (!Directory.Exists(componentDirectory))
                return null;

            try
            {
                var files = GetFilesInDirectory(componentDirectory, "*", SearchOption.TopDirectoryOnly);
                
                foreach (var file in files)
                {
                    var fileName = Path.GetFileName(file).ToLowerInvariant();
                    var fileNameWithoutExt = Path.GetFileNameWithoutExtension(fileName);
                    
                    // Match by name 'tooltip' (like Python's finder='name' mode)
                    // Supports: tooltip.mp4, tooltip.swf, tooltip.png
                    if (fileNameWithoutExt == "tooltip")
                    {
                        var ext = Path.GetExtension(fileName);
                        if (ext == ".mp4" || ext == ".swf" || ext == ".png")
                        {
                            return file;
                        }
                    }
                }
            }
            catch
            {
                // If we can't read the directory, just return null
            }

            return null;
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
            Separator,
            ComboBox
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
                    case ".combobox": return CommandComponentType.ComboBox;
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
                case CommandComponentType.ComboBox: return ".combobox";
                default: return string.Empty;
            }
        }
    }
}
