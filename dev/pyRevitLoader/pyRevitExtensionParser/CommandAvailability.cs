namespace pyRevitExtensionParser
{
    /// <summary>
    /// Enum representing different context types for command availability
    /// </summary>
    public enum AvailabilityContext
    {
        /// <summary>
        /// No specific context - always available
        /// </summary>
        None,
        
        /// <summary>
        /// Available when no document is open (zero-doc)
        /// </summary>
        ZeroDoc,
        
        /// <summary>
        /// Available when elements are selected
        /// </summary>
        Selection,
        
        /// <summary>
        /// Available when in an active view
        /// </summary>
        ActiveView,
        
        /// <summary>
        /// Custom context rules (category filters, view types, etc.)
        /// </summary>
        Custom
    }

    /// <summary>
    /// Class representing command availability information
    /// </summary>
    public class CommandAvailability
    {
        /// <summary>
        /// The context type for this command
        /// </summary>
        public AvailabilityContext ContextType { get; set; } = AvailabilityContext.None;
        
        /// <summary>
        /// The raw context string from bundle.yaml (may be formatted with parentheses and operators)
        /// </summary>
        public string RawContext { get; set; }
        
        /// <summary>
        /// Whether this command is available when no document is open
        /// </summary>
        public bool IsZeroDocAvailable => ContextType == AvailabilityContext.ZeroDoc || 
            (RawContext != null && (RawContext == "zero-doc" || RawContext.Contains("zero-doc")));
        
        /// <summary>
        /// Whether this command requires element selection
        /// </summary>
        public bool RequiresSelection => ContextType == AvailabilityContext.Selection || 
            (RawContext != null && (RawContext == "selection" || RawContext.Contains("selection")));
        
        /// <summary>
        /// Whether this command has category-based context filters (OST_*)
        /// </summary>
        public bool HasCategoryFilter => RawContext != null && RawContext.Contains("OST_");
        
        /// <summary>
        /// Whether this command has view type context filters (active-*)
        /// </summary>
        public bool HasViewTypeFilter => RawContext != null && RawContext.Contains("active-");
        
        /// <summary>
        /// Whether this command has document type context filters (doc-*)
        /// </summary>
        public bool HasDocumentTypeFilter => RawContext != null && RawContext.Contains("doc-");
        
        /// <summary>
        /// Parses context string and returns appropriate CommandAvailability
        /// </summary>
        /// <param name="contextString">The context string from bundle.yaml (may include formatting)</param>
        /// <returns>CommandAvailability instance</returns>
        public static CommandAvailability FromContext(string contextString)
        {
            if (string.IsNullOrEmpty(contextString))
            {
                return new CommandAvailability();
            }

            var availability = new CommandAvailability
            {
                RawContext = contextString
            };

            // Strip parentheses for simple matching
            var cleanContext = contextString.Trim('(', ')').ToLowerInvariant().Trim();

            // Check for simple single-value contexts
            switch (cleanContext)
            {
                case "zero-doc":
                    availability.ContextType = AvailabilityContext.ZeroDoc;
                    break;
                case "selection":
                    availability.ContextType = AvailabilityContext.Selection;
                    break;
                case "active-view":
                    availability.ContextType = AvailabilityContext.ActiveView;
                    break;
                default:
                    // Check if it contains any complex rules or category names
                    if (contextString.Contains("&") || contextString.Contains("|") || 
                        contextString.Contains("OST_") || contextString.Contains("active-") ||
                        contextString.Contains("doc-"))
                    {
                        availability.ContextType = AvailabilityContext.Custom;
                    }
                    else
                    {
                        availability.ContextType = AvailabilityContext.Custom;
                    }
                    break;
            }

            return availability;
        }
    }
}