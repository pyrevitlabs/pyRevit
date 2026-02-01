#nullable enable
namespace pyRevitAssemblyBuilder.UIManager
{
    /// <summary>
    /// Service for scanning and managing pyRevit UI elements in the ribbon.
    /// Mirrors Python _PyRevitUI wrapper's functionality using a registry-based approach.
    ///
    /// The cleanup flow works as follows:
    /// 1. Before loading: Call ResetDirtyFlags() to mark all known pyRevit elements as "untouched"
    /// 2. During loading: UI builders call MarkElementTouched() for each created/updated element
    /// 3. After loading: Call CleanupOrphanedElements() to hide elements that weren't touched
    /// </summary>
    public interface IUIRibbonScanner
    {
        /// <summary>
        /// Resets dirty flags on all registered pyRevit UI elements.
        /// Called before loading extensions to mark all elements as potentially orphaned.
        /// </summary>
        void ResetDirtyFlags();

        /// <summary>
        /// Marks an element as touched/updated during this session.
        /// Elements not marked will be cleaned up as orphaned.
        /// </summary>
        /// <param name="elementType">Type of element: "tab", "panel", or "button"</param>
        /// <param name="elementId">Unique identifier for the element (typically the name/DisplayName)</param>
        /// <param name="parentId">Optional parent identifier (e.g., tab name for panels, panel name for buttons)</param>
        void MarkElementTouched(string elementType, string elementId, string? parentId = null);

        /// <summary>
        /// Finds and deactivates all pyRevit UI elements that weren't touched.
        /// Called after loading extensions to cleanup orphaned UI elements.
        /// Only affects elements that were previously registered via MarkElementTouched.
        /// </summary>
        void CleanupOrphanedElements();

        /// <summary>
        /// Resets panel backgrounds on all pyRevit panels.
        /// Called before loading extensions to clear previous background colors.
        /// </summary>
        void ResetPanelBackgrounds();

        /// <summary>
        /// Checks if an element with the given ID is registered as a pyRevit element.
        /// </summary>
        bool IsRegisteredElement(string elementType, string elementId);
    }
}
