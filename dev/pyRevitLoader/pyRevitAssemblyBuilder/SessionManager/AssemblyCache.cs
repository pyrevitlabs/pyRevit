using System;
using System.Collections.Generic;
using System.Reflection;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Static cache for frequently accessed assemblies to avoid repeated AppDomain scanning.
    /// AppDomain.GetAssemblies() is expensive and should be called minimally.
    /// </summary>
    public static class AssemblyCache
    {
        private static readonly object _lock = new object();
        private static readonly Dictionary<string, Assembly> _cache = new Dictionary<string, Assembly>(StringComparer.OrdinalIgnoreCase);
        private static bool _scanned;
        
        /// <summary>
        /// Scans AppDomain once and caches all assembly references.
        /// </summary>
        private static void EnsureScanned()
        {
            if (_scanned) return;
            
            lock (_lock)
            {
                if (_scanned) return;
                
                foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
                {
                    try
                    {
                        var name = assembly.GetName().Name;
                        if (!string.IsNullOrEmpty(name) && !_cache.ContainsKey(name))
                        {
                            _cache[name] = assembly;
                        }
                    }
                    catch
                    {
                        // Ignore assemblies that throw on GetName()
                    }
                }
                
                _scanned = true;
            }
        }
        
        /// <summary>
        /// Gets an assembly by exact name.
        /// </summary>
        public static Assembly GetByName(string name)
        {
            EnsureScanned();
            return _cache.TryGetValue(name, out var assembly) ? assembly : null;
        }
        
        /// <summary>
        /// Gets an assembly by prefix (e.g., "pyRevitLoader" matches "pyRevitLoader.2024").
        /// </summary>
        public static Assembly GetByPrefix(string prefix)
        {
            EnsureScanned();
            
            lock (_lock)
            {
                foreach (var kvp in _cache)
                {
                    if (kvp.Key.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                        return kvp.Value;
                }
            }
            return null;
        }
        
        /// <summary>
        /// Gets an assembly by substring match (e.g., "IronPython" matches "IronPython.dll").
        /// </summary>
        public static Assembly GetByContains(string substring, params string[] exclusions)
        {
            EnsureScanned();
            
            lock (_lock)
            {
                foreach (var kvp in _cache)
                {
                    if (kvp.Key.Contains(substring))
                    {
                        bool excluded = false;
                        foreach (var ex in exclusions)
                        {
                            if (kvp.Key.Contains(ex))
                            {
                                excluded = true;
                                break;
                            }
                        }
                        if (!excluded)
                            return kvp.Value;
                    }
                }
            }
            return null;
        }
        
        /// <summary>
        /// Adds a newly loaded assembly to the cache.
        /// </summary>
        public static void Add(Assembly assembly)
        {
            if (assembly == null) return;
            
            try
            {
                var name = assembly.GetName().Name;
                if (!string.IsNullOrEmpty(name))
                {
                    lock (_lock)
                    {
                        _cache[name] = assembly;
                    }
                }
            }
            catch
            {
                // Ignore
            }
        }
        
        /// <summary>
        /// Clears the cache (useful for reload scenarios).
        /// </summary>
        public static void Clear()
        {
            lock (_lock)
            {
                _cache.Clear();
                _scanned = false;
            }
        }
    }
}
