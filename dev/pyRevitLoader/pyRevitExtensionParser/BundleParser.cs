using System.Collections.Generic;
using System.IO;

namespace pyRevitExtensionParser
{
    public class BundleParser
    {
        public class ParsedBundle
        {
            public List<string> LayoutOrder { get; set; } = new List<string>();
            public Dictionary<string, string> Titles { get; set; } = new Dictionary<string, string>();
            public Dictionary<string, string> Tooltips { get; set; } = new Dictionary<string, string>();
            /// <summary>
            /// Maps component names (from layout items) to their custom display titles.
            /// Used when layout items specify a custom title like: "Component Name[title:Custom Title]"
            /// </summary>
            public Dictionary<string, string> LayoutItemTitles { get; set; } = new Dictionary<string, string>();
            public string Author { get; set; }
            public string MinRevitVersion { get; set; }
            public string Context { get; set; }
            public string Hyperlink { get; set; }
            public string Highlight { get; set; }
            public string PanelBackground { get; set; }
            public string TitleBackground { get; set; }
            public string SlideoutBackground { get; set; }
            public EngineConfig Engine { get; set; } = new EngineConfig();
            public string Assembly { get; set; }
            public string CommandClass { get; set; }
            public string AvailabilityClass { get; set; }
        }

        public static class BundleYamlParser
        {
            public static ParsedBundle Parse(string filePath)
            {
                var parsed = new ParsedBundle();
                var lines = File.ReadAllLines(filePath);
                string currentSection = null;
                string currentLanguageKey = null;
                bool isInMultilineValue = false;
                bool isLiteralMultiline = false; // |-
                bool isFoldedMultiline = false;  // >-
                var multilineContent = new List<string>();

                for (int i = 0; i < lines.Length; i++)
                {
                    var raw = lines[i];
                    var line = raw.Trim();
                    
                    // Skip empty lines (but preserve them in multiline content)
                    if (string.IsNullOrWhiteSpace(line))
                    {
                        if (isInMultilineValue)
                        {
                            multilineContent.Add("");
                        }
                        continue;
                    }

                    // Handle multiline content continuation
                    if (isInMultilineValue)
                    {
                        // Content must be indented more than the language key (more than 2 spaces)
                        if (raw.StartsWith("    ") || raw.StartsWith("\t\t"))
                        {
                            var content = raw.TrimStart();
                            multilineContent.Add(content);
                            continue;
                        }
                        else
                        {
                            // End of multiline - process accumulated content
                            FinishMultilineValue(parsed, currentSection, currentLanguageKey, multilineContent, 
                                               isLiteralMultiline, isFoldedMultiline);
                            
                            // Reset multiline state
                            isInMultilineValue = false;
                            isLiteralMultiline = false;
                            isFoldedMultiline = false;
                            multilineContent.Clear();
                            currentLanguageKey = null;
                            
                            // Continue to process the current line that ended the multiline
                        }
                    }

                    // Top-level sections (no indentation)
                    if (!raw.StartsWith(" ") && !raw.StartsWith("\t") && line.Contains(":"))
                    {
                        var colonIndex = line.IndexOf(':');
                        currentSection = line.Substring(0, colonIndex).Trim().ToLowerInvariant();
                        var value = line.Substring(colonIndex + 1).Trim();

                        switch (currentSection)
                        {
                            case "author":
                                parsed.Author = value;
                                break;
                            case "min_revit_version":
                                parsed.MinRevitVersion = value;
                                break;
                            case "context":
                                parsed.Context = value;
                                break;
                            case "hyperlink":
                                parsed.Hyperlink = StripQuotes(value);
                                break;
                            case "highlight":
                                parsed.Highlight = value?.ToLowerInvariant();
                                break;
                            case "background":
                                // Single-line format: background: '#BB005591'
                                if (!string.IsNullOrEmpty(value))
                                {
                                    parsed.PanelBackground = StripQuotes(value);
                                }
                                // Multi-line format handled below
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
                            case "tooltip":
                            case "tooltips":
                            case "layout":
                            case "layout_order":
                            case "engine":
                                // These sections have nested content
                                break;
                        }
                        continue;
                    }

                    // Second-level items (indented with 2 spaces or 1 tab)
                    if ((raw.StartsWith("  ") && !raw.StartsWith("    ")) || 
                        (raw.StartsWith("\t") && !raw.StartsWith("\t\t")))
                    {
                        if ((currentSection == "layout" || currentSection == "layout_order") && line.StartsWith("-"))
                        {
                            // Layout list item
                            var item = line.Substring(1).Trim();
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
                        else if ((currentSection == "title" || currentSection == "titles" || 
                                 currentSection == "tooltip" || currentSection == "tooltips") && line.Contains(":"))
                        {
                            // Language-specific title or tooltip
                            var colonIndex = line.IndexOf(':');
                            currentLanguageKey = line.Substring(0, colonIndex).Trim();
                            var value = line.Substring(colonIndex + 1).Trim();

                            if (value == "|-")
                            {
                                // Literal multiline (preserve line breaks)
                                isInMultilineValue = true;
                                isLiteralMultiline = true;
                            }
                            else if (value == ">-")
                            {
                                // Folded multiline (join lines)
                                isInMultilineValue = true;
                                isFoldedMultiline = true;
                            }
                            else if (value == "|" || value == ">")
                            {
                                // Legacy multiline
                                isInMultilineValue = true;
                            }
                            else if (!string.IsNullOrEmpty(value))
                            {
                                // Single-line value - strip quotes if present
                                value = StripQuotes(value);
                                if (currentSection == "title" || currentSection == "titles")
                                    parsed.Titles[currentLanguageKey] = value;
                                else if (currentSection == "tooltip" || currentSection == "tooltips")
                                    parsed.Tooltips[currentLanguageKey] = value;
                            }
                            else
                            {
                                // Empty value after colon - might be implicit multiline
                                isInMultilineValue = true;
                            }
                        }
                        else if (currentSection == "engine" && line.Contains(":"))
                        {
                            // Engine configuration
                            var colonIndex = line.IndexOf(':');
                            var key = line.Substring(0, colonIndex).Trim().ToLowerInvariant();
                            var value = line.Substring(colonIndex + 1).Trim().ToLowerInvariant();

                            switch (key)
                            {
                                case "clean":
                                    parsed.Engine.Clean = value == "true";
                                    break;
                                case "full_frame":
                                    parsed.Engine.FullFrame = value == "true";
                                    break;
                                case "persistent":
                                    parsed.Engine.Persistent = value == "true";
                                    break;
                            }
                        }
                        else if (currentSection == "background" && line.Contains(":"))
                        {
                            // Multi-line background configuration
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
                    }
                }

                // Handle any remaining multiline content at end of file
                if (isInMultilineValue && multilineContent.Count > 0)
                {
                    FinishMultilineValue(parsed, currentSection, currentLanguageKey, multilineContent,
                                       isLiteralMultiline, isFoldedMultiline);
                }

                return parsed;
            }

            private static string StripQuotes(string value)
            {
                if (string.IsNullOrEmpty(value))
                    return value;
                
                // Handle single quotes
                if (value.StartsWith("'") && value.EndsWith("'") && value.Length >= 2)
                {
                    return value.Substring(1, value.Length - 2);
                }
                
                // Handle double quotes
                if (value.StartsWith("\"") && value.EndsWith("\"") && value.Length >= 2)
                {
                    return value.Substring(1, value.Length - 2);
                }
                
                return value;
            }

            private static void FinishMultilineValue(ParsedBundle parsed, string section, string languageKey,
                                                   List<string> content, bool isLiteral, bool isFolded)
            {
                if (content.Count == 0 || string.IsNullOrEmpty(languageKey) || string.IsNullOrEmpty(section))
                    return;

                var processedValue = ProcessMultilineValue(content, isLiteral, isFolded);
                
                if (section == "title" || section == "titles")
                    parsed.Titles[languageKey] = processedValue;
                else if (section == "tooltip" || section == "tooltips")
                    parsed.Tooltips[languageKey] = processedValue;
            }

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
                    // Folded style: join lines with spaces, preserve paragraph breaks
                    var result = new List<string>();
                    var currentParagraph = new List<string>();

                    foreach (var line in lines)
                    {
                        if (string.IsNullOrWhiteSpace(line))
                        {
                            // Empty line - end current paragraph
                            if (currentParagraph.Count > 0)
                            {
                                result.Add(string.Join(" ", currentParagraph));
                                currentParagraph.Clear();
                            }
                            result.Add("");
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
        }
    }
}
