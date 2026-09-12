using System;
using System.Collections.Concurrent;
using System.IO;
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
        private readonly struct Entry
        {
            public Entry(DateTime lastWriteUtc, BitmapSource bitmap)
            {
                LastWriteUtc = lastWriteUtc;
                Bitmap = bitmap;
            }

            public DateTime LastWriteUtc { get; }
            public BitmapSource Bitmap { get; }
        }

        // Key format: "filepath|size"
        private readonly ConcurrentDictionary<string, Entry> _cache = new ConcurrentDictionary<string, Entry>();

        private int _hits;
        private int _misses;

        /// <summary>
        /// Tries to get a cached bitmap for the given path and size. A cache entry whose file
        /// has been modified since it was cached counts as a miss, so a shared, process-lifetime
        /// cache (see <see cref="IconManager"/>) still picks up icons edited between reloads.
        /// </summary>
        /// <param name="imagePath">The path to the image file.</param>
        /// <param name="targetSize">The target size of the icon.</param>
        /// <param name="bitmap">The cached bitmap if found.</param>
        /// <returns>True if a cached bitmap was found, false otherwise.</returns>
        public bool TryGet(string imagePath, int targetSize, out BitmapSource bitmap)
        {
            var key = BuildKey(imagePath, targetSize);
            if (_cache.TryGetValue(key, out var entry))
            {
                if (entry.LastWriteUtc == File.GetLastWriteTimeUtc(imagePath))
                {
                    bitmap = entry.Bitmap;
                    Interlocked.Increment(ref _hits);
                    return true;
                }

                _cache.TryRemove(key, out _);
            }

            bitmap = null;
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
            _cache[key] = new Entry(File.GetLastWriteTimeUtc(imagePath), bitmap);
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
