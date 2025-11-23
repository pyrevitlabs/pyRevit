using System.Collections.Generic;

namespace pyRevitExtensionParser
{
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
        /// <para>Common values:</para>
        /// <list type="bullet">
        /// <item><description>"zero-doc" - Available when no document is open</description></item>
        /// <item><description>"no-active-doc" - Available when no active document</description></item>
        /// <item><description>"project" - Available in project documents</description></item>
        /// <item><description>"family" - Available in family editor</description></item>
        /// <item><description>Custom availability class name</description></item>
        /// </list>
        /// </remarks>
        public string Context { get; set; }

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
    }
}
