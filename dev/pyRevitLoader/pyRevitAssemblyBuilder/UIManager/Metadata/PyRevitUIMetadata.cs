using System;

namespace pyRevitAssemblyBuilder.UIManager.Metadata
{
    /// <summary>
    /// Base metadata for all pyRevit UI elements.
    /// Stores tracking information for cleanup during extension reloads.
    /// Mirrors the Python GenericPyRevitUIContainer's dirty flag mechanism.
    /// </summary>
    public class PyRevitUIMetadata
    {
        /// <summary>
        /// Whether this UI element was touched during the current reload.
        /// False = element exists but wasn't updated (orphaned candidate)
        /// True = element was created or updated in current session
        /// </summary>
        public bool IsDirty { get; set; } = false;
        
        /// <summary>
        /// Name of the extension that created this UI element.
        /// Used to track which extension owns which UI elements.
        /// </summary>
        public string ExtensionName { get; set; } = string.Empty;
        
        /// <summary>
        /// Path to the assembly that provides this UI element.
        /// Used to verify assembly changes during updates.
        /// </summary>
        public string AssemblyPath { get; set; } = string.Empty;
        
        /// <summary>
        /// Component unique identifier from ParsedComponent.UniqueId.
        /// Used for precise element matching.
        /// </summary>
        public string ComponentUniqueId { get; set; } = string.Empty;
        
        /// <summary>
        /// Timestamp when this element was created or last updated.
        /// </summary>
        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    }
    
    /// <summary>
    /// Metadata specifically for ribbon tabs.
    /// </summary>
    public class PyRevitTabMetadata : PyRevitUIMetadata
    {
        /// <summary>
        /// Identifier to confirm this is a pyRevit-managed tab.
        /// Must match UIManagerConstants.PyRevitTabIdentifier
        /// </summary>
        public const string PyRevitIdentifier = "pyrevit_tab";
    }
    
    /// <summary>
    /// Metadata for ribbon panels.
    /// </summary>
    public class PyRevitPanelMetadata : PyRevitUIMetadata
    {
        /// <summary>
        /// Parent tab name for this panel.
        /// </summary>
        public string TabName { get; set; } = string.Empty;
    }
    
    /// <summary>
    /// Metadata for ribbon buttons and other items.
    /// </summary>
    public class PyRevitButtonMetadata : PyRevitUIMetadata
    {
        /// <summary>
        /// Parent tab name for this button.
        /// </summary>
        public string TabName { get; set; } = string.Empty;
        
        /// <summary>
        /// Parent panel name for this button.
        /// </summary>
        public string PanelName { get; set; } = string.Empty;
    }
}
