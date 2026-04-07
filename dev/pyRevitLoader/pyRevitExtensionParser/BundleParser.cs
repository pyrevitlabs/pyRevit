using System;
using System.Collections.Generic;
using System.IO;
using YamlDotNet.Core;
using YamlDotNet.RepresentationModel;

namespace pyRevitExtensionParser
{
    public class BundleParser
    {
        private struct CachedBundle
        {
            public ParsedBundle Bundle { get; set; }
            public DateTime LastModified { get; set; }
        }

        private static readonly Dictionary<string, CachedBundle> _bundleCache =
            new Dictionary<string, CachedBundle>(StringComparer.OrdinalIgnoreCase);

        public static class BundleYamlParser
        {
            public static ParsedBundle Parse(string filePath)
            {
                if (string.IsNullOrEmpty(filePath))
                    throw new ArgumentNullException(nameof(filePath));

                if (!File.Exists(filePath))
                    throw new FileNotFoundException($"Bundle file not found: {filePath}", filePath);

                var lastModified = File.GetLastWriteTimeUtc(filePath);
                if (_bundleCache.TryGetValue(filePath, out var cached) && cached.LastModified == lastModified)
                    return cached.Bundle;

                var parsed = ParseInternal(filePath);
                _bundleCache[filePath] = new CachedBundle
                {
                    Bundle = parsed,
                    LastModified = lastModified
                };
                return parsed;
            }

            public static void ClearCache()
            {
                _bundleCache.Clear();
            }

            public static bool InvalidateCache(string filePath)
            {
                return _bundleCache.Remove(filePath);
            }
        }

        private static ParsedBundle ParseInternal(string filePath)
        {
            var parsed = new ParsedBundle();
            var yamlText = File.ReadAllText(filePath);
            var stream = new YamlStream();

            try
            {
                using (var reader = new StringReader(yamlText))
                {
                    stream.Load(reader);
                }
            }
            catch (YamlException ex)
            {
                AttachYamlErrorDetails(ex, yamlText);
                throw;
            }

            if (stream.Documents.Count < 1)
                return parsed;

            if (!(stream.Documents[0].RootNode is YamlMappingNode rootMap))
                return parsed;

            foreach (var entry in rootMap.Children)
            {
                var key = GetScalar(entry.Key)?.Trim();
                if (string.IsNullOrEmpty(key))
                    continue;

                ParseTopLevelNode(key, entry.Value, parsed, filePath);
            }

            return parsed;
        }

        private static void AttachYamlErrorDetails(YamlException ex, string yamlText)
        {
            if (ex == null || ex.Data == null)
                return;

            var lineNumber = ex.Start.Line + 1;
            var columnNumber = ex.Start.Column + 1;

            ex.Data["LineNumber"] = lineNumber;
            ex.Data["ColumnNumber"] = columnNumber;

            if (string.IsNullOrEmpty(yamlText))
                return;

            var lines = yamlText
                .Replace("\r\n", "\n")
                .Replace("\r", "\n")
                .Split('\n');

            if (lineNumber > 0 && lineNumber <= lines.Length)
                ex.Data["LineText"] = lines[lineNumber - 1];
        }

        private static void ParseTopLevelNode(string key, YamlNode valueNode, ParsedBundle parsed, string sourcePath)
        {
            var lowerKey = key.ToLowerInvariant();

            switch (lowerKey)
            {
                case "author":
                    parsed.Author = ParseAuthorValue(valueNode);
                    return;
                case "authors":
                    var authors = ParseAuthorsValue(valueNode);
                    if (!string.IsNullOrEmpty(authors))
                        parsed.Author = authors;
                    return;
                case "min_revit_version":
                    parsed.MinRevitVersion = GetScalar(valueNode);
                    return;
                case "max_revit_version":
                    parsed.MaxRevitVersion = GetScalar(valueNode);
                    return;
                case "context":
                    ParseContext(valueNode, parsed);
                    return;
                case "hyperlink":
                    parsed.Hyperlink = GetScalar(valueNode);
                    return;
                case "help_url":
                    ParseLocalizedOrScalar(valueNode, parsed.HelpUrls, sourcePath, "help_url", out var helpUrlScalar);
                    if (!string.IsNullOrEmpty(helpUrlScalar))
                        parsed.HelpUrl = helpUrlScalar;
                    return;
                case "highlight":
                    parsed.Highlight = GetScalar(valueNode)?.ToLowerInvariant();
                    return;
                case "is_beta":
                case "beta":
                    parsed.IsBeta = ParseBool(valueNode);
                    return;
                case "content":
                    parsed.Content = GetScalar(valueNode);
                    return;
                case "content_alt":
                    parsed.ContentAlt = GetScalar(valueNode);
                    return;
                case "background":
                    ParseBackground(valueNode, parsed);
                    return;
                case "assembly":
                    parsed.Assembly = GetScalar(valueNode);
                    return;
                case "command_class":
                    parsed.CommandClass = GetScalar(valueNode);
                    return;
                case "availability_class":
                    parsed.AvailabilityClass = GetScalar(valueNode);
                    return;
                case "title":
                case "titles":
                    ParseLocalizedOrScalar(valueNode, parsed.Titles, sourcePath, "title", out var titleScalar);
                    if (!string.IsNullOrEmpty(titleScalar))
                        parsed.Titles["en_us"] = titleScalar;
                    return;
                case "tooltip":
                case "tooltips":
                    ParseLocalizedOrScalar(valueNode, parsed.Tooltips, sourcePath, "tooltip", out var tooltipScalar);
                    if (!string.IsNullOrEmpty(tooltipScalar))
                        parsed.Tooltips["en_us"] = tooltipScalar;
                    return;
                case "layout":
                case "layout_order":
                    ParseLayout(valueNode, parsed);
                    return;
                case "engine":
                    ParseEngine(valueNode, parsed);
                    return;
                case "modules":
                    ParseModules(valueNode, parsed);
                    return;
                case "members":
                    ParseMembers(valueNode, parsed);
                    return;
                case "templates":
                    ParseTemplates(valueNode, parsed);
                    return;
                case "collapsed":
                    parsed.Collapsed = ParseBool(valueNode);
                    return;
                default:
                    // Keep existing behavior where unknown top-level scalar key-value pairs
                    // are treated as template values.
                    var scalarTemplateValue = GetScalar(valueNode);
                    if (scalarTemplateValue != null)
                        parsed.Templates[key] = scalarTemplateValue;
                    return;
            }
        }

        private static void ParseLocalizedOrScalar(
            YamlNode valueNode,
            Dictionary<string, string> localizedTarget,
            string sourcePath,
            string sectionName,
            out string scalarValue)
        {
            scalarValue = null;

            if (valueNode is YamlScalarNode scalar)
            {
                scalarValue = scalar.Value;
                return;
            }

            if (!(valueNode is YamlMappingNode mapping))
                return;

            foreach (var entry in mapping.Children)
            {
                var rawLocale = GetScalar(entry.Key)?.Trim();
                if (string.IsNullOrEmpty(rawLocale))
                    continue;

                var normalizedLocale = LocaleSupport.NormalizeLocaleKey(rawLocale);
                if (normalizedLocale == null)
                {
                    var suffix = string.IsNullOrEmpty(sourcePath) ? string.Empty : $" ({sourcePath})";
                    ExtensionParser.LogWarning($"Unsupported locale key '{rawLocale}' in bundle.yaml{suffix}");
                    continue;
                }

                var text = GetScalar(entry.Value);
                if (text != null)
                    localizedTarget[normalizedLocale] = text;
            }
        }

        private static string ParseAuthorValue(YamlNode node)
        {
            if (node is YamlScalarNode scalar)
                return scalar.Value;

            if (node is YamlSequenceNode seq)
            {
                var values = new List<string>();
                foreach (var child in seq.Children)
                {
                    var text = GetScalar(child);
                    if (!string.IsNullOrEmpty(text))
                        values.Add(text);
                }
                return values.Count > 0 ? string.Join("\n", values) : null;
            }

            return null;
        }

        private static string ParseAuthorsValue(YamlNode node)
        {
            if (node is YamlSequenceNode seq)
            {
                var values = new List<string>();
                foreach (var child in seq.Children)
                {
                    var text = GetScalar(child);
                    if (!string.IsNullOrEmpty(text))
                        values.Add(text);
                }
                return values.Count > 0 ? string.Join("\n", values) : null;
            }

            return GetScalar(node);
        }

        private static void ParseLayout(YamlNode node, ParsedBundle parsed)
        {
            if (!(node is YamlSequenceNode seq))
                return;

            foreach (var child in seq.Children)
            {
                var item = GetScalar(child);
                if (!string.IsNullOrWhiteSpace(item))
                    ParseLayoutItem(item, parsed);
            }
        }

        private static void ParseLayoutItem(string item, ParsedBundle parsed)
        {
            var componentName = item;
            if (item.Contains("[") && item.EndsWith("]", StringComparison.Ordinal))
            {
                var bracketStart = item.IndexOf('[');
                componentName = item.Substring(0, bracketStart).Trim();
                var directiveContent = item.Substring(bracketStart + 1, item.Length - bracketStart - 2);

                var colonIndex = directiveContent.IndexOf(':');
                if (colonIndex > 0)
                {
                    var directiveType = directiveContent.Substring(0, colonIndex).Trim().ToLowerInvariant();
                    var targetValue = directiveContent.Substring(colonIndex + 1).Trim();

                    if (directiveType == "title")
                    {
                        targetValue = targetValue.Replace("\\n", "\n");
                        parsed.LayoutItemTitles[componentName] = targetValue;
                    }
                    else if ((directiveType == "before" || directiveType == "after" ||
                              directiveType == "beforeall" || directiveType == "afterall") &&
                             !string.IsNullOrEmpty(componentName))
                    {
                        parsed.LayoutDirectives[componentName] = new LayoutDirective
                        {
                            DirectiveType = directiveType,
                            Target = targetValue
                        };
                    }
                }
            }

            if (string.IsNullOrEmpty(componentName))
                componentName = item;

            parsed.LayoutOrder.Add(componentName);
        }

        private static void ParseEngine(YamlNode node, ParsedBundle parsed)
        {
            if (!(node is YamlMappingNode map))
                return;

            foreach (var entry in map.Children)
            {
                var key = GetScalar(entry.Key)?.Trim().ToLowerInvariant();
                if (string.IsNullOrEmpty(key))
                    continue;

                switch (key)
                {
                    case "type":
                        parsed.Engine.Type = GetScalar(entry.Value);
                        break;
                    case "clean":
                        parsed.Engine.Clean = ParseBool(entry.Value);
                        break;
                    case "full_frame":
                        parsed.Engine.FullFrame = ParseBool(entry.Value);
                        break;
                    case "persistent":
                        parsed.Engine.Persistent = ParseBool(entry.Value);
                        break;
                    case "mainthread":
                        parsed.Engine.MainThread = ParseBool(entry.Value);
                        break;
                    case "automate":
                        parsed.Engine.Automate = ParseBool(entry.Value);
                        break;
                    case "dynamo_path":
                        parsed.Engine.DynamoPath = GetScalar(entry.Value);
                        break;
                    case "dynamo_path_exec":
                        parsed.Engine.DynamoPathExec = ParseBool(entry.Value);
                        break;
                    case "dynamo_path_check_existing":
                        parsed.Engine.DynamoPathCheckExisting = ParseBool(entry.Value);
                        break;
                    case "dynamo_force_manual_run":
                        parsed.Engine.DynamoForceManualRun = ParseBool(entry.Value);
                        break;
                    case "dynamo_model_nodes_info":
                        parsed.Engine.DynamoModelNodesInfo = GetScalar(entry.Value);
                        break;
                }
            }
        }

        private static void ParseContext(YamlNode node, ParsedBundle parsed)
        {
            if (node is YamlScalarNode scalar)
            {
                parsed.Context = scalar.Value;
                return;
            }

            if (node is YamlSequenceNode list)
            {
                foreach (var child in list.Children)
                {
                    var text = GetScalar(child);
                    if (!string.IsNullOrEmpty(text))
                        parsed.ContextItems.Add(text);
                }
                return;
            }

            if (!(node is YamlMappingNode map))
                return;

            foreach (var entry in map.Children)
            {
                var key = GetScalar(entry.Key)?.Trim().ToLowerInvariant();
                if (string.IsNullOrEmpty(key))
                    continue;

                if (key == "rule")
                {
                    parsed.Context = GetScalar(entry.Value);
                    continue;
                }

                if (key == "type")
                    continue;

                if (key != "any" && key != "all" && key != "exact" &&
                    key != "not_any" && key != "not_all" && key != "not_exact")
                    continue;

                var rule = new ContextRule { RuleType = key };
                if (entry.Value is YamlSequenceNode ruleItems)
                {
                    foreach (var itemNode in ruleItems.Children)
                    {
                        var item = GetScalar(itemNode);
                        if (!string.IsNullOrEmpty(item))
                            rule.Items.Add(item);
                    }
                }
                else
                {
                    var item = GetScalar(entry.Value);
                    if (!string.IsNullOrEmpty(item))
                        rule.Items.Add(item);
                }

                if (rule.Items.Count > 0)
                    parsed.ContextRules.Add(rule);
            }
        }

        private static void ParseModules(YamlNode node, ParsedBundle parsed)
        {
            if (!(node is YamlSequenceNode seq))
                return;

            foreach (var child in seq.Children)
            {
                var value = GetScalar(child);
                if (!string.IsNullOrEmpty(value))
                    parsed.Modules.Add(value);
            }
        }

        private static void ParseMembers(YamlNode node, ParsedBundle parsed)
        {
            if (node is YamlSequenceNode list)
            {
                foreach (var child in list.Children)
                {
                    if (child is YamlMappingNode memberMap)
                    {
                        var member = ParseMemberMap(memberMap);
                        if (member != null)
                            parsed.Members.Add(member);
                    }
                    else if (child is YamlSequenceNode tuple && tuple.Children.Count >= 2)
                    {
                        var id = GetScalar(tuple.Children[0]);
                        var text = GetScalar(tuple.Children[1]);
                        if (!string.IsNullOrEmpty(id))
                        {
                            parsed.Members.Add(new ComboBoxMember
                            {
                                Id = id,
                                Text = text
                            });
                        }
                    }
                    else
                    {
                        var value = GetScalar(child);
                        if (!string.IsNullOrEmpty(value))
                        {
                            parsed.Members.Add(new ComboBoxMember
                            {
                                Id = value,
                                Text = value
                            });
                        }
                    }
                }
                return;
            }

            if (!(node is YamlMappingNode map))
                return;

            foreach (var entry in map.Children)
            {
                var id = GetScalar(entry.Key);
                var text = GetScalar(entry.Value);
                if (!string.IsNullOrEmpty(id))
                {
                    parsed.Members.Add(new ComboBoxMember
                    {
                        Id = id,
                        Text = text
                    });
                }
            }
        }

        private static ComboBoxMember ParseMemberMap(YamlMappingNode map)
        {
            var member = new ComboBoxMember();

            foreach (var entry in map.Children)
            {
                var key = GetScalar(entry.Key)?.Trim().ToLowerInvariant();
                if (string.IsNullOrEmpty(key))
                    continue;

                var value = GetScalar(entry.Value);
                switch (key)
                {
                    case "id":
                        member.Id = value;
                        break;
                    case "text":
                        member.Text = value;
                        break;
                    case "icon":
                        member.Icon = value;
                        break;
                    case "tooltip":
                        member.Tooltip = value;
                        break;
                    case "group":
                        member.Group = value;
                        break;
                    case "tooltip_image":
                        member.TooltipImage = value;
                        break;
                }
            }

            if (string.IsNullOrEmpty(member.Id) && !string.IsNullOrEmpty(member.Text))
                member.Id = member.Text;
            if (string.IsNullOrEmpty(member.Text) && !string.IsNullOrEmpty(member.Id))
                member.Text = member.Id;

            return string.IsNullOrEmpty(member.Id) && string.IsNullOrEmpty(member.Text) ? null : member;
        }

        private static void ParseTemplates(YamlNode node, ParsedBundle parsed)
        {
            if (!(node is YamlMappingNode map))
                return;

            foreach (var entry in map.Children)
            {
                var key = GetScalar(entry.Key);
                if (string.IsNullOrEmpty(key))
                    continue;

                var value = GetScalar(entry.Value);
                if (value != null)
                    parsed.Templates[key] = value;
            }
        }

        private static void ParseBackground(YamlNode node, ParsedBundle parsed)
        {
            if (node is YamlScalarNode scalar)
            {
                parsed.PanelBackground = scalar.Value;
                return;
            }

            if (!(node is YamlMappingNode map))
                return;

            foreach (var entry in map.Children)
            {
                var key = GetScalar(entry.Key)?.Trim().ToLowerInvariant();
                if (string.IsNullOrEmpty(key))
                    continue;

                var value = GetScalar(entry.Value);
                switch (key)
                {
                    case "panel":
                        parsed.PanelBackground = value;
                        break;
                    case "title":
                        parsed.TitleBackground = value;
                        break;
                    case "slideout":
                        parsed.SlideoutBackground = value;
                        break;
                }
            }
        }

        private static bool ParseBool(YamlNode node)
        {
            var scalar = node as YamlScalarNode;
            if (scalar == null)
                return false;

            var value = scalar.Value?.Trim();
            if (string.IsNullOrEmpty(value))
                return false;

            if (bool.TryParse(value, out var b))
                return b;

            return value.Equals("true", StringComparison.InvariantCultureIgnoreCase)
                   || value.Equals("1", StringComparison.Ordinal)
                   || value.Equals("yes", StringComparison.InvariantCultureIgnoreCase)
                   || value.Equals("on", StringComparison.InvariantCultureIgnoreCase);
        }

        private static string GetScalar(YamlNode node)
        {
            return (node as YamlScalarNode)?.Value;
        }
    }
}
