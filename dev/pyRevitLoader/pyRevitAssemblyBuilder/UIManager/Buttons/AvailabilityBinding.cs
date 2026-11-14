#nullable enable

namespace pyRevitAssemblyBuilder.UIManager.Buttons
{
    /// <summary>
    /// Computes the availability class name to assign to a ribbon button.
    /// </summary>
    internal static class AvailabilityBinding
    {
        /// <summary>
        /// Returns the availability class name for a command, or null when the component has no context.
        /// </summary>
        /// <param name="commandClassName">Class name of the command the button is bound to.</param>
        /// <param name="context">The component context expression; empty when the button has none.</param>
        /// <returns>
        /// The availability class name, or null. Callers must not assign null or an empty string to
        /// <c>AvailabilityClassName</c>: Revit rejects both, so a context removed from a bundle is not cleared.
        /// </returns>
        public static string? ForContext(string commandClassName, string? context)
        {
            return string.IsNullOrEmpty(context) ? null : commandClassName + "_avail";
        }
    }
}
