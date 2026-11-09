using System;
using System.Collections.Generic;

namespace PyRevitLoader
{
    /// <summary>
    /// Process-wide slots that let each session load release what the previous session load
    /// left behind under the same name.
    /// </summary>
    /// <remarks>
    /// Every session load brings its own copy of the loader assembly, so a static in that copy
    /// never sees the previous one. The slots therefore live in AppDomain data, are locked on
    /// the shared dictionary instance itself, and hold plain <see cref="Action"/> delegates
    /// that any copy can invoke.
    /// </remarks>
    public static class SessionResourceRegistry
    {
        private const string SlotsKey = "PYREVITSessionResourceSlots";

        /// <summary>
        /// Stores <paramref name="release"/> under <paramref name="slotName"/> and runs the
        /// release that a previous session load stored there, if any.
        /// </summary>
        /// <param name="slotName">Name of the resource, shared by every session load.</param>
        /// <param name="release">Releases the resources of the calling session load.</param>
        /// <param name="onError">Receives the failure of the previous release, if it threw.</param>
        /// <remarks>
        /// Important: a failing previous release is reported through <paramref name="onError"/>
        /// and swallowed so that the current session load can always continue.
        /// </remarks>
        public static void Replace(string slotName, Action release, Action<string> onError = null)
        {
            Action previous;
            var slots = GetSlots();
            lock (slots)
            {
                slots.TryGetValue(slotName, out previous);
                slots[slotName] = release;
            }

            if (previous == null)
                return;

            try
            {
                previous();
            }
            catch (Exception ex)
            {
                onError?.Invoke($"Releasing previous '{slotName}' resources failed: {ex.Message}");
            }
        }

        private static Dictionary<string, Action> GetSlots()
        {
            var existing = AppDomain.CurrentDomain.GetData(SlotsKey) as Dictionary<string, Action>;
            if (existing != null)
                return existing;

            var created = new Dictionary<string, Action>();
            AppDomain.CurrentDomain.SetData(SlotsKey, created);
            return created;
        }
    }
}
