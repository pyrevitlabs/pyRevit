using System;
using System.Collections.Generic;
using System.Diagnostics;
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
        internal static IParserLogger ParserLogger { get; private set; }

        public static void SetLogger(IParserLogger parserLogger)
        {
            ParserLogger = parserLogger;
        }

        internal static void LogDebug(string message)
        {
            if (ParserLogger != null)
                ParserLogger.Debug(message);
            else
                logger.Debug(message);
        }

        internal static void LogInfo(string message)
        {
            if (ParserLogger != null)
                ParserLogger.Info(message);
            else
                logger.Info(message);
        }

        internal static void LogWarning(string message)
        {
            if (ParserLogger != null)
                ParserLogger.Warning(message);
            else
                logger.Warn(message);
        }

        internal static void LogError(string message)
        {
            if (ParserLogger != null)
                ParserLogger.Error(message);
            else
                logger.Error(message);
        }

        private static void LogParseException(string parsedFile, Exception ex)
        {
            if (ex == null)
                return;

            // Use the outer exception for Data (BundleParser enriches the caught exception)
            // Use the innermost exception for message/type (the root cause)
            var rootEx = ex.InnerException ?? ex;
            var lineNo = GetExceptionInt(ex, "LineNumber", "Line", "LineNo");
            var colNo = GetExceptionInt(ex, "ColumnNumber", "Column", "Offset", "LineColumn", "LinePosition");
            var lineText = GetExceptionString(ex, "LineText", "Text", "Line");

            var errMsg = rootEx.Message ?? string.Empty;
            var errType = rootEx.GetType().Name;
            var msg =
                "Error while parsing file:\n" + parsedFile +
                "\nError type: " + errType +
                "\nError Message: " + errMsg +
                "\nLine/Column: " + lineNo + "/" + colNo +
                "\nLine Text: " + lineText;

            LogError(msg);
        }

        /// <summary>
        /// Returns true if the given revitYear falls within the declared min/max version range.
        /// A null or empty constraint is treated as no restriction (open-ended).
        /// A non-empty value that cannot be parsed to an integer is treated as a hard fail.
        /// </summary>
        /// <param name="minRevitVersion">The minimum Revit version.</param>
        /// <param name="maxRevitVersion">The maximum Revit version.</param>
        /// <param name="revitYear">The Revit year of the running Revit instance.</param>
        /// <param name="name">The component or extension name, used in log messages.</param>
        private static bool IsRevitVersionCompatible(string minRevitVersion, string maxRevitVersion, int revitYear, string name)
        {
            // Early exit when Revit version is unknown — skip version filtering entirely
            if (revitYear <= 0)
            {
                LogWarning("Skipping min / max version test, since Revit version is unknown");
                return true;
            }

            bool compatible = true;

            // Parse and validate min_revit_version
            if (!string.IsNullOrEmpty(minRevitVersion))
            {
                if (!int.TryParse(minRevitVersion, out var min))
                {
                    LogWarning($"'{name}': min_revit_version value '{minRevitVersion}' is not a valid integer - skipping.");
                    compatible = false;
                }
                else if (revitYear < min)
                {
                    LogInfo($"'{name}': skipped - requires Revit {min} or later (running {revitYear}).");
                    compatible = false;
                }
            }

            // Parse and validate max_revit_version
            if (!string.IsNullOrEmpty(maxRevitVersion))
            {
                if (!int.TryParse(maxRevitVersion, out var max))
                {
                    LogWarning($"'{name}': max_revit_version value '{maxRevitVersion}' is not a valid integer - skipping.");
                    compatible = false;
                }
                else if (revitYear > max)
                {
                    LogInfo($"'{name}': skipped - requires Revit {max} or earlier (running {revitYear}).");
                    compatible = false;
                }
            }

            return compatible;
        }

        private static int GetExceptionInt(Exception ex, params string[] keys)
        {
            if (ex?.Data == null)
                return 0;

            foreach (var key in keys)
            {
                if (ex.Data.Contains(key) && int.TryParse(ex.Data[key]?.ToString(), out var value))
                    return value;
            }

            return 0;
        }

        private static string GetExceptionString(Exception ex, params string[] keys)
        {
            if (ex?.Data == null)
                return string.Empty;

            foreach (var key in keys)
            {
                if (ex.Data.Contains(key))
                    return ex.Data[key]?.ToString() ?? string.Empty;
            }

            return string.Empty;
        }

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
                try
                {
                    files = Directory.GetFiles(directory, searchPattern, searchOption);
                }
                catch (Exception ex)
                {
                    LogParseException(directory, ex);
                    files = Array.Empty<string>();
                }
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

        // Per-session cache for ReadScriptMetadata so we don't re-read the INI
        // once per script during a single parse pass.
        private static bool? _readScriptMetadataCache;

        private static bool ReadScriptMetadataEnabled()
        {
            if (!_readScriptMetadataCache.HasValue)
                _readScriptMetadataCache = GetConfig().ReadScriptMetadata;
            return _readScriptMetadataCache.Value;
        }

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
            PyRevitConfig.ClearCache();
            _pythonScriptCache.Clear();
            _readScriptMetadataCache = null;
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

        public static IEnumerable<ParsedExtension> ParseInstalledExtensions(int revitYear = 0)
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
                string[] extDirs;
                try
                {
                    extDirs = Directory.GetDirectories(root, "*.extension");
                }
                catch (Exception ex)
                {
                    LogParseException(root, ex);
                    extDirs = Array.Empty<string>();
                }
                foreach (var extDir in extDirs)
                {
                    // Use full path for deduplication
                    var fullPath = Path.GetFullPath(extDir);
                    if (discoveredExtensions.Add(fullPath))
                    {
                        var sw = Stopwatch.StartNew();
                        var parsed = ParseExtension(extDir, revitYear);
                        // Only record timing for extensions actually parsed; disabled or
                        // version-incompatible ones return null after a near-zero config check
                        // and shouldn't appear in the [PERF] breakdown or inflate the count.
                        if (parsed != null)
                        {
                            RecordParseTiming(extDir, "ui", sw.ElapsedMilliseconds);
                            yield return parsed;
                        }
                    }
                }

                // Parse .lib directories (Library extensions)
                string[] libDirs;
                try
                {
                    libDirs = Directory.GetDirectories(root, "*.lib");
                }
                catch (Exception ex)
                {
                    LogParseException(root, ex);
                    libDirs = Array.Empty<string>();
                }
                foreach (var libDir in libDirs)
                {
                    var fullPath = Path.GetFullPath(libDir);
                    if (discoveredExtensions.Add(fullPath))
                    {
                        var sw = Stopwatch.StartNew();
                        var parsed = ParseExtension(libDir, revitYear);
                        if (parsed != null)
                        {
                            RecordParseTiming(libDir, "lib", sw.ElapsedMilliseconds);
                            yield return parsed;
                        }
                    }
                }
            }
        }

        // Per-extension parse timings collected as ParseInstalledExtensions iterates. Read and
        // cleared by SessionManagerService after the .ToList() call that consumes the enumerator.
        private static readonly object _parseStatsLock = new object();
        private static readonly List<(string Name, string Kind, long ElapsedMs)> _parseTimings = new List<(string, string, long)>();

        private static void RecordParseTiming(string extDir, string kind, long elapsedMs)
        {
            lock (_parseStatsLock)
            {
                _parseTimings.Add((Path.GetFileName(extDir), kind, elapsedMs));
            }
        }

        /// <summary>
        /// Returns per-extension parse timings collected since the last call and clears them.
        /// Used by per-session instrumentation to attribute <c>ParseAllExtensions</c> cost to
        /// individual <c>.extension</c> / <c>.lib</c> bundles.
        /// </summary>
        public static List<(string Name, string Kind, long ElapsedMs)> ResetAndGetParseStats()
        {
            lock (_parseStatsLock)
            {
                var snapshot = _parseTimings.ToList();
                _parseTimings.Clear();
                return snapshot;
            }
        }

        /// <summary>
        /// Parses a specific extension from the given extension path
        /// </summary>
        /// <param name="extensionPath">The full path to the .extension or .lib directory</param>
        /// <param name="revitYear">The running Revit version year (e.g. 2024). Pass 0 to skip version filtering.</param>
        /// <returns>A single ParsedExtension if the path is valid and contains an extension, otherwise empty</returns>
        public static IEnumerable<ParsedExtension> ParseInstalledExtensions(string extensionPath, int revitYear = 0)
        {
            if (string.IsNullOrWhiteSpace(extensionPath) || !Directory.Exists(extensionPath))
                yield break;

            // Ensure the directory has .extension or .lib suffix
            if (!extensionPath.EndsWith(".extension", StringComparison.OrdinalIgnoreCase) &&
                !extensionPath.EndsWith(".lib", StringComparison.OrdinalIgnoreCase))
                yield break;

            var parsed = ParseExtension(extensionPath, revitYear);
            if (parsed != null)
                yield return parsed;
        }

        /// <summary>
        /// Parses specific extensions from the given extension paths
        /// </summary>
        /// <param name="extensionPaths">The full paths to the .extension or .lib directories</param>
        /// <param name="revitYear">The running Revit version year (e.g. 2024). Pass 0 to skip version filtering.</param>
        /// <returns>ParsedExtensions for valid paths that contain extensions</returns>
        public static IEnumerable<ParsedExtension> ParseInstalledExtensions(IEnumerable<string> extensionPaths, int revitYear = 0)
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

                var parsed = ParseExtension(extensionPath, revitYear);
                if (parsed != null)
                    yield return parsed;
            }
        }

        // Config caching is now handled inside PyRevitConfig.Load() itself.
        // All callers (UIManagerService, EnvDictionarySeeder, etc.) benefit from the
        // single cache without needing their own copy.  Fix for #3268.
        private static PyRevitConfig GetConfig() => PyRevitConfig.Load();

        /// <summary>
        /// Parses a single extension from the given extension directory path
        /// </summary>
        /// <param name="extDir">The path to the .extension directory</param>
        /// <param name="revitYear">The running Revit version year (e.g. 2024). Pass 0 to skip version filtering.</param>
        /// <returns>A ParsedExtension object, or null if the extension is incompatible with the given Revit version</returns>
        private static ParsedExtension ParseExtension(string extDir, int revitYear = 0)
        {
            var extName = Path.GetFileNameWithoutExtension(extDir);

            // skip disabled extensions before walking the component tree
            var extConfig = GetConfig().ParseExtensionByName(extName);
            if (extConfig != null && extConfig.Disabled)
                return null;

            var bundlePath = Path.Combine(extDir, "bundle.yaml");
            ParsedBundle parsedBundle = null;
            if (FileExists(bundlePath))
            {
                try
                {
                    parsedBundle = BundleParser.BundleYamlParser.Parse(bundlePath);
                }
                catch (Exception ex)
                {
                    LogParseException(bundlePath, ex);
                }
            }

            // Extension-level version gate: skip the entire extension (and its directory tree)
            // if it declares a version range that doesn't include the running Revit year.
            if (!IsRevitVersionCompatible(parsedBundle?.MinRevitVersion, parsedBundle?.MaxRevitVersion, revitYear, extName))
                return null;

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
            // Read extension.json for additional templates and rocket_mode_compatible
            bool rocketModeCompatible = false;
            List<string> authUsers = null;
            List<string> authGroups = null;
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

                    // Read rocket_mode_compatible setting
                    var rocketModeValue = json["rocket_mode_compatible"]?.ToString();
                    if (!string.IsNullOrEmpty(rocketModeValue))
                    {
                        rocketModeCompatible = rocketModeValue.Equals("true", StringComparison.OrdinalIgnoreCase);
                    }

                    // Read authusers if present (list of authorized usernames)
                    var authUsersArray = json["authusers"] as JArray;
                    if (authUsersArray != null && authUsersArray.Count > 0)
                    {
                        authUsers = new List<string>();
                        foreach (var item in authUsersArray)
                        {
                            var user = item?.ToString();
                            if (!string.IsNullOrEmpty(user))
                            {
                                authUsers.Add(user);
                            }
                        }
                    }

                    // Read authgroups if present (list of authorized Windows security groups)
                    var authGroupsArray = json["authgroups"] as JArray;
                    if (authGroupsArray != null && authGroupsArray.Count > 0)
                    {
                        authGroups = new List<string>();
                        foreach (var item in authGroupsArray)
                        {
                            var group = item?.ToString();
                            if (!string.IsNullOrEmpty(group))
                            {
                                authGroups.Add(group);
                            }
                        }
                    }
                }
                catch (Exception ex)
                {
                    LogParseException(extensionJsonPath, ex);
                }
            }

            // pyRevitCore is always rocket mode compatible (hardcoded, matches Python behavior)
            if (string.Equals(extName, "pyRevitCore", StringComparison.OrdinalIgnoreCase))
            {
                rocketModeCompatible = true;
            }

            var children = ParseComponents(extDir, extName, null,
                extensionTemplates.Count > 0 ? extensionTemplates : null,
                revitYear);

            var parsedExtension = new ParsedExtension
            {
                Name = extName,
                Directory = extDir,
                Children = children,
                LayoutOrder = parsedBundle?.LayoutOrder,
                LayoutItemTitles = parsedBundle?.LayoutItemTitles,
                LayoutDirectives = parsedBundle?.LayoutDirectives,
                Titles = parsedBundle?.Titles,
                Tooltips = parsedBundle?.Tooltips,
                MinRevitVersion = parsedBundle?.MinRevitVersion,
                MaxRevitVersion = parsedBundle?.MaxRevitVersion,
                Context = parsedBundle?.GetFormattedContext(),
                Engine = parsedBundle?.Engine,
                Config = extConfig,
                RocketModeCompatible = rocketModeCompatible,
                AuthorizedUsers = authUsers,
                AuthorizedGroups = authGroups
            };

            ReorderByLayout(parsedExtension, parsedExtension, null);

            return parsedExtension;
        }

        /// <summary>
        /// Recursively reorders the given component's Children in-place
        /// according to its own LayoutOrder.  If LayoutOrder is null or empty,
        /// we skip sorting here but still recurse into children.
        /// </summary>
        /// <param name="component">The component to reorder</param>
        /// <param name="extension">The root extension (to store external layout directives)</param>
        /// <param name="currentTabName">The current tab name (for context when storing external directives)</param>
        private static void ReorderByLayout(ParsedComponent component, ParsedExtension extension, string currentTabName)
        {
            if (component?.Children == null)
                return;

            // Track the tab name for children - if this is a tab, use its name
            var tabName = currentTabName;
            if (component.Type == CommandComponentType.Tab)
            {
                tabName = component.DisplayName ?? component.Name;
            }

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

                // Apply layout directives (before, after, beforeall, afterall)
                // External directives (where target is not found) are stored for post-UI-build sorting
                ApplyLayoutDirectives(component, reorderedChildren, extension, tabName);

                component.Children = reorderedChildren;
            }

            foreach (var child in component.Children)
            {
                if (child != null)
                {
                    ReorderByLayout(child, extension, tabName);
                }
            }
        }

        /// <summary>
        /// Applies layout directives (before, after, beforeall, afterall) to reorder components.
        /// Directives that reference external components (not found in children) are stored
        /// in the extension's ExternalLayoutDirectives for post-UI-build sorting.
        /// </summary>
        /// <param name="component">The component containing the layout directives</param>
        /// <param name="children">The list of children to reorder</param>
        /// <param name="extension">The root extension to store external directives</param>
        /// <param name="tabName">The current tab name (for context when storing external directives)</param>
        private static void ApplyLayoutDirectives(ParsedComponent component, List<ParsedComponent> children,
            ParsedExtension extension, string tabName)
        {
            if (component.LayoutDirectives == null || component.LayoutDirectives.Count == 0)
                return;

            // First pass: apply beforeall directives (move to first position)
            var beforeAllItems = component.LayoutDirectives
                .Where(kvp => kvp.Value?.DirectiveType == "beforeall")
                .Select(kvp => kvp.Key)
                .ToList();

            foreach (var itemName in beforeAllItems)
            {
                var item = children.Find(c => c?.DisplayName == itemName);
                if (item != null)
                {
                    children.Remove(item);
                    children.Insert(0, item);
                }
            }

            // Second pass: apply afterall directives (move to last position)
            var afterAllItems = component.LayoutDirectives
                .Where(kvp => kvp.Value?.DirectiveType == "afterall")
                .Select(kvp => kvp.Key)
                .ToList();

            foreach (var itemName in afterAllItems)
            {
                var item = children.Find(c => c?.DisplayName == itemName);
                if (item != null)
                {
                    children.Remove(item);
                    children.Add(item);
                }
            }

            // Third pass: apply before directives (move before target)
            var beforeItems = component.LayoutDirectives
                .Where(kvp => kvp.Value?.DirectiveType == "before")
                .ToList();

            foreach (var kvp in beforeItems)
            {
                var itemName = kvp.Key;
                var targetName = kvp.Value.Target;
                if (string.IsNullOrEmpty(targetName))
                    continue;

                var item = children.Find(c => c?.DisplayName == itemName);
                var target = children.Find(c => c?.DisplayName == targetName);

                if (item != null && target != null && item != target)
                {
                    // Both item and target found internally - apply the directive
                    children.Remove(item);
                    var targetIndex = children.IndexOf(target);
                    children.Insert(targetIndex, item);
                }
                else if (item != null && target == null && extension != null && !string.IsNullOrEmpty(tabName))
                {
                    // Item found but target not found - this is an external directive
                    // (e.g., "Packages & Tags[before:Modify]" where Modify is a native Revit panel)
                    extension.ExternalLayoutDirectives.Add(new ExternalLayoutDirective
                    {
                        TabName = tabName,
                        ComponentName = itemName,
                        DirectiveType = "before",
                        Target = targetName
                    });
                }
            }

            // Fourth pass: apply after directives (move after target)
            var afterItems = component.LayoutDirectives
                .Where(kvp => kvp.Value?.DirectiveType == "after")
                .ToList();

            foreach (var kvp in afterItems)
            {
                var itemName = kvp.Key;
                var targetName = kvp.Value.Target;
                if (string.IsNullOrEmpty(targetName))
                    continue;

                var item = children.Find(c => c?.DisplayName == itemName);
                var target = children.Find(c => c?.DisplayName == targetName);

                if (item != null && target != null && item != target)
                {
                    // Both item and target found internally - apply the directive
                    children.Remove(item);
                    var targetIndex = children.IndexOf(target);
                    children.Insert(targetIndex + 1, item);
                }
                else if (item != null && target == null && extension != null && !string.IsNullOrEmpty(tabName))
                {
                    // Item found but target not found - this is an external directive
                    extension.ExternalLayoutDirectives.Add(new ExternalLayoutDirective
                    {
                        TabName = tabName,
                        ComponentName = itemName,
                        DirectiveType = "after",
                        Target = targetName
                    });
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
            var userExtensionsCount = 0;
            var userExtensionsAdded = 0;
            foreach (var extPath in userExtensions)
            {
                userExtensionsCount++;
                if (string.IsNullOrWhiteSpace(extPath))
                {
                    logger.Debug("Skipping empty userextensions path");
                    continue;
                }

                try
                {
                    var expandedPath = Environment.ExpandEnvironmentVariables(extPath);
                    var normalizedPath = Path.GetFullPath(expandedPath);
                    if (Directory.Exists(normalizedPath))
                    {
                        roots.Add(normalizedPath);
                        userExtensionsAdded++;
                    }
                    else
                    {
                        logger.Debug("Skipping non-existent userextensions path: {0}", normalizedPath);
                        logger.Warn("User extension path does not exist: {0}", normalizedPath);
                    }
                }
                catch (ArgumentException ex)
                {
                    logger.Debug("Skipping invalid userextensions path '{0}': {1}", extPath, ex.Message);
                    logger.Warn("User extension path is invalid: '{0}'", extPath);
                }
                catch (PathTooLongException ex)
                {
                    logger.Debug("Skipping too long userextensions path '{0}': {1}", extPath, ex.Message);
                    logger.Warn("User extension path is too long: '{0}'", extPath);
                }
                catch (NotSupportedException ex)
                {
                    logger.Debug("Skipping unsupported userextensions path '{0}': {1}", extPath, ex.Message);
                    logger.Warn("User extension path is not supported: '{0}'", extPath);
                }
            }

            if (userExtensionsCount > 0 && userExtensionsAdded == 0)
            {
                logger.Warn("No valid userextensions paths found. Check pyRevit_config.ini for non-ASCII or invalid paths.");
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

        /// <summary>
        /// Merges bundle-level localized values over script-level ones; bundle wins on key collision.
        /// </summary>
        private static Dictionary<string, string> MergeLocalized(
            Dictionary<string, string> scriptLocalized,
            Dictionary<string, string> bundleLocalized)
        {
            if (bundleLocalized == null || bundleLocalized.Count == 0)
                return scriptLocalized;

            var result = scriptLocalized ?? new Dictionary<string, string>(bundleLocalized.Count);
            foreach (var kvp in bundleLocalized)
                result[kvp.Key] = kvp.Value;
            return result;
        }

        private static List<ParsedComponent> ParseComponents(
            string baseDir,
            string extensionName,
            string parentPath = null,
            Dictionary<string, string> inheritedTemplates = null,
            int revitYear = 0)
        {
            var components = new List<ParsedComponent>();

            string[] dirs;
            try
            {
                dirs = Directory.GetDirectories(baseDir);
            }
            catch (Exception ex)
            {
                LogParseException(baseDir, ex);
                return components;
            }

            foreach (var dir in dirs)
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

                var bundleDirFiles = GetFilesInDirectory(dir, "*", SearchOption.TopDirectoryOnly);

                string scriptPath = null;

                if (componentType == CommandComponentType.UrlButton)
                {
                    var yaml = Path.Combine(dir, "bundle.yaml");
                    if (FileExists(yaml))
                        scriptPath = yaml;
                }

                if (scriptPath == null)
                {
                    var validEndings = new[] { "script", "_script", "-script", ".script" };
                    var dirFiles = bundleDirFiles.Where(f =>
                    {
                        var nameNoExt = Path.GetFileNameWithoutExtension(f);
                        return validEndings.Any(end => nameNoExt.EndsWith(end, StringComparison.OrdinalIgnoreCase));
                    }).ToArray();

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
                        foreach (var scriptExt in scriptExtensions)
                        {
                            // Look for any file ending with _script{ext} or just {ext}
                            scriptPath = bundleDirFiles.FirstOrDefault(f =>
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

                // Look for config script (*config.py, *config.cs, etc.)
                // e.g. both "config.py" and "name_config.py" will match
                string configScriptPath = null;
                var configExtensions = new[] { ".py", ".cs", ".vb", ".rb", ".dyn", ".gh", ".ghx" };
                // Prefer exact "config{ext}" match, then fall back to postfix "*config{ext}"
                foreach (var configExt in configExtensions)
                {
                    var configFile = $"config{configExt}";
                    configScriptPath = bundleDirFiles.FirstOrDefault(f =>
                        Path.GetFileName(f).Equals(configFile, StringComparison.OrdinalIgnoreCase));
                    if (configScriptPath != null)
                        break;
                }
                if (configScriptPath == null)
                {
                    foreach (var configExt in configExtensions)
                    {
                        var configPostfix = $"config{configExt}";
                        configScriptPath = bundleDirFiles.FirstOrDefault(f =>
                            Path.GetFileName(f).EndsWith(configPostfix, StringComparison.OrdinalIgnoreCase));
                        if (configScriptPath != null)
                            break;
                    }
                }
                // If no separate config script found, use the main script path
                if (configScriptPath == null)
                    configScriptPath = scriptPath;

                var bundleFile = Path.Combine(dir, "bundle.yaml");
                ParsedBundle bundleInComponent = null;
                if (FileExists(bundleFile))
                {
                    try
                    {
                        bundleInComponent = BundleParser.BundleYamlParser.Parse(bundleFile);
                    }
                    catch (Exception ex)
                    {
                        LogParseException(bundleFile, ex);
                    }
                }

                // Handle .content bundles - special logic for Revit family (.rfa) files
                // Content bundles load RFA files, with scriptPath being the primary content
                // and configScriptPath being the alternative content (CTRL+Click)
                if (componentType == CommandComponentType.ContentButton)
                {
                    // Try to get content from bundle.yaml metadata first
                    if (bundleInComponent != null && !string.IsNullOrEmpty(bundleInComponent.Content))
                    {
                        scriptPath = ResolveContentPath(dir, bundleInComponent.Content);
                    }

                    // If no content in metadata, use naming convention
                    if (scriptPath == null)
                    {
                        // Look for version-specific content first: content_{version}.rfa
                        var versionedContent = bundleDirFiles.FirstOrDefault(f =>
                        {
                            var name = Path.GetFileName(f);
                            return name.StartsWith("content_", StringComparison.OrdinalIgnoreCase)
                                && name.EndsWith(".rfa", StringComparison.OrdinalIgnoreCase);
                        });
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
                                var anyRfa = bundleDirFiles.FirstOrDefault(f =>
                                    f.EndsWith(".rfa", StringComparison.OrdinalIgnoreCase));
                                if (anyRfa != null)
                                {
                                    scriptPath = anyRfa;
                                }
                            }
                        }
                    }

                    // Handle alternative content (CTRL+Click)
                    if (bundleInComponent != null && !string.IsNullOrEmpty(bundleInComponent.ContentAlt))
                    {
                        configScriptPath = ResolveContentPath(dir, bundleInComponent.ContentAlt);
                    }
                    else
                    {
                        // Look for version-specific alternative content: other_{version}.rfa
                        var versionedAltContent = bundleDirFiles.FirstOrDefault(f =>
                        {
                            var name = Path.GetFileName(f);
                            return name.StartsWith("other_", StringComparison.OrdinalIgnoreCase)
                                && name.EndsWith(".rfa", StringComparison.OrdinalIgnoreCase);
                        });
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

                // Look for help file (help.* pattern) for file-based help
                var helpFile = FindHelpFile(dir);

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
                var children = ParseComponents(dir, extensionName, fullPath, mergedTemplates, revitYear);

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
                    if (string.IsNullOrEmpty(bundleTitle) &&
                        bundleInComponent.Titles != null &&
                        bundleInComponent.Titles.TryGetValue("en_us", out var bundleTitleEnUs))
                    {
                        bundleTitle = bundleTitleEnUs;
                    }

                    var bundleTooltip = GetLocalizedValue(bundleInComponent.Tooltips);
                    if (string.IsNullOrEmpty(bundleTooltip) &&
                        bundleInComponent.Tooltips != null &&
                        bundleInComponent.Tooltips.TryGetValue("en_us", out var bundleTooltipEnUs))
                    {
                        bundleTooltip = bundleTooltipEnUs;
                    }

                    if (!string.IsNullOrEmpty(bundleTitle))
                        title = bundleTitle;

                    if (!string.IsNullOrEmpty(bundleTooltip))
                        doc = bundleTooltip;

                    if (!string.IsNullOrEmpty(bundleInComponent.Author))
                        author = bundleInComponent.Author;
                }

                var finalLocalizedTitles = MergeLocalized(scriptLocalizedTitles, bundleInComponent?.Titles);
                var finalLocalizedTooltips = MergeLocalized(scriptLocalizedTooltips, bundleInComponent?.Tooltips);
                var finalLocalizedHelpUrls = MergeLocalized(scriptLocalizedHelpUrls, bundleInComponent?.HelpUrls);

                // Apply template substitution to string values
                title = SubstituteTemplates(title, mergedTemplates);
                doc = SubstituteTemplates(doc, mergedTemplates);
                author = SubstituteTemplates(author, mergedTemplates);
                var hyperlink = SubstituteTemplates(bundleInComponent?.Hyperlink, mergedTemplates);
                var bundleHelpUrl = SubstituteTemplates(bundleInComponent?.HelpUrl, mergedTemplates);
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
                string finalHelpUrl = !string.IsNullOrEmpty(bundleHelpUrl)
                    ? bundleHelpUrl
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

                // Component-level version gate: skip this component (and its children) if it declares
                // a version range that doesn't include the running Revit year.
                if (!IsRevitVersionCompatible(finalMinRevitVersion, finalMaxRevitVersion, revitYear, displayName))
                    continue;

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
                    LayoutDirectives = bundleInComponent?.LayoutDirectives,
                    Title = title,
                    Author = author,
                    Context = finalContext,
                    Hyperlink = finalHyperlink,
                    HelpUrl = finalHelpUrl,
                    Highlight = finalHighlight,
                    MinRevitVersion = finalMinRevitVersion,
                    MaxRevitVersion = finalMaxRevitVersion,
                    IsBeta = finalIsBeta,
                    Collapsed = bundleInComponent?.Collapsed ?? false,
                    InheritIcon = bundleInComponent?.InheritIcon ?? true,
                    LargeIcon = bundleInComponent?.LargeIcon ?? false,
                    PanelBackground = bundleInComponent?.PanelBackground,
                    TitleBackground = bundleInComponent?.TitleBackground,
                    SlideoutBackground = bundleInComponent?.SlideoutBackground,
                    Icons = ParseIconsForComponent(dir),
                    TargetAssembly = bundleInComponent?.Assembly,
                    CommandClass = bundleInComponent?.CommandClass,
                    AvailabilityClass = bundleInComponent?.AvailabilityClass,
                    Modules = bundleInComponent?.Modules ?? new List<string>(),
                    LocalizedTitles = (finalLocalizedTitles != null && finalLocalizedTitles.Count > 0) ? finalLocalizedTitles : null,
                    LocalizedTooltips = (finalLocalizedTooltips != null && finalLocalizedTooltips.Count > 0) ? finalLocalizedTooltips : null,
                    LocalizedHelpUrls = (finalLocalizedHelpUrls != null && finalLocalizedHelpUrls.Count > 0) ? finalLocalizedHelpUrls : null,
                    Directory = dir,
                    Engine = finalEngine,
                    Members = bundleInComponent?.Members ?? new List<ComboBoxMember>(),
                    OnIconPath = onIconPath,
                    OnIconDarkPath = onIconDarkPath,
                    OffIconPath = offIconPath,
                    OffIconDarkPath = offIconDarkPath,
                    MediaFile = mediaFile,
                    HelpFile = helpFile
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

            foreach (var locale in LocaleSupport.GetLocaleSearchOrder(preferredLocale, DefaultLocale))
            {
                if (localizedValues.TryGetValue(locale, out string value))
                    return value;
            }

            return null;
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

        /// <summary>
        /// Sanitizes a string using the legacy Python cleanup_string() replacement table.
        /// Public so that HookManager can generate hook IDs matching the legacy format.
        /// See: pyrevitlib/pyrevit/coreutils/__init__.py lines 295-344
        /// </summary>
        public static string SanitizeClassName(string name)
        {
            var result = name
                .Replace(" ", "")
                .Replace("~", "")
                .Replace("!", "EXCLAM")
                .Replace("@", "AT")
                .Replace("#", "SHARP")
                .Replace("$", "DOLLAR")
                .Replace("%", "PERCENT")
                .Replace("^", "")
                .Replace("&", "AND")
                .Replace("*", "STAR")
                .Replace("+", "PLUS")
                .Replace(";", "")
                .Replace(":", "")
                .Replace(",", "")
                .Replace("\"", "")
                .Replace("{", "")
                .Replace("}", "")
                .Replace("[", "")
                .Replace("]", "")
                .Replace("\\(", "")
                .Replace("\\)", "")
                .Replace("(", "")
                .Replace(")", "")
                .Replace("-", "MINUS")
                .Replace("=", "EQUALS")
                .Replace("<", "")
                .Replace(">", "")
                .Replace("?", "QMARK")
                .Replace(".", "DOT")
                // '_' is intentionally NOT replaced — it is the separator (skip=['_'])
                .Replace("|", "VERT")
                .Replace("\\/", "")
                .Replace("\\", "");

            // Final safety pass: strip any character not valid in a C# identifier
            var sb = new StringBuilder(result.Length);
            foreach (char c in result)
                if (char.IsLetterOrDigit(c) || c == '_')
                    sb.Append(c);

            // Fix for #3107: Ensure UniqueId is a valid C# identifier.
            // Leading digits are invalid in C# class names generated by Roslyn.
            // The legacy loader used Reflection.Emit which accepted leading digits.
            if (sb.Length > 0 && char.IsDigit(sb[0]))
                sb.Insert(0, '_');

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
            if (!ReadScriptMetadataEnabled())
                return new PythonScriptConstants();

            if (_pythonScriptCache.TryGetValue(scriptPath, out var cached))
                return cached;

            var result = ParseScriptConstants(scriptPath);
            _pythonScriptCache[scriptPath] = result;
            return result;
        }

        /// <summary>
        /// Reads dunder metadata (__title__, __author__, __doc__, ...) directly from
        /// a Python script and returns it as a bundle.yaml-shaped dictionary.
        /// Bypasses both the read_script_metadata user setting and the per-path cache,
        /// so migration / tooling callers always receive the script's raw declarations.
        /// </summary>
        public static IReadOnlyDictionary<string, object> ReadScriptMetadata(string scriptPath)
        {
            var yaml = new Dictionary<string, object>();
            if (string.IsNullOrEmpty(scriptPath) || !File.Exists(scriptPath))
                return yaml;

            var c = ParseScriptConstants(scriptPath);

            if (c.LocalizedTitles != null && c.LocalizedTitles.Count > 0)
                yaml["title"] = c.LocalizedTitles;
            else if (!string.IsNullOrEmpty(c.Title))
                yaml["title"] = c.Title;

            if (!string.IsNullOrEmpty(c.Author))
                yaml["author"] = c.Author;

            if (c.LocalizedTooltips != null && c.LocalizedTooltips.Count > 0)
                yaml["tooltip"] = c.LocalizedTooltips;
            else if (!string.IsNullOrEmpty(c.Doc))
                yaml["tooltip"] = c.Doc;

            if (c.LocalizedHelpUrls != null && c.LocalizedHelpUrls.Count > 0)
                yaml["help_url"] = c.LocalizedHelpUrls;
            else if (!string.IsNullOrEmpty(c.HelpUrl))
                yaml["help_url"] = c.HelpUrl;

            if (c.ContextItems != null && c.ContextItems.Count > 0)
            {
                yaml["context"] = c.ContextItems;
            }
            else if (!string.IsNullOrEmpty(c.Context))
            {
                // Strip the parser's surrounding "(...)" so the yaml value matches the
                // shape humans write (a bare string like "zero-doc" or "selection").
                var ctx = c.Context.Trim();
                if (ctx.Length >= 2 && ctx[0] == '(' && ctx[ctx.Length - 1] == ')')
                    ctx = ctx.Substring(1, ctx.Length - 2);
                yaml["context"] = ctx;
            }

            if (!string.IsNullOrEmpty(c.Highlight))
                yaml["highlight"] = c.Highlight;
            if (!string.IsNullOrEmpty(c.MinRevitVersion))
                yaml["min_revit_version"] = c.MinRevitVersion;
            if (!string.IsNullOrEmpty(c.MaxRevitVersion))
                yaml["max_revit_version"] = c.MaxRevitVersion;
            if (c.IsBeta)
                yaml["is_beta"] = true;

            var engine = new Dictionary<string, object>();
            if (c.CleanEngine) engine["clean"] = true;
            if (c.FullFrameEngine) engine["full_frame"] = true;
            if (c.PersistentEngine) engine["persistent"] = true;
            if (engine.Count > 0)
                yaml["engine"] = engine;

            return yaml;
        }

        private static PythonScriptConstants ParseScriptConstants(string scriptPath)
        {
            var result = new PythonScriptConstants();

            try
            {
                // Stream lines lazily (File.ReadLines) instead of eager File.ReadAllLines.
                // This keeps peak memory bounded and lets ExtractPythonMultilineString
                // consume continuation lines straight from the enumerator instead of
                // allocating a fresh List<string> per multi-line dunder.
                using (var enumerator = File.ReadLines(scriptPath).GetEnumerator())
                {
                    while (enumerator.MoveNext())
                    {
                        var trimmedLine = enumerator.Current.TrimStart();

                        if (trimmedLine.StartsWith("__title__"))
                        {
                            var dictValue = ExtractPythonDictionary(trimmedLine);
                            if (dictValue != null)
                            {
                                result.LocalizedTitles = LocaleSupport.NormalizeLocaleDict(dictValue);
                                result.Title = GetLocalizedValue(result.LocalizedTitles);
                            }
                            else if (trimmedLine.Contains("\"\"\""))
                            {
                                result.Title = ExtractPythonMultilineString(trimmedLine, enumerator);
                            }
                            else
                            {
                                result.Title = ExtractPythonConstantValue(trimmedLine);
                            }
                        }
                        else if (trimmedLine.StartsWith("__authors__"))
                        {
                            // __authors__ is a list, join with newline like Python does
                            var listValue = ExtractPythonList(trimmedLine);
                            if (listValue != null && listValue.Count > 0)
                                result.Author = string.Join("\n", listValue);
                        }
                        else if (trimmedLine.StartsWith("__author__"))
                        {
                            // Only use __author__ if __authors__ wasn't found
                            if (string.IsNullOrEmpty(result.Author))
                                result.Author = ExtractPythonConstantValue(trimmedLine);
                        }
                        else if (trimmedLine.StartsWith("__doc__"))
                        {
                            var dictValue = ExtractPythonDictionary(trimmedLine);
                            if (dictValue != null)
                            {
                                result.LocalizedTooltips = LocaleSupport.NormalizeLocaleDict(dictValue);
                                result.Doc = GetLocalizedValue(result.LocalizedTooltips);
                            }
                            else if (trimmedLine.Contains("\"\"\""))
                            {
                                result.Doc = ExtractPythonMultilineString(trimmedLine, enumerator);
                            }
                            else
                            {
                                result.Doc = ExtractPythonConstantValue(trimmedLine);
                            }
                        }
                        else if (trimmedLine.StartsWith("__helpurl__"))
                        {
                            var dictValue = ExtractPythonDictionary(trimmedLine);
                            if (dictValue != null)
                            {
                                result.LocalizedHelpUrls = LocaleSupport.NormalizeLocaleDict(dictValue);
                                result.HelpUrl = GetLocalizedValue(result.LocalizedHelpUrls);
                            }
                            else
                            {
                                result.HelpUrl = ExtractPythonConstantValue(trimmedLine);
                            }
                        }
                        else if (trimmedLine.StartsWith("__context__"))
                        {
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
                            result.Highlight = ExtractPythonConstantValue(trimmedLine);
                        else if (trimmedLine.StartsWith("__min_revit_ver__"))
                            result.MinRevitVersion = ExtractPythonValue(trimmedLine);
                        else if (trimmedLine.StartsWith("__max_revit_ver__"))
                            result.MaxRevitVersion = ExtractPythonValue(trimmedLine);
                        else if (trimmedLine.StartsWith("__beta__"))
                            result.IsBeta = ExtractPythonBoolValue(trimmedLine);
                        else if (trimmedLine.StartsWith("__cleanengine__"))
                            result.CleanEngine = ExtractPythonBoolValue(trimmedLine);
                        else if (trimmedLine.StartsWith("__fullframeengine__"))
                            result.FullFrameEngine = ExtractPythonBoolValue(trimmedLine);
                        else if (trimmedLine.StartsWith("__persistentengine__"))
                            result.PersistentEngine = ExtractPythonBoolValue(trimmedLine);
                    }
                }
            }
            catch (Exception ex)
            {
                LogParseException(scriptPath, ex);
            }

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
        /// Extracts a multiline Python string literal (triple-quoted) starting at firstLine,
        /// consuming additional lines from the enumerator until the closing triple quote.
        /// Handles docstrings and other multiline string content.
        /// </summary>
        private static string ExtractPythonMultilineString(string firstLine, IEnumerator<string> enumerator)
        {
            var firstLineTrimmed = firstLine.TrimStart();
            int firstQuotePos = firstLineTrimmed.IndexOf("\"\"\"");
            if (firstQuotePos == -1)
                return null;

            int contentStart = firstQuotePos + 3;
            string partialContent = firstLineTrimmed.Substring(contentStart);

            // Closing quote on the same line — single-line triple-quoted literal.
            int closingQuotePos = partialContent.IndexOf("\"\"\"");
            if (closingQuotePos != -1)
                return partialContent.Substring(0, closingQuotePos);

            var content = new StringBuilder();
            content.Append(partialContent);
            content.Append("\n");

            while (enumerator.MoveNext())
            {
                var line = enumerator.Current;
                content.Append(line);
                content.Append("\n");

                if (line.Contains("\"\"\""))
                {
                    var lastQuotePos = line.LastIndexOf("\"\"\"");
                    if (lastQuotePos > 0)
                    {
                        // Strip the just-appended line + newline and replace with the
                        // content up to (but not including) the closing triple quote.
                        var beforeClosing = line.Substring(0, lastQuotePos);
                        content.Length -= line.Length + 1;
                        content.Append(beforeClosing);
                    }
                    break;
                }
            }

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
            catch (Exception ex)
            {
                LogParseException(componentDirectory, ex);
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
            catch (Exception ex)
            {
                LogParseException(componentDirectory, ex);
            }

            return null;
        }

        /// <summary>
        /// Finds a help file in the component directory matching the pattern "help.*" (e.g., help.html, help.md).
        /// This implements file-based help discovery similar to the Python loader.
        /// </summary>
        /// <param name="componentDirectory">The directory containing the component</param>
        /// <returns>Full path to the help file if found, null otherwise</returns>
        private static string FindHelpFile(string componentDirectory)
        {
            if (!Directory.Exists(componentDirectory))
                return null;

            try
            {
                return GetFilesInDirectory(componentDirectory, "*help.*", SearchOption.TopDirectoryOnly)
                    .FirstOrDefault();
            }
            catch (Exception ex)
            {
                LogParseException(componentDirectory, ex);
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
