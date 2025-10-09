using System.Collections.Generic;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParser
{
    public class ParsedComponent
    {
        public string Name { get; set; }
        public string DisplayName { get; set; }
        public string ScriptPath { get; set; }
        public string Tooltip { get; set; }
        public string UniqueId { get; set; }
        public CommandComponentType Type { get; set; }
        public List<ParsedComponent> Children { get; set; }
        public string BundleFile { get; set; }
        public List<string> LayoutOrder { get; set; }
        public bool HasSlideout { get; set; } = false;
        public string Title { get; set; }
        public string Author { get; set; }

        /// <summary>
        /// Collection of icon files associated with this component
        /// </summary>
        public ComponentIconCollection Icons { get; set; } = new ComponentIconCollection();

        /// <summary>
        /// Gets the primary icon for this component (convenience property)
        /// </summary>
        public ComponentIcon PrimaryIcon => Icons?.PrimaryIcon;

        /// <summary>
        /// Whether this component has any icons
        /// </summary>
        public bool HasIcons => Icons?.Count > 0;

        /// <summary>
        /// Whether this component has any valid (existing) icons
        /// </summary>
        public bool HasValidIcons => Icons?.HasValidIcons == true;
    }
}
