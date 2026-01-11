using System.Collections.Generic;

namespace pyRevitExtensionParser
{
    /// <summary>
    /// Represents a context rule for complex command availability conditions.
    /// </summary>
    /// <remarks>
    /// <para>Context rules support the following types:</para>
    /// <list type="bullet">
    /// <item><description>any - Match if ANY of the items match (OR logic)</description></item>
    /// <item><description>all - Match if ALL items match (AND logic)</description></item>
    /// <item><description>exact - Match if selection exactly matches the items</description></item>
    /// <item><description>not_any - Match if NONE of the items match</description></item>
    /// <item><description>not_all - Match if NOT ALL items match</description></item>
    /// <item><description>not_exact - Match if selection does NOT exactly match</description></item>
    /// </list>
    /// </remarks>
    public class ContextRule
    {
        /// <summary>
        /// The type of rule: any, all, exact, not_any, not_all, not_exact
        /// </summary>
        public string RuleType { get; set; }
        
        /// <summary>
        /// The list of items (category names, view types, etc.) for this rule
        /// </summary>
        public List<string> Items { get; set; } = new List<string>();
        
        /// <summary>
        /// Whether this is a NOT rule (inverted logic)
        /// </summary>
        public bool IsNot => RuleType?.StartsWith("not_") == true;
        
        /// <summary>
        /// Gets the separator character for this rule type
        /// </summary>
        public char Separator
        {
            get
            {
                var baseType = IsNot ? RuleType.Substring(4) : RuleType;
                switch (baseType?.ToLowerInvariant())
                {
                    case "any": return '|';
                    case "exact": return ';';
                    case "all":
                    default: return '&';
                }
            }
        }
        
        /// <summary>
        /// Converts this rule to the formatted string for runtime consumption.
        /// </summary>
        /// <returns>Formatted rule string like "(item1&amp;item2)" or "!(item1|item2)"</returns>
        public string ToFormattedString()
        {
            if (Items == null || Items.Count == 0)
                return string.Empty;
                
            var joined = string.Join(Separator.ToString(), Items);
            var formatted = "(" + joined + ")";
            
            return IsNot ? "!" + formatted : formatted;
        }
    }
    
    /// <summary>
    /// Represents a parsed pyRevit bundle configuration containing all metadata,
    /// layout information, and engine settings for a command or component.
    /// </summary>
    /// <remarks>
    /// <para>A bundle is the fundamental unit of a pyRevit command or component, typically defined
    /// in a bundle.yaml file. It contains all the configuration needed to display and execute
    /// the command within Revit.</para>
    /// <para>This class follows the Builder pattern and is populated by <see cref="BundleYamlParser"/>.</para>
    /// </remarks>
    public class ParsedBundle
    {
        /// <summary>
        /// Gets or sets the ordered list of component names defining the layout sequence.
        /// </summary>
        /// <remarks>
        /// Defines the order in which child components (buttons, panels, etc.) should appear
        /// in the Revit UI. Component names may include custom title syntax.
        /// </remarks>
        /// <example>
        /// <code>
        /// layout_order:
        ///   - Button1
        ///   - Button2[title:Custom Name]
        ///   - Separator
        /// </code>
        /// </example>
        public List<string> LayoutOrder { get; set; } = new List<string>();

        /// <summary>
        /// Gets or sets the localized titles for this bundle, keyed by language code.
        /// </summary>
        /// <remarks>
        /// Language codes should follow ISO format (e.g., "en_us", "de_de", "fr_fr").
        /// If a specific language is not found, pyRevit falls back to "en_us".
        /// </remarks>
        /// <example>
        /// <code>
        /// titles:
        ///   en_us: "My Command"
        ///   de_de: "Mein Befehl"
        /// </code>
        /// </example>
        public Dictionary<string, string> Titles { get; set; } = new Dictionary<string, string>();

        /// <summary>
        /// Gets or sets the localized tooltips for this bundle, keyed by language code.
        /// </summary>
        /// <remarks>
        /// Supports multiline tooltips using YAML literal (|-) or folded (>-) syntax.
        /// Tooltips can contain escape sequences like \n for line breaks.
        /// </remarks>
        /// <example>
        /// <code>
        /// tooltips:
        ///   en_us: |-
        ///     This is a multiline tooltip
        ///     with detailed information
        /// </code>
        /// </example>
        public Dictionary<string, string> Tooltips { get; set; } = new Dictionary<string, string>();

        /// <summary>
        /// Maps component names from layout to their custom display titles.
        /// </summary>
        /// <remarks>
        /// <para>Used when layout items specify custom titles using the syntax:</para>
        /// <code>"Component Name[title:Custom Title]"</code>
        /// <para>This allows overriding the default title for a specific layout instance
        /// without modifying the component's bundle.yaml file.</para>
        /// </remarks>
        /// <example>
        /// For layout item "MyButton[title:Click Me\nNow]", this dictionary would contain:
        /// Key: "MyButton", Value: "Click Me\nNow"
        /// </example>
        public Dictionary<string, string> LayoutItemTitles { get; set; } = new Dictionary<string, string>();

        /// <summary>
        /// Gets or sets the author name or organization for this bundle.
        /// </summary>
        /// <remarks>
        /// Displayed in bundle information and credits. Optional field.
        /// </remarks>
        public string Author { get; set; }

        /// <summary>
        /// Gets or sets the minimum Revit version required to run this bundle.
        /// </summary>
        /// <remarks>
        /// <para>Format: "YYYY" (e.g., "2020", "2021", "2024")</para>
        /// <para>If the current Revit version is lower than specified, the command
        /// will not be loaded or will be disabled.</para>
        /// </remarks>
        /// <example>
        /// <code>min_revit_version: 2023</code>
        /// </example>
        public string MinRevitVersion { get; set; }

        /// <summary>
        /// Gets or sets the context filter determining when this bundle is available.
        /// </summary>
        /// <remarks>
        /// <para>Common values (as string or list items):</para>
        /// <list type="bullet">
        /// <item><description>"zero-doc" - Available when no document is open</description></item>
        /// <item><description>"selection" - Available when elements are selected</description></item>
        /// <item><description>"doc-project" - Available in project documents</description></item>
        /// <item><description>"doc-family" - Available in family editor</description></item>
        /// <item><description>"OST_Walls", "OST_Doors", etc. - Built-in category names</description></item>
        /// <item><description>"active-floor-plan", "active-3d-view", etc. - Active view type conditions</description></item>
        /// </list>
        /// <para>The context can be specified as:</para>
        /// <list type="bullet">
        /// <item><description>A single string value</description></item>
        /// <item><description>A list of category/condition values (all must match)</description></item>
        /// <item><description>A dictionary with any/all/exact/not_ keys for complex rules</description></item>
        /// </list>
        /// </remarks>
        /// <example>
        /// Simple string:
        /// <code>context: zero-doc</code>
        /// 
        /// List (all must match):
        /// <code>
        /// context:
        ///   - OST_Walls
        ///   - OST_TextNotes
        /// </code>
        /// 
        /// Complex rules:
        /// <code>
        /// context:
        ///   any:
        ///     - OST_Walls
        ///     - OST_Doors
        /// </code>
        /// </example>
        public string Context { get; set; }
        
        /// <summary>
        /// Gets or sets the list of context items when context is specified as a YAML list.
        /// </summary>
        /// <remarks>
        /// When context is specified as a list in bundle.yaml, items are stored here.
        /// Use <see cref="GetFormattedContext"/> to get the runtime-formatted context string.
        /// </remarks>
        public List<string> ContextItems { get; set; } = new List<string>();
        
        /// <summary>
        /// Gets or sets context rules for complex context specifications using any/all/exact/not_ keys.
        /// </summary>
        /// <remarks>
        /// Stores parsed context rules when using dictionary format:
        /// <code>
        /// context:
        ///   any:
        ///     - OST_Walls
        ///     - OST_Doors
        ///   not_all:
        ///     - OST_TextNotes
        /// </code>
        /// </remarks>
        public List<ContextRule> ContextRules { get; set; } = new List<ContextRule>();
        
        /// <summary>
        /// Gets the formatted context string for runtime consumption.
        /// </summary>
        /// <returns>
        /// A context string formatted according to pyRevit runtime expectations:
        /// - "(item1&amp;item2)" for ALL conditions (list format)
        /// - "(item1|item2)" for ANY conditions
        /// - "(item1;item2)" for EXACT conditions
        /// - "!(rule)" for NOT conditions
        /// </returns>
        public string GetFormattedContext()
        {
            // If we have context rules, format them
            if (ContextRules != null && ContextRules.Count > 0)
            {
                var formattedRules = new List<string>();
                foreach (var rule in ContextRules)
                {
                    formattedRules.Add(rule.ToFormattedString());
                }
                // Join multiple rules with & (ALL)
                return string.Join("&", formattedRules);
            }
            
            // If we have context items (list format), join with & (ALL must match)
            if (ContextItems != null && ContextItems.Count > 0)
            {
                return "(" + string.Join("&", ContextItems) + ")";
            }
            
            // Simple string context - wrap in parentheses if not already
            if (!string.IsNullOrEmpty(Context))
            {
                if (Context.StartsWith("(") && Context.EndsWith(")"))
                    return Context;
                return "(" + Context + ")";
            }
            
            // No context defined - return null (button always available, no availability class needed)
            return null;
        }

        /// <summary>
        /// Gets or sets the URL hyperlink associated with this bundle.
        /// </summary>
        /// <remarks>
        /// When specified, the command button can display a hyperlink icon or
        /// provide context menu access to open the URL.
        /// </remarks>
        public string Hyperlink { get; set; }

        /// <summary>
        /// Gets or sets the highlight color for this bundle's button.
        /// </summary>
        /// <remarks>
        /// <para>Supported values: color names or hex codes (e.g., "#FF5733")</para>
        /// <para>Used to visually emphasize important or frequently-used commands.</para>
        /// </remarks>
        public string Highlight { get; set; }

        /// <summary>
        /// Gets or sets the background color for the panel containing this bundle.
        /// </summary>
        /// <remarks>
        /// Format: Hex color code (e.g., "#BB005591")
        /// Can be specified inline or as part of a background section.
        /// </remarks>
        public string PanelBackground { get; set; }

        /// <summary>
        /// Gets or sets the background color for the title bar of this bundle's panel.
        /// </summary>
        /// <remarks>
        /// Part of multi-line background configuration. Format: Hex color code.
        /// </remarks>
        public string TitleBackground { get; set; }

        /// <summary>
        /// Gets or sets the background color for slideout panels.
        /// </summary>
        /// <remarks>
        /// Used when the bundle creates a slideout or pulldown menu.
        /// Format: Hex color code.
        /// </remarks>
        public string SlideoutBackground { get; set; }

        /// <summary>
        /// Gets or sets the engine configuration settings for script execution.
        /// </summary>
        /// <remarks>
        /// <para>Controls how the script engine behaves when executing this command:</para>
        /// <list type="bullet">
        /// <item><description>Threading model (main thread vs. background)</description></item>
        /// <item><description>Engine scope (clean vs. persistent)</description></item>
        /// <item><description>Dynamo-specific settings</description></item>
        /// </list>
        /// </remarks>
        public EngineConfig Engine { get; set; } = new EngineConfig();

        /// <summary>
        /// Gets or sets the path to the compiled assembly for invoke-type commands.
        /// </summary>
        /// <remarks>
        /// <para>Used for commands implemented as compiled .NET assemblies instead of scripts.</para>
        /// <para>The path can be absolute or relative to the bundle directory.</para>
        /// <para>Supports both .dll and .exe files.</para>
        /// </remarks>
        /// <example>
        /// <code>assembly: "bin/MyCommand.dll"</code>
        /// </example>
        public string Assembly { get; set; }

        /// <summary>
        /// Gets or sets the fully-qualified class name containing the IExternalCommand implementation.
        /// </summary>
        /// <remarks>
        /// <para>Required for invoke-type commands. Format: "Namespace.ClassName"</para>
        /// <para>The class must implement Autodesk.Revit.UI.IExternalCommand interface.</para>
        /// </remarks>
        /// <example>
        /// <code>command_class: "MyExtension.Commands.MyCommand"</code>
        /// </example>
        public string CommandClass { get; set; }

        /// <summary>
        /// Gets or sets the fully-qualified class name for command availability checking.
        /// </summary>
        /// <remarks>
        /// <para>Optional. Format: "Namespace.ClassName"</para>
        /// <para>The class must implement Autodesk.Revit.UI.IExternalCommandAvailability interface.</para>
        /// <para>Used to dynamically enable/disable commands based on Revit's current state.</para>
        /// </remarks>
        /// <example>
        /// <code>availability_class: "MyExtension.Availability.MyCommandAvailability"</code>
        /// </example>
        public string AvailabilityClass { get; set; }

        /// <summary>
        /// Gets or sets the list of additional module names to load for this command.
        /// </summary>
        /// <remarks>
        /// <para>Modules are typically .dll files that provide additional functionality.</para>
        /// <para>They are loaded into the script engine's scope before command execution.</para>
        /// <para>Useful for sharing code between multiple commands or loading third-party libraries.</para>
        /// </remarks>
        /// <example>
        /// <code>
        /// modules:
        ///   - "MySharedLibrary.dll"
        ///   - "ThirdPartyLib.dll"
        /// </code>
        /// </example>
        public List<string> Modules { get; set; } = new List<string>();

        /// <summary>
        /// Gets or sets the list of members for ComboBox controls.
        /// </summary>
        /// <remarks>
        /// <para>Only applicable for .combobox bundles.</para>
        /// <para>Each member defines an option in the ComboBox dropdown.</para>
        /// </remarks>
        /// <example>
        /// <code>
        /// members:
        ///   - id: "one"
        ///     text: "Option One"
        ///   - id: "two"
        ///     text: "Option Two"
        /// </code>
        /// </example>
        public List<ComboBoxMember> Members { get; set; } = new List<ComboBoxMember>();

        /// <summary>
        /// Gets or sets template variables for liquid tag substitution.
        /// </summary>
        /// <remarks>
        /// <para>Template variables can be used in child components using the {{variable}} syntax.</para>
        /// <para>Variables defined in parent bundles are passed down to children.</para>
        /// <para>Any top-level key that doesn't match a known property is treated as a template variable.</para>
        /// </remarks>
        /// <example>
        /// <code>
        /// template_test: "My custom value"
        /// author: "John Doe"
        /// docpath: "https://example.com/docs"
        /// </code>
        /// These can be used in child bundles:
        /// <code>
        /// tooltip: "Documentation: {{docpath}}"
        /// authors:
        ///   - "{{author}}"
        /// </code>
        /// </example>
        public Dictionary<string, string> Templates { get; set; } = new Dictionary<string, string>();

        /// <summary>
        /// Gets or sets the content file path for .content bundles.
        /// </summary>
        /// <remarks>
        /// <para>Used for content-type bundles (.content) that import Revit families (.rfa).</para>
        /// <para>The path can be absolute or relative to the bundle directory.</para>
        /// <para>Relative paths support parent directory navigation (e.g., "..\A.rfa").</para>
        /// </remarks>
        /// <example>
        /// <code>content: "A.rfa"</code>
        /// <code>content: "..\A.rfa"</code>
        /// <code>content: "C:\Families\MyFamily.rfa"</code>
        /// </example>
        public string Content { get; set; }

        /// <summary>
        /// Gets or sets the alternative content file path for .content bundles.
        /// </summary>
        /// <remarks>
        /// <para>Alternative content is loaded when the user invokes the command with CTRL+Click.</para>
        /// <para>The path can be absolute or relative to the bundle directory.</para>
        /// <para>If not specified, defaults to the same file as Content.</para>
        /// </remarks>
        /// <example>
        /// <code>content_alt: "B.rfa"</code>
        /// </example>
        public string ContentAlt { get; set; }
    }
}
