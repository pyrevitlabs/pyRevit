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
        /// Custom context rules
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
        /// The raw context string from bundle.yaml
        /// </summary>
        public string RawContext { get; set; }
        
        /// <summary>
        /// Whether this command is available when no document is open
        /// </summary>
        public bool IsZeroDocAvailable => ContextType == AvailabilityContext.ZeroDoc || RawContext == "zero-doc";
        
        /// <summary>
        /// Whether this command requires element selection
        /// </summary>
        public bool RequiresSelection => ContextType == AvailabilityContext.Selection || RawContext == "selection";
        
        /// <summary>
        /// Parses context string and returns appropriate CommandAvailability
        /// </summary>
        /// <param name="contextString">The context string from bundle.yaml</param>
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

            switch (contextString.ToLowerInvariant().Trim())
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
                    availability.ContextType = AvailabilityContext.Custom;
                    break;
            }

            return availability;
        }
    }
}