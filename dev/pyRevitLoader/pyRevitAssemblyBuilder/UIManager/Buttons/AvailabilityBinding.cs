#nullable enable
using Autodesk.Revit.UI;

namespace pyRevitAssemblyBuilder.UIManager.Buttons
{
    /// <summary>
    /// Computes the availability class name to assign when an existing ribbon button is rebound.
    /// </summary>
    internal static class AvailabilityBinding
    {
        /// <summary>
        /// Returns the value to assign to <c>AvailabilityClassName</c> on a reused button.
        /// </summary>
        /// <param name="commandClassName">Class name of the command the button is bound to.</param>
        /// <param name="context">The component context expression; empty when the button has none.</param>
        /// <returns>
        /// The availability class name when a context is defined, otherwise an empty string so a
        /// context removed from the bundle stops gating the button after a reload.
        /// </returns>
        public static string ForContext(string commandClassName, string? context)
        {
            return string.IsNullOrEmpty(context) ? string.Empty : commandClassName + "_avail";
        }

        /// <summary>
        /// Returns the value to assign to <c>AvailabilityClassName</c> given a resolved class name that may be absent.
        /// </summary>
        public static string ForResolved(string? availabilityClassName)
        {
            return availabilityClassName ?? string.Empty;
        }

        /// <summary>
        /// True when assigning <paramref name="desired"/> would change the button's availability class.
        /// </summary>
        /// <param name="current">The value currently set on the button; null and empty are equivalent.</param>
        /// <param name="desired">The value computed by <see cref="ForContext"/> or <see cref="ForResolved"/>.</param>
        public static bool NeedsUpdate(string? current, string desired)
        {
            return (current ?? string.Empty) != desired;
        }

        /// <summary>
        /// Assigns <paramref name="desired"/> to <c>AvailabilityClassName</c> only when it differs from
        /// the current value, so buttons that never had a context never hit the setter with an empty string.
        /// </summary>
        public static void Apply(PushButton button, string desired)
        {
            if (NeedsUpdate(button.AvailabilityClassName, desired))
                button.AvailabilityClassName = desired;
        }
    }
}
