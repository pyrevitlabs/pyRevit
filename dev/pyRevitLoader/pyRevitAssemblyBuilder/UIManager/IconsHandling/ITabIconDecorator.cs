#nullable enable
using Autodesk.Windows;

namespace pyRevitAssemblyBuilder.UIManager.Icons
{
    /// <summary>
    /// Shows a bundle-provided icon before the title of a ribbon tab.
    /// </summary>
    /// <remarks>
    /// Call order per session load: <see cref="Reset"/> before the UI is built,
    /// <see cref="TryAddIcons"/> for each tab bundle, then <see cref="RefreshHeaders"/> once after the
    /// build.
    /// Must be called on the UI thread.
    /// </remarks>
    public interface ITabIconDecorator
    {
        /// <summary>
        /// Starts a new session: forgets every tab icon and makes this decorator the one that
        /// decorates tab headers.
        /// </summary>
        void Reset();

        /// <summary>
        /// Returns the tab bundle directory whose icons the tab shows this session, or <c>null</c>
        /// when the tab has no icon yet.
        /// </summary>
        string? GetIconSource(RibbonTab tab);

        /// <summary>
        /// Records the icons of a tab bundle for a tab. The first tab bundle with an icon wins: when
        /// several extensions contribute the same tab, later calls for that tab are ignored until
        /// <see cref="Reset"/>.
        /// </summary>
        /// <param name="tab">The ribbon tab.</param>
        /// <param name="iconSource">The tab bundle directory the icons come from.</param>
        /// <param name="lightIconPath">Icon for the light theme.</param>
        /// <param name="darkIconPath">Icon for the dark theme.</param>
        /// <returns><c>true</c> when the icons were recorded; <c>false</c> when the tab already has
        /// icons or neither file could be loaded.</returns>
        bool TryAddIcons(RibbonTab tab, string iconSource, string? lightIconPath, string? darkIconPath);

        /// <summary>
        /// Applies the recorded icons to every tab header that already exists, using the current
        /// Revit theme, and keeps them in sync with later theme changes. Headers created later are
        /// decorated as they load.
        /// </summary>
        void RefreshHeaders();
    }
}
