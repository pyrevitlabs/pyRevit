using System;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;

namespace pyRevitExtensionParser
{
    /// <summary>
    /// High-performance parser for pyRevit bundle YAML configuration files.
    /// </summary>
    /// <remarks>
    /// <para>This parser is optimized for pyRevit's specific YAML subset and provides:</para>
    /// <list type="bullet">
    /// <item><description>File modification-based caching for improved performance</description></item>
    /// <item><description>Support for localized titles and tooltips</description></item>
    /// <item><description>YAML multiline syntax (literal |- and folded >-)</description></item>
    /// <item><description>Custom layout title syntax: Component[title:Custom Title]</description></item>
    /// </list>
    /// <para>This is NOT a full YAML 1.2 parser - it only supports the subset used by pyRevit bundles.</para>
    /// </remarks>
    public class BundleParser
    {
        /// <summary>
        /// Cached parsed bundles with file modification tracking for invalidation.
        /// Key: file path, Value: (ParsedBundle, LastWriteTimeUtc)
        /// </summary>
        private static readonly Dictionary<string, CachedBundle> _bundleCache = 
            new Dictionary<string, CachedBundle>();

        /// <summary>
        /// Regex for unescaping string values (compiled for performance).
        /// </summary>
        private static readonly Regex _unescapeRegex = new Regex(
            @"\\([nrt\\'])",
            RegexOptions.Compiled
        );

        /// <summary>
        /// Represents a cached bundle with its last modification time for invalidation.
        /// </summary>
        private struct CachedBundle
        {
            /// <summary>
            /// Gets or sets the parsed bundle data.
            /// </summary>
            public ParsedBundle Bundle { get; set; }

            /// <summary>
            /// Gets or sets the last modification time of the bundle file.
            /// </summary>
            public DateTime LastModified { get; set; }
        }

        /// <summary>
        /// Nested class providing the main parsing API.
        /// Maintains backward compatibility with existing code.
        /// </summary>
        public static class BundleYamlParser
        {
            /// <summary>
            /// Parses a bundle YAML file and returns the configuration.
            /// Uses intelligent caching based on file modification time.
            /// </summary>
            /// <param name="filePath">Full path to the bundle.yaml file to parse.</param>
            /// <returns>
            /// A <see cref="ParsedBundle"/> object containing all parsed configuration.
            /// </returns>
            /// <exception cref="ArgumentNullException">Thrown when filePath is null or empty.</exception>
            /// <exception cref="FileNotFoundException">Thrown when the specified file does not exist.</exception>
            /// <exception cref="IOException">Thrown when file cannot be read.</exception>
            /// <remarks>
            /// <para>The parser implements a file modification-based cache:</para>
            /// <list type="number">
            /// <item><description>Checks if file is already cached</description></item>
            /// <item><description>Validates cache by comparing file modification time</description></item>
            /// <item><description>Returns cached result if file hasn't changed</description></item>
            /// <item><description>Re-parses and updates cache if file was modified</description></item>
            /// </list>
            /// <para>This provides significant performance improvements when parsing the same
            /// bundle multiple times during extension loading or refresh operations.</para>
            /// </remarks>
            /// <example>
            /// <code>
            /// var bundle = BundleParser.BundleYamlParser.Parse(@"C:\Extensions\MyExt\MyCommand.pushbutton\bundle.yaml");
            /// Console.WriteLine($"Command: {bundle.Titles["en_us"]}");
            /// Console.WriteLine($"Engine Clean: {bundle.Engine.Clean}");
            /// </code>
            /// </example>
            public static ParsedBundle Parse(string filePath)
            {
                if (string.IsNullOrEmpty(filePath))
                    throw new ArgumentNullException(nameof(filePath));

                if (!File.Exists(filePath))
                    throw new FileNotFoundException($"Bundle file not found: {filePath}", filePath);

                // Check cache with file modification validation
                var lastModified = File.GetLastWriteTimeUtc(filePath);
                if (_bundleCache.TryGetValue(filePath, out var cached))
                {
                    // Validate cache by checking modification time
                    if (cached.LastModified == lastModified)
                    {
                        return cached.Bundle;
                    }
                }

                // Parse the file
                var parsed = ParseInternal(filePath);

                // Update cache with new data and modification time
                _bundleCache[filePath] = new CachedBundle
                {
                    Bundle = parsed,
                    LastModified = lastModified
                };

                return parsed;
            }

            /// <summary>
            /// Clears the internal parse cache, forcing re-parsing on next access.
            /// </summary>
            /// <remarks>
            /// Use this method when you know bundle files have been modified externally
            /// and need to ensure fresh parsing, or to free memory if many bundles
            /// were parsed and are no longer needed.
            /// </remarks>
            public static void ClearCache()
            {
                _bundleCache.Clear();
            }

            /// <summary>
            /// Removes a specific file from the cache.
            /// </summary>
            /// <param name="filePath">Full path to the bundle file to remove from cache.</param>
            /// <returns>True if the item was removed; false if it wasn't in the cache.</returns>
            public static bool InvalidateCache(string filePath)
            {
                return _bundleCache.Remove(filePath);
            }
        }

        /// <summary>
        /// Internal parsing logic separated from caching concerns.
        /// </summary>
        private static ParsedBundle ParseInternal(string filePath)
        {
            var parsed = new ParsedBundle();
            var lines = File.ReadAllLines(filePath);
            
            // Parser state
            var state = new ParserState();

            for (int i = 0; i < lines.Length; i++)
            {
                var raw = lines[i];
                var line = raw.Trim();

                // Skip empty lines (but preserve them in multiline content)
                if (string.IsNullOrWhiteSpace(line))
                {
                    if (state.IsInMultilineValue)
                    {
                        state.MultilineContent.Add("");
                    }
                    continue;
                }

                // Handle multiline content continuation
                if (state.IsInMultilineValue)
                {
                    // For top-level multiline (like tooltip: |), content is indented with 2 spaces
                    // For nested multiline (like tooltip:\n  en_us: |), content is indented with 4 spaces
                    // Accept both levels of indentation for multiline content
                    if (raw.StartsWith("  ") || raw.StartsWith("\t"))
                    {
                        // Check if this is a new language key declaration (e.g., "  fr_fr: >-")
                        // This happens in localized sections where multiline content for one language
                        // is followed by another language key at the same indentation level
                        var isNewLanguageKey = false;
                        if ((state.CurrentSection == "title" || state.CurrentSection == "titles" ||
                             state.CurrentSection == "tooltip" || state.CurrentSection == "tooltips") &&
                            line.Contains(":"))
                        {
                            // Check if this looks like a language key (short alphanumeric before colon)
                            var colonIdx = line.IndexOf(':');
                            var potentialKey = line.Substring(0, colonIdx).Trim();
                            // Language keys are typically short (e.g., "ru", "en_us", "fr_fr", "de_de", "chinese_s")
                            if (potentialKey.Length <= 12 && !potentialKey.Contains(" "))
                            {
                                isNewLanguageKey = true;
                            }
                        }
                        
                        if (isNewLanguageKey)
                        {
                            // End current multiline and process as new language key
                            FinishMultilineValue(parsed, state);
                            state.ResetMultiline();
                            // Fall through to parse as second-level item
                        }
                        else
                        {
                            var content = raw.TrimStart();
                            state.MultilineContent.Add(content);
                            continue;
                        }
                    }
                    else
                    {
                        // End of multiline - process accumulated content
                        FinishMultilineValue(parsed, state);
                        state.ResetMultiline();
                        // Continue to process the current line that ended the multiline
                    }
                }

                // Parse the line based on indentation level
                if (!raw.StartsWith(" ") && !raw.StartsWith("\t"))
                {
                    ParseTopLevelSection(line, parsed, state);
                }
                else if ((raw.StartsWith("  ") && !raw.StartsWith("    ")) ||
                         (raw.StartsWith("\t") && !raw.StartsWith("\t\t")))
                {
                    ParseSecondLevelItem(line, raw, parsed, state);
                }
                else if (raw.StartsWith("    ") || raw.StartsWith("\t\t"))
                {
                    // Third level - for member properties and nested configurations
                    ParseThirdLevelItem(line, parsed, state);
                }
            }

            // Handle any remaining multiline content at end of file
            if (state.IsInMultilineValue && state.MultilineContent.Count > 0)
            {
                FinishMultilineValue(parsed, state);
            }

            return parsed;
        }

        /// <summary>
        /// Parses top-level sections (no indentation).
        /// </summary>
        private static void ParseTopLevelSection(string line, ParsedBundle parsed, ParserState state)
        {
            // Handle layout list items at top level (no indentation)
            // In pyRevit bundles, layout items often don't have leading indentation
            if (line.StartsWith("-") && (state.CurrentSection == "layout" || state.CurrentSection == "layout_order"))
            {
                ParseLayoutItem(line, parsed);
                return;
            }
            
            // Handle module list items at top level
            if (line.StartsWith("-") && state.CurrentSection == "modules")
            {
                ParseModuleItem(line, parsed);
                return;
            }

            // Handle member list items at top level (for .combobox bundles)
            if (line.StartsWith("-") && state.CurrentSection == "members")
            {
                // Start a new member
                state.CurrentMember = new ComboBoxMember();
                parsed.Members.Add(state.CurrentMember);
                
                // Check if this line also contains the first property (e.g., "- id: one")
                var memberContent = line.Substring(1).Trim();
                if (memberContent.Contains(":"))
                {
                    ParseMemberProperty(memberContent, state);
                }
                return;
            }
            
            if (!line.Contains(":"))
                return;

            var colonIndex = line.IndexOf(':');
            state.CurrentSection = line.Substring(0, colonIndex).Trim().ToLowerInvariant();
            var value = line.Substring(colonIndex + 1).Trim();

            switch (state.CurrentSection)
            {
                case "author":
                    parsed.Author = value;
                    break;
                case "min_revit_version":
                    parsed.MinRevitVersion = value;
                    break;
                case "context":
                    // Context can be a simple string or a list
                    // If there's a value on this line, it's a simple string
                    // If the line is just "context:", the items follow as a list
                    if (!string.IsNullOrEmpty(value))
                    {
                        parsed.Context = value;
                    }
                    // else: context items will be parsed as second-level items
                    break;
                case "hyperlink":
                    parsed.Hyperlink = StripQuotes(value);
                    break;
                case "highlight":
                    parsed.Highlight = value?.ToLowerInvariant();
                    break;
                case "content":
                    // Content path for .content bundles (family .rfa files)
                    parsed.Content = StripQuotes(value);
                    break;
                case "content_alt":
                    // Alternative content path for .content bundles (CTRL+Click)
                    parsed.ContentAlt = StripQuotes(value);
                    break;
                case "background":
                    // Single-line format: background: '#BB005591'
                    if (!string.IsNullOrEmpty(value))
                    {
                        parsed.PanelBackground = StripQuotes(value);
                    }
                    break;
                case "assembly":
                    parsed.Assembly = StripQuotes(value);
                    break;
                case "command_class":
                    parsed.CommandClass = StripQuotes(value);
                    break;
                case "availability_class":
                    parsed.AvailabilityClass = StripQuotes(value);
                    break;
                case "title":
                case "titles":
                    // Handle multiline indicators or simple non-localized title
                    if (value == "|-")
                    {
                        // Literal multiline (preserve line breaks)
                        state.IsInMultilineValue = true;
                        state.IsLiteralMultiline = true;
                        state.CurrentLanguageKey = "en_us";
                    }
                    else if (value == ">-")
                    {
                        // Folded multiline (join lines)
                        state.IsInMultilineValue = true;
                        state.IsFoldedMultiline = true;
                        state.CurrentLanguageKey = "en_us";
                    }
                    else if (value == "|" || value == ">")
                    {
                        // Legacy multiline
                        state.IsInMultilineValue = true;
                        state.CurrentLanguageKey = "en_us";
                    }
                    else if (!string.IsNullOrEmpty(value))
                    {
                        parsed.Titles["en_us"] = StripQuotes(value);
                    }
                    break;
                case "tooltip":
                case "tooltips":
                    // Handle multiline indicators or simple non-localized tooltip
                    if (value == "|-")
                    {
                        // Literal multiline (preserve line breaks)
                        state.IsInMultilineValue = true;
                        state.IsLiteralMultiline = true;
                        state.CurrentLanguageKey = "en_us";
                    }
                    else if (value == ">-")
                    {
                        // Folded multiline (join lines)
                        state.IsInMultilineValue = true;
                        state.IsFoldedMultiline = true;
                        state.CurrentLanguageKey = "en_us";
                    }
                    else if (value == "|" || value == ">")
                    {
                        // Legacy multiline
                        state.IsInMultilineValue = true;
                        state.CurrentLanguageKey = "en_us";
                    }
                    else if (!string.IsNullOrEmpty(value))
                    {
                        parsed.Tooltips["en_us"] = StripQuotes(value);
                    }
                    break;
                // These sections have nested content and are handled by second/third level parsing
                case "layout":
                case "layout_order":
                case "engine":
                case "modules":
                case "members":
                case "templates":
                    // Just set the section, don't process value - nested content follows
                    break;
                default:
                    // Any unknown top-level key is treated as a template variable
                    // This supports liquid tag substitution like {{template_test}}
                    if (!string.IsNullOrEmpty(value))
                    {
                        var originalKey = line.Substring(0, colonIndex).Trim();
                        parsed.Templates[originalKey] = StripQuotes(value);
                    }
                    break;
            }
        }

        /// <summary>
        /// Parses second-level items (indented with 2 spaces or 1 tab).
        /// </summary>
        private static void ParseSecondLevelItem(string line, string raw, ParsedBundle parsed, ParserState state)
        {
            // Layout list items
            if ((state.CurrentSection == "layout" || state.CurrentSection == "layout_order") && line.StartsWith("-"))
            {
                ParseLayoutItem(line, parsed);
                return;
            }

            // Module list items
            if (state.CurrentSection == "modules" && line.StartsWith("-"))
            {
                ParseModuleItem(line, parsed);
                return;
            }
            
            // Context list items or context rules
            if (state.CurrentSection == "context")
            {
                if (line.StartsWith("-"))
                {
                    // Simple list item: - OST_Walls
                    ParseContextListItem(line, parsed);
                }
                else if (line.Contains(":"))
                {
                    // Context rule: any:, all:, exact:, not_any:, etc.
                    ParseContextRule(line, parsed, state);
                }
                return;
            }

            // Member list items for ComboBox
            if (state.CurrentSection == "members")
            {
                if (line.StartsWith("-"))
                {
                    // Start a new member
                    state.CurrentMember = new ComboBoxMember();
                    parsed.Members.Add(state.CurrentMember);
                    
                    // Check if this line also contains the first property (e.g., "- id: one")
                    var memberContent = line.Substring(1).Trim();
                    if (memberContent.Contains(":"))
                    {
                        ParseMemberProperty(memberContent, state);
                    }
                }
                else if (line.Contains(":") && state.CurrentMember != null)
                {
                    // Parse member property
                    ParseMemberProperty(line, state);
                }
                return;
            }

            // Localized titles/tooltips
            if ((state.CurrentSection == "title" || state.CurrentSection == "titles" ||
                 state.CurrentSection == "tooltip" || state.CurrentSection == "tooltips") && line.Contains(":"))
            {
                ParseLocalizedText(line, parsed, state);
                return;
            }

            // Engine configuration
            if (state.CurrentSection == "engine" && line.Contains(":"))
            {
                ParseEngineConfig(line, parsed);
                return;
            }

            // Background configuration
            if (state.CurrentSection == "background" && line.Contains(":"))
            {
                ParseBackgroundConfig(line, parsed);
                return;
            }

            // Templates section - nested key:value pairs
            if (state.CurrentSection == "templates" && line.Contains(":"))
            {
                var colonIndex = line.IndexOf(':');
                var key = line.Substring(0, colonIndex).Trim();
                var value = line.Substring(colonIndex + 1).Trim();
                if (!string.IsNullOrEmpty(value))
                {
                    parsed.Templates[key] = StripQuotes(value);
                }
            }
        }

        /// <summary>
        /// Parses a layout list item with optional custom title syntax.
        /// </summary>
        private static void ParseLayoutItem(string line, ParsedBundle parsed)
        {
            var item = line.Substring(1).Trim();
            
            // Strip quotes if present
            if ((item.StartsWith("\"") && item.EndsWith("\"")) ||
                (item.StartsWith("'") && item.EndsWith("'")))
            {
                item = item.Substring(1, item.Length - 2);
            }

            // Check for custom title syntax: "Component[title:Custom Title]"
            var componentName = item;
            if (item.Contains("[title:") && item.EndsWith("]"))
            {
                var titleStartIndex = item.IndexOf("[title:");
                componentName = item.Substring(0, titleStartIndex);
                var titleValue = item.Substring(titleStartIndex + 7, item.Length - titleStartIndex - 8);

                // Unescape \n to newline
                titleValue = titleValue.Replace("\\n", "\n");

                // Store the custom title mapping
                parsed.LayoutItemTitles[componentName] = titleValue;
            }

            parsed.LayoutOrder.Add(componentName);
        }

        /// <summary>
        /// Parses a module list item.
        /// </summary>
        private static void ParseModuleItem(string line, ParsedBundle parsed)
        {
            var moduleName = line.Substring(1).Trim();
            
            // Strip quotes if present
            if ((moduleName.StartsWith("\"") && moduleName.EndsWith("\"")) ||
                (moduleName.StartsWith("'") && moduleName.EndsWith("'")))
            {
                moduleName = moduleName.Substring(1, moduleName.Length - 2);
            }
            
            parsed.Modules.Add(moduleName);
        }

        /// <summary>
        /// Parses a context list item (e.g., "- OST_Walls").
        /// </summary>
        /// <remarks>
        /// Context can be specified as a simple list:
        /// <code>
        /// context:
        ///   - OST_Walls
        ///   - OST_TextNotes
        /// </code>
        /// This is equivalent to requiring ALL categories to be present.
        /// </remarks>
        private static void ParseContextListItem(string line, ParsedBundle parsed)
        {
            var contextItem = line.Substring(1).Trim();
            
            // Strip quotes if present
            if ((contextItem.StartsWith("\"") && contextItem.EndsWith("\"")) ||
                (contextItem.StartsWith("'") && contextItem.EndsWith("'")))
            {
                contextItem = contextItem.Substring(1, contextItem.Length - 2);
            }
            
            if (!string.IsNullOrEmpty(contextItem))
            {
                parsed.ContextItems.Add(contextItem);
            }
        }

        /// <summary>
        /// Parses a context rule definition (e.g., "any:", "all:", "not_any:").
        /// </summary>
        /// <remarks>
        /// Context rules allow complex availability conditions:
        /// <code>
        /// context:
        ///   any:
        ///     - OST_Walls
        ///     - OST_Doors
        ///   not_all:
        ///     - OST_TextNotes
        /// </code>
        /// </remarks>
        private static void ParseContextRule(string line, ParsedBundle parsed, ParserState state)
        {
            var colonIndex = line.IndexOf(':');
            var ruleType = line.Substring(0, colonIndex).Trim().ToLowerInvariant();
            var value = line.Substring(colonIndex + 1).Trim();
            
            // Supported rule types: any, all, exact, not_any, not_all, not_exact
            if (ruleType == "any" || ruleType == "all" || ruleType == "exact" ||
                ruleType == "not_any" || ruleType == "not_all" || ruleType == "not_exact")
            {
                var rule = new ContextRule { RuleType = ruleType };
                parsed.ContextRules.Add(rule);
                state.CurrentContextRule = rule;
                
                // If there's a value on the same line, it might be a single item
                if (!string.IsNullOrEmpty(value))
                {
                    rule.Items.Add(StripQuotes(value));
                }
            }
        }

        /// <summary>
        /// Parses a context rule item (third level, e.g., "    - OST_Walls" under "  any:").
        /// </summary>
        private static void ParseContextRuleItem(string line, ParserState state)
        {
            if (state.CurrentContextRule == null)
                return;
                
            if (line.StartsWith("-"))
            {
                var item = line.Substring(1).Trim();
                
                // Strip quotes if present
                if ((item.StartsWith("\"") && item.EndsWith("\"")) ||
                    (item.StartsWith("'") && item.EndsWith("'")))
                {
                    item = item.Substring(1, item.Length - 2);
                }
                
                if (!string.IsNullOrEmpty(item))
                {
                    state.CurrentContextRule.Items.Add(item);
                }
            }
        }

        /// <summary>
        /// Parses localized title or tooltip entries with multiline support.
        /// </summary>
        private static void ParseLocalizedText(string line, ParsedBundle parsed, ParserState state)
        {
            var colonIndex = line.IndexOf(':');
            state.CurrentLanguageKey = line.Substring(0, colonIndex).Trim();
            var value = line.Substring(colonIndex + 1).Trim();

            if (value == "|-")
            {
                // Literal multiline (preserve line breaks)
                state.IsInMultilineValue = true;
                state.IsLiteralMultiline = true;
            }
            else if (value == ">-")
            {
                // Folded multiline (join lines)
                state.IsInMultilineValue = true;
                state.IsFoldedMultiline = true;
            }
            else if (value == "|" || value == ">")
            {
                // Legacy multiline
                state.IsInMultilineValue = true;
            }
            else if (!string.IsNullOrEmpty(value))
            {
                // Single-line value
                value = StripQuotes(value);
                if (state.CurrentSection == "title" || state.CurrentSection == "titles")
                    parsed.Titles[state.CurrentLanguageKey] = value;
                else if (state.CurrentSection == "tooltip" || state.CurrentSection == "tooltips")
                    parsed.Tooltips[state.CurrentLanguageKey] = value;
            }
            else
            {
                // Empty value after colon - might be implicit multiline
                state.IsInMultilineValue = true;
            }
        }

        /// <summary>
        /// Parses engine configuration options.
        /// </summary>
        private static void ParseEngineConfig(string line, ParsedBundle parsed)
        {
            var colonIndex = line.IndexOf(':');
            var key = line.Substring(0, colonIndex).Trim().ToLowerInvariant();
            var rawValue = line.Substring(colonIndex + 1).Trim();

            switch (key)
            {
                case "clean":
                    parsed.Engine.Clean = rawValue.Equals("true", StringComparison.InvariantCultureIgnoreCase);
                    break;
                case "full_frame":
                    parsed.Engine.FullFrame = rawValue.Equals("true", StringComparison.InvariantCultureIgnoreCase);
                    break;
                case "persistent":
                    parsed.Engine.Persistent = rawValue.Equals("true", StringComparison.InvariantCultureIgnoreCase);
                    break;
                case "mainthread":
                    parsed.Engine.MainThread = rawValue.Equals("true", StringComparison.InvariantCultureIgnoreCase);
                    break;
                case "automate":
                    parsed.Engine.Automate = rawValue.Equals("true", StringComparison.InvariantCultureIgnoreCase);
                    break;
                case "dynamo_path":
                    parsed.Engine.DynamoPath = StripQuotes(rawValue);
                    break;
                case "dynamo_path_exec":
                    parsed.Engine.DynamoPathExec = rawValue.Equals("true", StringComparison.InvariantCultureIgnoreCase);
                    break;
                case "dynamo_path_check_existing":
                    parsed.Engine.DynamoPathCheckExisting = rawValue.Equals("true", StringComparison.InvariantCultureIgnoreCase);
                    break;
                case "dynamo_force_manual_run":
                    parsed.Engine.DynamoForceManualRun = rawValue.Equals("true", StringComparison.InvariantCultureIgnoreCase);
                    break;
                case "dynamo_model_nodes_info":
                    parsed.Engine.DynamoModelNodesInfo = StripQuotes(rawValue);
                    break;
            }
        }

        /// <summary>
        /// Parses background color configuration.
        /// </summary>
        private static void ParseBackgroundConfig(string line, ParsedBundle parsed)
        {
            var colonIndex = line.IndexOf(':');
            var key = line.Substring(0, colonIndex).Trim().ToLowerInvariant();
            var value = line.Substring(colonIndex + 1).Trim();

            switch (key)
            {
                case "title":
                    parsed.TitleBackground = StripQuotes(value);
                    break;
                case "panel":
                    parsed.PanelBackground = StripQuotes(value);
                    break;
                case "slideout":
                    parsed.SlideoutBackground = StripQuotes(value);
                    break;
            }
        }

        /// <summary>
        /// Parses third-level items (indented with 4 spaces or 2 tabs).
        /// Used for member properties in ComboBox and context rule items.
        /// </summary>
        private static void ParseThirdLevelItem(string line, ParsedBundle parsed, ParserState state)
        {
            // Context rule items (items under any:, all:, exact:, etc.)
            if (state.CurrentSection == "context" && state.CurrentContextRule != null)
            {
                ParseContextRuleItem(line, state);
                return;
            }
            
            // Member properties for ComboBox
            if (state.CurrentSection == "members" && state.CurrentMember != null && line.Contains(":"))
            {
                ParseMemberProperty(line, state);
            }
        }

        /// <summary>
        /// Parses a single ComboBox member property.
        /// </summary>
        private static void ParseMemberProperty(string line, ParserState state)
        {
            if (state.CurrentMember == null)
                return;

            var colonIndex = line.IndexOf(':');
            if (colonIndex <= 0)
                return;

            var key = line.Substring(0, colonIndex).Trim().ToLowerInvariant();
            var value = StripQuotes(line.Substring(colonIndex + 1).Trim());

            switch (key)
            {
                case "id":
                    state.CurrentMember.Id = value;
                    break;
                case "text":
                    state.CurrentMember.Text = value;
                    break;
                case "icon":
                    state.CurrentMember.Icon = value;
                    break;
                case "tooltip":
                    state.CurrentMember.Tooltip = value;
                    break;
                case "group":
                    state.CurrentMember.Group = value;
                    break;
                case "tooltip_image":
                    state.CurrentMember.TooltipImage = value;
                    break;
            }
        }

        /// <summary>
        /// Strips surrounding quotes and processes escape sequences.
        /// </summary>
        /// <param name="value">The string value to process.</param>
        /// <returns>The unquoted and unescaped string.</returns>
        /// <remarks>
        /// <para>Handles both single and double quotes.</para>
        /// <para>Processes standard escape sequences: \n, \r, \t, \\, \'</para>
        /// <para>Uses compiled regex for performance when processing escape sequences.</para>
        /// </remarks>
        private static string StripQuotes(string value)
        {
            if (string.IsNullOrEmpty(value))
                return value;

            // Check for and remove quotes
            if ((value.StartsWith("'") && value.EndsWith("'") && value.Length >= 2) ||
                (value.StartsWith("\"") && value.EndsWith("\"") && value.Length >= 2))
            {
                var unquoted = value.Substring(1, value.Length - 2);
                
                // Process escape sequences using compiled regex for performance
                return _unescapeRegex.Replace(unquoted, match =>
                {
                    switch (match.Groups[1].Value)
                    {
                        case "n": return "\n";
                        case "r": return "\r";
                        case "t": return "\t";
                        case "\\": return "\\";
                        case "'": return "'";
                        default: return match.Value;
                    }
                });
            }

            return value;
        }

        /// <summary>
        /// Completes multiline value processing and stores the result.
        /// </summary>
        private static void FinishMultilineValue(ParsedBundle parsed, ParserState state)
        {
            if (state.MultilineContent.Count == 0 || 
                string.IsNullOrEmpty(state.CurrentLanguageKey) || 
                string.IsNullOrEmpty(state.CurrentSection))
                return;

            var processedValue = ProcessMultilineValue(
                state.MultilineContent,
                state.IsLiteralMultiline,
                state.IsFoldedMultiline);

            if (state.CurrentSection == "title" || state.CurrentSection == "titles")
                parsed.Titles[state.CurrentLanguageKey] = processedValue;
            else if (state.CurrentSection == "tooltip" || state.CurrentSection == "tooltips")
                parsed.Tooltips[state.CurrentLanguageKey] = processedValue;
        }

        /// <summary>
        /// Processes multiline content according to YAML literal (|-) or folded (>-) syntax.
        /// </summary>
        /// <param name="lines">The collected multiline content lines.</param>
        /// <param name="isLiteral">True if using literal syntax (|- preserves line breaks).</param>
        /// <param name="isFolded">True if using folded syntax (>- joins lines with spaces).</param>
        /// <returns>The processed multiline string.</returns>
        /// <remarks>
        /// <para>Literal style (|-): Preserves all line breaks</para>
        /// <para>Folded style (>-): Joins lines with spaces, preserves paragraph breaks (empty lines)</para>
        /// <para>Default style: Joins with newlines</para>
        /// </remarks>
        private static string ProcessMultilineValue(List<string> lines, bool isLiteral, bool isFolded)
        {
            if (lines.Count == 0)
                return string.Empty;

            if (isLiteral)
            {
                // Literal style: preserve line breaks
                return string.Join("\n", lines).TrimEnd('\n');
            }
            else if (isFolded)
            {
                // Folded style: join lines with spaces, empty lines become single newlines
                // Per YAML spec, in folded style (>-), consecutive non-empty lines are joined with spaces,
                // and empty lines create paragraph breaks (single newlines)
                var result = new List<string>();
                var currentParagraph = new List<string>();

                foreach (var line in lines)
                {
                    if (string.IsNullOrWhiteSpace(line))
                    {
                        // Empty line - end current paragraph and start new one
                        if (currentParagraph.Count > 0)
                        {
                            result.Add(string.Join(" ", currentParagraph));
                            currentParagraph.Clear();
                        }
                        // Don't add empty string - the newline between paragraphs 
                        // comes from joining result list with "\n"
                    }
                    else
                    {
                        currentParagraph.Add(line.Trim());
                    }
                }

                // Add final paragraph
                if (currentParagraph.Count > 0)
                {
                    result.Add(string.Join(" ", currentParagraph));
                }

                return string.Join("\n", result).Trim();
            }
            else
            {
                // Default: join with newlines
                return string.Join("\n", lines);
            }
        }

        /// <summary>
        /// Encapsulates the mutable state of the parser to avoid parameter passing.
        /// </summary>
        private class ParserState
        {
            public string CurrentSection { get; set; }
            public string CurrentLanguageKey { get; set; }
            public bool IsInMultilineValue { get; set; }
            public bool IsLiteralMultiline { get; set; }
            public bool IsFoldedMultiline { get; set; }
            public List<string> MultilineContent { get; set; } = new List<string>();
            
            /// <summary>
            /// Current ComboBox member being parsed (for .combobox bundles)
            /// </summary>
            public ComboBoxMember CurrentMember { get; set; }
            
            /// <summary>
            /// Current context rule being parsed (for complex context specifications)
            /// </summary>
            public ContextRule CurrentContextRule { get; set; }

            public void ResetMultiline()
            {
                IsInMultilineValue = false;
                IsLiteralMultiline = false;
                IsFoldedMultiline = false;
                MultilineContent.Clear();
                CurrentLanguageKey = null;
            }
        }
    }
}
