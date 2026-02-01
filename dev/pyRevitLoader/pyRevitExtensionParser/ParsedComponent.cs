using System.Collections.Generic;
using System.Linq;
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
        
        /// <summary>
        /// The control ID for this component, used to find the ribbon item.
        /// Format: "CustomCtrl_%CustomCtrl_%{tab}%{panel}%{group}%{button}"
        /// </summary>
        public string ControlId { get; set; }
        
        /// <summary>
        /// Maps component names (from layout items) to their custom display titles.
        /// Used when layout items specify a custom title like: "Component Name[title:Custom Title]"
        /// </summary>
        public Dictionary<string, string> LayoutItemTitles { get; set; }
        public bool HasSlideout { get; set; } = false;
        public string Title { get; set; }
        public string Author { get; set; }
        public string Context { get; set; }
        public string Hyperlink { get; set; }
        public string HelpUrl { get; set; }
        public string Highlight { get; set; }
        public string MinRevitVersion { get; set; }
        public string MaxRevitVersion { get; set; }
        public bool IsBeta { get; set; }
        public string TargetAssembly { get; set; }
        public string CommandClass { get; set; }
        public string AvailabilityClass { get; set; }
        public List<string> Modules { get; set; } = new List<string>();
        public EngineConfig Engine { get; set; }
        
        /// <summary>
        /// Path to the config script (config.py, config.cs, etc.) if it exists.
        /// When no separate config script exists, this equals ScriptPath.
        /// </summary>
        public string ConfigScriptPath { get; set; }
        
        /// <summary>
        /// Whether this component has a separate config script (config.py differs from script.py).
        /// Used to add the dot indicator (●) to button titles.
        /// </summary>
        public bool HasConfigScript => 
            !string.IsNullOrEmpty(ConfigScriptPath) && 
            !string.IsNullOrEmpty(ScriptPath) && 
            !string.Equals(ConfigScriptPath, ScriptPath, System.StringComparison.OrdinalIgnoreCase);
        
        /// <summary>
        /// Path to the "on" state icon for toggle/smart buttons.
        /// Used when the button is in the activated/on state.
        /// </summary>
        public string OnIconPath { get; set; }
        
        /// <summary>
        /// Path to the dark theme "on" state icon for toggle/smart buttons.
        /// </summary>
        public string OnIconDarkPath { get; set; }
        
        /// <summary>
        /// Path to the "off" state icon for toggle/smart buttons.
        /// Used when the button is in the deactivated/off state.
        /// </summary>
        public string OffIconPath { get; set; }
        
        /// <summary>
        /// Path to the dark theme "off" state icon for toggle/smart buttons.
        /// </summary>
        public string OffIconDarkPath { get; set; }
        
        /// <summary>
        /// Whether this component has on/off state icons for toggle functionality.
        /// </summary>
        public bool HasToggleIcons => 
            !string.IsNullOrEmpty(OnIconPath) || !string.IsNullOrEmpty(OffIconPath);
        
        /// <summary>
        /// Path to the tooltip media file (tooltip.mp4, tooltip.swf, or tooltip.png).
        /// Used for video or image tooltips on buttons.
        /// </summary>
        public string MediaFile { get; set; }
        
        /// <summary>
        /// Whether this component has a tooltip media file.
        /// </summary>
        public bool HasMediaFile => !string.IsNullOrEmpty(MediaFile);
        
        /// <summary>
        /// Panel background color (ARGB hex format, e.g., '#BB005591')
        /// </summary>
        public string PanelBackground { get; set; }
        
        /// <summary>
        /// Panel title background color (ARGB hex format, e.g., '#E2A000')
        /// </summary>
        public string TitleBackground { get; set; }
        
        /// <summary>
        /// Panel slideout background color (ARGB hex format, e.g., '#E25200')
        /// </summary>
        public string SlideoutBackground { get; set; }
        
        /// <summary>
        /// The directory path where this component resides
        /// </summary>
        public string Directory { get; set; }

        /// <summary>
        /// Parsed availability information for this component
        /// </summary>
        public CommandAvailability Availability => CommandAvailability.FromContext(Context);

        /// <summary>
        /// Collection of icon files associated with this component
        /// </summary>
        public ComponentIconCollection Icons { get; set; } = new ComponentIconCollection();

        /// <summary>
        /// Localized titles from bundle.yaml (locale -> title)
        /// </summary>
        public Dictionary<string, string> LocalizedTitles { get; set; }

        /// <summary>
        /// Localized tooltips from bundle.yaml (locale -> tooltip)
        /// </summary>
        public Dictionary<string, string> LocalizedTooltips { get; set; }

        /// <summary>
        /// Localized help URLs from bundle.yaml (locale -> help URL)
        /// </summary>
        public Dictionary<string, string> LocalizedHelpUrls { get; set; } = new Dictionary<string, string>();

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

        /// <summary>
        /// Whether this component has localized content
        /// </summary>
        public bool HasLocalizedContent =>
            (LocalizedTitles?.Count > 0) || (LocalizedTooltips?.Count > 0);

        /// <summary>
        /// Gets available locales for this component
        /// </summary>
        public IEnumerable<string> AvailableLocales
        {
            get
            {
                var locales = new HashSet<string>();
                if (LocalizedTitles != null)
                {
                    foreach (var locale in LocalizedTitles.Keys)
                        locales.Add(locale);
                }
                if (LocalizedTooltips != null)
                {
                    foreach (var locale in LocalizedTooltips.Keys)
                        locales.Add(locale);
                }
                return locales;
            }
        }

        /// <summary>
        /// List of members for ComboBox controls.
        /// </summary>
        /// <remarks>
        /// Only populated for components of type ComboBox.
        /// Each member represents an option in the dropdown.
        /// </remarks>
        public List<ComboBoxMember> Members { get; set; } = new List<ComboBoxMember>();

        /// <summary>
        /// Gets the localized title for the specified locale, with fallback logic
        /// </summary>
        /// <param name="locale">The preferred locale (e.g., "en_us", "fr_fr")</param>
        /// <returns>The localized title or null if not available</returns>
        public string GetLocalizedTitle(string locale = null)
        {
            return GetLocalizedValue(LocalizedTitles, locale) ?? Title;
        }

        /// <summary>
        /// Gets the localized tooltip for the specified locale, with fallback logic
        /// </summary>
        /// <param name="locale">The preferred locale (e.g., "en_us", "fr_fr")</param>
        /// <returns>The localized tooltip or null if not available</returns>
        public string GetLocalizedTooltip(string locale = null)
        {
            return GetLocalizedValue(LocalizedTooltips, locale) ?? Tooltip;
        }

        /// <summary>
        /// Gets the localized help URL for the specified locale, with fallback logic
        /// </summary>
        /// <param name="locale">The preferred locale (e.g., "en_us", "fr_fr")</param>
        /// <returns>The localized help URL or null if not available</returns>
        public string GetLocalizedHelpUrl(string locale = null)
        {
            return GetLocalizedValue(LocalizedHelpUrls, locale) ?? HelpUrl;
        }

        /// <summary>
        /// Helper method to get localized value with fallback logic
        /// </summary>
        private string GetLocalizedValue(Dictionary<string, string> localizedValues, string preferredLocale = null)
        {
            if (localizedValues == null || localizedValues.Count == 0)
                return null;

            // Use ExtensionParser's default locale if no preferred locale specified
            if (string.IsNullOrEmpty(preferredLocale))
                preferredLocale = ExtensionParser.DefaultLocale;

            // Try preferred locale first
            if (localizedValues.TryGetValue(preferredLocale, out string preferredValue))
                return preferredValue;

            // Fallback to default locale if different preferred locale was specified
            if (preferredLocale != ExtensionParser.DefaultLocale && localizedValues.TryGetValue(ExtensionParser.DefaultLocale, out string defaultValue))
                return defaultValue;

            // Fallback to first available value
            return localizedValues.Values.FirstOrDefault();
        }
    }
}
