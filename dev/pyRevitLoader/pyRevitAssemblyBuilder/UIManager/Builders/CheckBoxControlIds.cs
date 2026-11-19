#nullable enable

namespace pyRevitAssemblyBuilder.UIManager.Builders
{
    /// <summary>
    /// Builds the AdWindows ids of .checkbox controls and of the row panels that stack them.
    /// </summary>
    /// <remarks>
    /// Important: keep this class free of AdWindows and Revit API types, so the ids are tested
    /// without Revit.
    /// Invariant: reloads find a checkbox's control and a stack's row panel by these ids, and
    /// <see cref="RibbonScanner"/> tracks checkboxes by them. A stacked checkbox's id also names its
    /// stack, so it never matches a standalone checkbox with the same name in the same panel, and a
    /// row panel's id never matches a checkbox's id.
    /// </remarks>
    internal static class CheckBoxControlIds
    {
        private const string ControlIdPrefix = "pyRevitCheckBox";
        private const string StackIdPrefix = "pyRevitCheckBoxStack";

        internal static string ForCheckBox(string tabName, string panelName, string displayName)
        {
            return $"{ControlIdPrefix}%{tabName}%{panelName}%{displayName}";
        }

        internal static string ForStack(string tabName, string panelName, string stackDisplayName)
        {
            return $"{StackIdPrefix}%{tabName}%{panelName}%{stackDisplayName}";
        }

        internal static string ForStackedCheckBox(string tabName, string panelName, string stackDisplayName, string displayName)
        {
            return $"{ControlIdPrefix}%{tabName}%{panelName}%{stackDisplayName}%{displayName}";
        }
    }
}
