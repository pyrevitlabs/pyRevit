using System;
using System.Collections.Concurrent;
using System.Threading;
using System.Windows.Media.Imaging;

namespace pyRevitAssemblyBuilder.UIManager.Icons
{
    /// <summary>
    /// Thread-safe cache for bitmap images used in the Revit UI.
    /// Uses ConcurrentDictionary to support parallel icon pre-loading.
    /// </summary>
    public class BitmapCache
    {
        // Key format: "filepath|size"
        private readonly ConcurrentDictionary<string, BitmapSource> _cache = new ConcurrentDictionary<string, BitmapSource>();

        private int _hits;
        private int _misses;

        /// <summary>
        /// Tries to get a cached bitmap for the given path and size.
        /// </summary>
        /// <param name="imagePath">The path to the image file.</param>
        /// <param name="targetSize">The target size of the icon.</param>
        /// <param name="bitmap">The cached bitmap if found.</param>
        /// <returns>True if a cached bitmap was found, false otherwise.</returns>
        public bool TryGet(string imagePath, int targetSize, out BitmapSource bitmap)
        {
            var key = BuildKey(imagePath, targetSize);
            if (_cache.TryGetValue(key, out bitmap))
            {
                Interlocked.Increment(ref _hits);
                return true;
            }

            Interlocked.Increment(ref _misses);
            return false;
        }

        /// <summary>
        /// Returns the accumulated (hits, misses) counters since the last reset and clears them.
        /// Used by per-extension instrumentation to attribute cache behaviour to a single
        /// <c>BuildUI</c> window.
        /// </summary>
        public (int Hits, int Misses) ResetAndGetStats()
        {
            var hits = Interlocked.Exchange(ref _hits, 0);
            var misses = Interlocked.Exchange(ref _misses, 0);
            return (hits, misses);
        }

        /// <summary>
        /// Adds or updates a bitmap in the cache.
        /// </summary>
        /// <param name="imagePath">The path to the image file.</param>
        /// <param name="targetSize">The target size of the icon.</param>
        /// <param name="bitmap">The bitmap to cache.</param>
        public void Set(string imagePath, int targetSize, BitmapSource bitmap)
        {
            if (bitmap == null)
                return;

            var key = BuildKey(imagePath, targetSize);
            _cache.TryAdd(key, bitmap);
        }

        /// <summary>
        /// Clears all cached bitmaps.
        /// </summary>
        public void Clear()
        {
            _cache.Clear();
        }

        /// <summary>
        /// Gets the number of cached items.
        /// </summary>
        public int Count => _cache.Count;

        /// <summary>
        /// Builds the cache key from path and size.
        /// </summary>
        private static string BuildKey(string imagePath, int targetSize)
        {
            return $"{imagePath}|{targetSize}";
        }
    }
}
