using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using YamlDotNet.RepresentationModel;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParser
{
    /// <summary>
    /// Parses extension_layout.yaml files to build the component tree.
    /// When an extension has an extension_layout.yaml, tools are discovered
    /// from a flat tools/ directory and arranged into tabs/panels based on
    /// the YAML layout declarations.
    /// </summary>
    public static class LayoutParser
    {
        private const string LayoutFileName = "extension_layout.yaml";
        private const string ToolsDirName = "tools";

        // YAML keys
        private const string TabsKey = "tabs";
        private const string PanelsKey = "panels";
        private const string NameKey = "name";
        private const string TitleKey = "title";
        private const string LayoutKey = "layout";
        private const string LayoutFileKey = "layout_file";
        private const string StackKey = "stack";

        /// <summary>
        /// Checks whether an extension directory has an extension_layout.yaml file.
        /// </summary>
        public static bool HasLayoutFile(string extensionDir)
        {
            if (string.IsNullOrEmpty(extensionDir))
                return false;
            var layoutPath = Path.Combine(extensionDir, LayoutFileName);
            return File.Exists(layoutPath);
        }

        /// <summary>
        /// Gets the path to the layout file for the given extension directory.
        /// Returns null if no layout file exists.
        /// </summary>
        public static string GetLayoutFilePath(string extensionDir)
        {
            if (string.IsNullOrEmpty(extensionDir))
                return null;
            var layoutPath = Path.Combine(extensionDir, LayoutFileName);
            return File.Exists(layoutPath) ? layoutPath : null;
        }

        /// <summary>
        /// Parses the extension using layout-based discovery.
        /// Scans tools/ for recognized bundles, then arranges them into
        /// the tab/panel structure declared in extension_layout.yaml.
        /// </summary>
        /// <param name="extensionDir">Path to the .extension directory</param>
        /// <param name="extensionName">Name of the extension (without .extension suffix)</param>
        /// <param name="inheritedTemplates">Templates inherited from extension bundle.yaml</param>
        /// <param name="revitYear">Running Revit version year (0 to skip filtering)</param>
        /// <returns>List of ParsedComponent (tabs) representing the layout tree</returns>
        public static List<ParsedComponent> ParseLayout(
            string extensionDir,
            string extensionName,
            Dictionary<string, string> inheritedTemplates,
            int revitYear)
        {
            var layoutPath = Path.Combine(extensionDir, LayoutFileName);
            var toolsDir = Path.Combine(extensionDir, ToolsDirName);

            // Build tool index from tools/ directory
            var toolIndex = BuildToolIndex(toolsDir, extensionName, inheritedTemplates, revitYear);

            // Parse the layout YAML
            var layoutYaml = LoadYaml(layoutPath);
            if (layoutYaml == null)
                return new List<ParsedComponent>();

            // Build the component tree from layout
            return BuildComponentTree(layoutYaml, extensionDir, extensionName, toolIndex);
        }

        #region Tool Index

        /// <summary>
        /// Scans the tools/ directory recursively for recognized bundles.
        /// Returns a dictionary mapping tool name to its ParsedComponent.
        /// </summary>
        private static Dictionary<string, ParsedComponent> BuildToolIndex(
            string toolsDir,
            string extensionName,
            Dictionary<string, string> inheritedTemplates,
            int revitYear)
        {
            var index = new Dictionary<string, ParsedComponent>(StringComparer.OrdinalIgnoreCase);

            if (string.IsNullOrEmpty(toolsDir) || !Directory.Exists(toolsDir))
                return index;

            ScanToolDirectory(toolsDir, extensionName, inheritedTemplates, revitYear, index);

            ExtensionParser.LogDebug(
                $"Layout: Built tool index with {index.Count} entries from: {toolsDir}");

            return index;
        }

        /// <summary>
        /// Recursively scans a directory for tool bundles.
        /// Recognized bundles (directories with known postfixes) are indexed.
        /// Plain directories (no recognized postfix) are recursed into as
        /// organizational folders.
        /// </summary>
        private static void ScanToolDirectory(
            string searchDir,
            string extensionName,
            Dictionary<string, string> inheritedTemplates,
            int revitYear,
            Dictionary<string, ParsedComponent> index)
        {
            string[] dirs;
            try
            {
                dirs = Directory.GetDirectories(searchDir);
            }
            catch (Exception ex)
            {
                ExtensionParser.LogError($"Layout: Cannot list directory {searchDir}: {ex.Message}");
                return;
            }

            foreach (var dir in dirs)
            {
                var dirName = Path.GetFileName(dir);

                // Skip hidden/private entries
                if (dirName.StartsWith(".") || dirName.StartsWith("_"))
                    continue;

                var ext = Path.GetExtension(dir);
                var componentType = CommandComponentTypeExtensions.FromExtension(ext);

                if (componentType != CommandComponentType.Unknown)
                {
                    // This is a recognized tool bundle - index it
                    IndexTool(dir, componentType, extensionName, inheritedTemplates, revitYear, index);
                }
                else
                {
                    // Plain organizational folder - recurse into it
                    ScanToolDirectory(dir, extensionName, inheritedTemplates, revitYear, index);
                }
            }
        }

        /// <summary>
        /// Creates a ParsedComponent from a tool bundle directory and adds it to the index.
        /// For container tools (pulldown, splitbutton), also parses their children.
        /// </summary>
        private static void IndexTool(
            string toolPath,
            CommandComponentType componentType,
            string extensionName,
            Dictionary<string, string> inheritedTemplates,
            int revitYear,
            Dictionary<string, ParsedComponent> index)
        {
            var toolName = Path.GetFileNameWithoutExtension(toolPath);
            var displayName = toolName;

            // Check for duplicate names
            if (index.ContainsKey(toolName))
            {
                ExtensionParser.LogWarning(
                    $"Layout: Duplicate tool name \"{toolName}\" found at {toolPath}. " +
                    $"Skipping (first occurrence wins).");
                return;
            }

            // Use the standard ParseComponents logic to fully parse this single bundle.
            // We parse the tool directory as if it were the only entry in a parent directory.
            // This reuses all existing script detection, bundle.yaml parsing, icon handling, etc.
            var parsed = ParseSingleBundle(toolPath, componentType, extensionName, toolName,
                inheritedTemplates, revitYear);

            if (parsed == null)
                return;

            index[toolName] = parsed;
            ExtensionParser.LogDebug(
                $"Layout: Indexed tool \"{toolName}\" ({componentType}) from {toolPath}");
        }

        /// <summary>
        /// Parses a single tool bundle directory into a ParsedComponent.
        /// This delegates to ExtensionParser.ParseComponentSingle to reuse
        /// all existing bundle.yaml, script detection, and icon parsing logic.
        /// </summary>
        private static ParsedComponent ParseSingleBundle(
            string bundleDir,
            CommandComponentType componentType,
            string extensionName,
            string toolName,
            Dictionary<string, string> inheritedTemplates,
            int revitYear)
        {
            // Build the unique ID path in layout format: extensionname_toolname
            var uniquePath = $"{extensionName}_{toolName}";

            // Use the shared single-bundle parser
            return ExtensionParser.ParseSingleComponent(
                bundleDir, componentType, extensionName, uniquePath,
                inheritedTemplates, revitYear);
        }

        #endregion

        #region YAML Parsing

        /// <summary>
        /// Loads and parses a YAML file into a YamlMappingNode.
        /// </summary>
        private static YamlMappingNode LoadYaml(string yamlPath)
        {
            if (!File.Exists(yamlPath))
                return null;

            try
            {
                var yamlText = File.ReadAllText(yamlPath);
                var stream = new YamlStream();
                using (var reader = new StringReader(yamlText))
                {
                    stream.Load(reader);
                }

                if (stream.Documents.Count < 1)
                    return null;

                return stream.Documents[0].RootNode as YamlMappingNode;
            }
            catch (Exception ex)
            {
                ExtensionParser.LogError(
                    $"Layout: Failed to parse YAML file {yamlPath}: {ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// Gets a scalar string value from a YAML node.
        /// </summary>
        private static string GetScalar(YamlNode node)
        {
            return (node as YamlScalarNode)?.Value;
        }

        /// <summary>
        /// Gets a child node from a mapping node by key.
        /// </summary>
        private static YamlNode GetMappingValue(YamlMappingNode mapping, string key)
        {
            foreach (var entry in mapping.Children)
            {
                if (string.Equals(GetScalar(entry.Key), key, StringComparison.OrdinalIgnoreCase))
                    return entry.Value;
            }
            return null;
        }

        #endregion

        #region Component Tree Building

        /// <summary>
        /// Builds the full component tree (tabs > panels > tools) from the layout YAML.
        /// </summary>
        private static List<ParsedComponent> BuildComponentTree(
            YamlMappingNode layoutRoot,
            string extensionDir,
            string extensionName,
            Dictionary<string, ParsedComponent> toolIndex)
        {
            var tabs = new List<ParsedComponent>();

            var tabsNode = GetMappingValue(layoutRoot, TabsKey) as YamlSequenceNode;
            if (tabsNode == null)
            {
                ExtensionParser.LogWarning(
                    $"Layout: No 'tabs' key found in layout file for {extensionName}");
                return tabs;
            }

            foreach (var tabNode in tabsNode.Children)
            {
                var tabMapping = tabNode as YamlMappingNode;
                if (tabMapping == null)
                    continue;

                var tab = CreateTab(tabMapping, extensionDir, extensionName, toolIndex);
                if (tab != null)
                    tabs.Add(tab);
            }

            return tabs;
        }

        /// <summary>
        /// Creates a Tab component from a YAML tab entry.
        /// </summary>
        private static ParsedComponent CreateTab(
            YamlMappingNode tabMapping,
            string extensionDir,
            string extensionName,
            Dictionary<string, ParsedComponent> toolIndex)
        {
            var name = GetScalar(GetMappingValue(tabMapping, NameKey));
            if (string.IsNullOrEmpty(name))
            {
                ExtensionParser.LogWarning("Layout: Tab entry missing 'name' field");
                return null;
            }

            var title = GetScalar(GetMappingValue(tabMapping, TitleKey)) ?? name;
            var namePart = name.Replace(" ", "");
            var uniqueId = ExtensionParser.SanitizeClassName(
                $"{extensionName}_{namePart}".ToLowerInvariant());

            var tab = new ParsedComponent
            {
                Name = namePart,
                DisplayName = name,
                Title = title,
                Type = CommandComponentType.Tab,
                UniqueId = uniqueId,
                Directory = extensionDir,
                Children = new List<ParsedComponent>()
            };

            // Parse panels
            var panelsNode = GetMappingValue(tabMapping, PanelsKey) as YamlSequenceNode;
            if (panelsNode == null)
                return tab;

            foreach (var panelNode in panelsNode.Children)
            {
                var panelMapping = panelNode as YamlMappingNode;
                if (panelMapping == null)
                    continue;

                var panel = CreatePanel(panelMapping, extensionDir, extensionName, toolIndex);
                if (panel != null)
                    tab.Children.Add(panel);
            }

            return tab;
        }

        /// <summary>
        /// Creates a Panel component from a YAML panel entry.
        /// Supports both inline layout and external .panel.yaml files.
        /// </summary>
        private static ParsedComponent CreatePanel(
            YamlMappingNode panelMapping,
            string extensionDir,
            string extensionName,
            Dictionary<string, ParsedComponent> toolIndex)
        {
            var name = GetScalar(GetMappingValue(panelMapping, NameKey));
            if (string.IsNullOrEmpty(name))
            {
                ExtensionParser.LogWarning("Layout: Panel entry missing 'name' field");
                return null;
            }

            var title = GetScalar(GetMappingValue(panelMapping, TitleKey)) ?? name;
            var namePart = name.Replace(" ", "");
            var uniqueId = ExtensionParser.SanitizeClassName(
                $"{extensionName}_{namePart}".ToLowerInvariant());

            var panel = new ParsedComponent
            {
                Name = namePart,
                DisplayName = name,
                Title = title,
                Type = CommandComponentType.Panel,
                UniqueId = uniqueId,
                Directory = extensionDir,
                Children = new List<ParsedComponent>()
            };

            // Determine layout source: external file or inline
            YamlSequenceNode layoutList = null;

            var layoutFileName = GetScalar(GetMappingValue(panelMapping, LayoutFileKey));
            if (!string.IsNullOrEmpty(layoutFileName))
            {
                // External panel layout file
                var panelLayoutPath = Path.Combine(extensionDir, layoutFileName);
                layoutList = LoadPanelLayoutFile(panelLayoutPath);
            }

            if (layoutList == null)
            {
                // Try inline layout
                layoutList = GetMappingValue(panelMapping, LayoutKey) as YamlSequenceNode;
            }

            if (layoutList != null)
            {
                PopulatePanel(panel, layoutList, extensionName, toolIndex);
            }

            return panel;
        }

        /// <summary>
        /// Loads a .panel.yaml file and returns the layout sequence node.
        /// </summary>
        private static YamlSequenceNode LoadPanelLayoutFile(string panelLayoutPath)
        {
            var panelYaml = LoadYaml(panelLayoutPath);
            if (panelYaml == null)
            {
                ExtensionParser.LogWarning(
                    $"Layout: Panel layout file not found or invalid: {panelLayoutPath}");
                return null;
            }

            return GetMappingValue(panelYaml, LayoutKey) as YamlSequenceNode;
        }

        /// <summary>
        /// Populates a panel's children from a layout sequence.
        /// Each entry in the layout can be:
        ///   - A string (tool name reference, separator "---", or slideout ">>>")
        ///   - A mapping with a "stack:" key (creates a stack group)
        /// </summary>
        private static void PopulatePanel(
            ParsedComponent panel,
            YamlSequenceNode layoutList,
            string extensionName,
            Dictionary<string, ParsedComponent> toolIndex)
        {
            foreach (var item in layoutList.Children)
            {
                if (item is YamlScalarNode scalarNode)
                {
                    var value = scalarNode.Value;
                    if (string.IsNullOrEmpty(value))
                        continue;

                    if (value.Contains("---"))
                    {
                        // Separator
                        panel.Children.Add(new ParsedComponent
                        {
                            Name = "---",
                            DisplayName = "---",
                            Type = CommandComponentType.Separator,
                            Directory = panel.Directory
                        });
                    }
                    else if (value.Contains(">>>"))
                    {
                        // Slideout marker
                        panel.Children.Add(new ParsedComponent
                        {
                            Name = ">>>",
                            DisplayName = ">>>",
                            Type = CommandComponentType.Separator,
                            HasSlideout = true,
                            Directory = panel.Directory
                        });
                    }
                    else
                    {
                        // Tool name reference - look up in index
                        if (toolIndex.TryGetValue(value, out var tool))
                        {
                            panel.Children.Add(tool);
                        }
                        else
                        {
                            ExtensionParser.LogWarning(
                                $"Layout: Tool \"{value}\" referenced in panel " +
                                $"\"{panel.DisplayName}\" not found in tools/ directory");
                        }
                    }
                }
                else if (item is YamlMappingNode mappingNode)
                {
                    // Check for stack: key
                    var stackNode = GetMappingValue(mappingNode, StackKey) as YamlSequenceNode;
                    if (stackNode != null)
                    {
                        var stack = CreateStack(stackNode, panel, extensionName, toolIndex);
                        if (stack != null)
                            panel.Children.Add(stack);
                    }
                }
            }
        }

        /// <summary>
        /// Creates a Stack component from a YAML stack entry.
        /// A stack groups 2-3 buttons vertically.
        /// </summary>
        private static ParsedComponent CreateStack(
            YamlSequenceNode stackItems,
            ParsedComponent parentPanel,
            string extensionName,
            Dictionary<string, ParsedComponent> toolIndex)
        {
            var stackChildren = new List<ParsedComponent>();

            foreach (var stackItem in stackItems.Children)
            {
                var toolName = GetScalar(stackItem);
                if (string.IsNullOrEmpty(toolName))
                    continue;

                if (toolIndex.TryGetValue(toolName, out var tool))
                {
                    stackChildren.Add(tool);
                }
                else
                {
                    ExtensionParser.LogWarning(
                        $"Layout: Tool \"{toolName}\" referenced in stack " +
                        $"(panel \"{parentPanel.DisplayName}\") not found in tools/ directory");
                }
            }

            if (stackChildren.Count == 0)
                return null;

            // Generate a unique name for the stack from its children
            var stackName = string.Join("", stackChildren.Select(c => c.Name));
            var uniqueId = ExtensionParser.SanitizeClassName(
                $"{extensionName}_{stackName}".ToLowerInvariant());

            return new ParsedComponent
            {
                Name = stackName,
                DisplayName = stackName,
                Type = CommandComponentType.Stack,
                UniqueId = uniqueId,
                Directory = parentPanel.Directory,
                Children = stackChildren
            };
        }

        #endregion
    }
}
