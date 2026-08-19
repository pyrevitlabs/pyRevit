using System;
using System.Collections.Generic;
using System.Runtime.CompilerServices;

namespace pyRevitAssemblyBuilder.UIManager.Icons
{
    /// <summary>
    /// Retains the icon update operation for each live ribbon control so theme changes can be
    /// applied without rebuilding the pyRevit session.
    /// </summary>
    public static class RibbonIconRegistry
    {
        private static readonly object SyncRoot = new object();
        private static readonly Dictionary<object, Action<bool>> RefreshActions =
            new Dictionary<object, Action<bool>>(ReferenceComparer.Instance);

        /// <summary>
        /// Registers or replaces the theme-aware icon updater for a ribbon control.
        /// </summary>
        public static void Register(object item, Action<bool> refreshAction)
        {
            if (item == null || refreshAction == null)
                return;

            lock (SyncRoot)
            {
                RefreshActions[item] = refreshAction;
            }
        }

        /// <summary>
        /// Reapplies icons to all registered ribbon controls for the active theme.
        /// </summary>
        public static void RefreshAll(bool isDarkTheme)
        {
            Action<bool>[] actions;
            lock (SyncRoot)
            {
                actions = new Action<bool>[RefreshActions.Count];
                RefreshActions.Values.CopyTo(actions, 0);
            }

            foreach (var refreshAction in actions)
            {
                try
                {
                    refreshAction(isDarkTheme);
                }
                catch
                {
                    // A stale ribbon control must not prevent the remaining icons from updating.
                }
            }
        }

        /// <summary>
        /// Removes registrations from the previous session before the ribbon is rebuilt.
        /// </summary>
        public static void Clear()
        {
            lock (SyncRoot)
            {
                RefreshActions.Clear();
            }
        }

        internal static int Count
        {
            get
            {
                lock (SyncRoot)
                {
                    return RefreshActions.Count;
                }
            }
        }

        private sealed class ReferenceComparer : IEqualityComparer<object>
        {
            public static readonly ReferenceComparer Instance = new ReferenceComparer();

            public new bool Equals(object x, object y) => ReferenceEquals(x, y);

            public int GetHashCode(object obj) => RuntimeHelpers.GetHashCode(obj);
        }
    }
}
