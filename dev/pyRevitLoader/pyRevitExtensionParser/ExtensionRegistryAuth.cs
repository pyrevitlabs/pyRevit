using System;
using System.Collections.Generic;
using System.IO;
using pyRevitLabs.Json.Linq;

namespace pyRevitExtensionParser
{
    /// <summary>
    /// Reads extension authorization metadata from registry definition files
    /// (extensions.json and configured lookup sources), matching Python exts.extpackages.
    /// </summary>
    internal static class ExtensionRegistryAuth
    {
        internal const string RegistryFileName = "extensions.json";

        private static Dictionary<string, RegistryAuthEntry> _registryAuthByName;

        internal sealed class RegistryAuthEntry
        {
            public List<string> AuthorizedUsers { get; } = new List<string>();
            public List<string> AuthorizedGroups { get; } = new List<string>();
        }

        internal static void ClearCache()
        {
            _registryAuthByName = null;
        }

        internal static void ApplyRegistryAuthorization(
            string extDir,
            string folderName,
            string manifestName,
            ref List<string> authUsers,
            ref List<string> authGroups)
        {
            if (string.IsNullOrWhiteSpace(extDir))
                return;

            var lookupNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            if (!string.IsNullOrWhiteSpace(folderName))
                lookupNames.Add(folderName);
            if (!string.IsNullOrWhiteSpace(manifestName))
                lookupNames.Add(manifestName);

            if (lookupNames.Count == 0)
                return;

            EnsureRegistryCache(extDir);

            foreach (var lookupName in lookupNames)
            {
                if (!_registryAuthByName.TryGetValue(lookupName, out var entry))
                    continue;

                MergeAuthList(ref authUsers, entry.AuthorizedUsers);
                MergeAuthList(ref authGroups, entry.AuthorizedGroups);
            }
        }

        private static void EnsureRegistryCache(string extDir)
        {
            if (_registryAuthByName != null)
                return;

            // Populate a local map and publish it last: collecting the source paths
            // reads config, which can clear this cache re-entrantly (e.g. a locale
            // change during parsing), and that must not leave the field null.
            var cache = new Dictionary<string, RegistryAuthEntry>(StringComparer.OrdinalIgnoreCase);

            foreach (var sourcePath in CollectDefinitionSourcePaths(extDir))
            {
                LoadRegistryAuthFromFile(sourcePath, cache);
            }

            _registryAuthByName = cache;
        }

        internal static IEnumerable<string> CollectDefinitionSourcePaths(string extDir)
        {
            var paths = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            if (!string.IsNullOrWhiteSpace(extDir))
            {
                var fullExtDir = Path.GetFullPath(extDir);
                foreach (var root in ExtensionParser.GetExtensionRootsForAuthLookup())
                {
                    if (IsUnderRoot(fullExtDir, root))
                    {
                        paths.Add(Path.Combine(Path.GetFullPath(root), RegistryFileName));
                    }
                }

                var parentDir = Path.GetDirectoryName(fullExtDir);
                if (!string.IsNullOrEmpty(parentDir))
                {
                    paths.Add(Path.Combine(parentDir, RegistryFileName));
                }
            }
            else
            {
                foreach (var root in ExtensionParser.GetExtensionRootsForAuthLookup())
                {
                    paths.Add(Path.Combine(Path.GetFullPath(root), RegistryFileName));
                }
            }

            foreach (var source in ExtensionParser.GetExtensionLookupSources())
            {
                if (string.IsNullOrWhiteSpace(source))
                    continue;

                try
                {
                    var expanded = Environment.ExpandEnvironmentVariables(source.Trim());
                    paths.Add(Path.GetFullPath(expanded));
                }
                catch
                {
                    // Ignore invalid configured lookup source paths.
                }
            }

            return paths;
        }

        private static void LoadRegistryAuthFromFile(
            string filePath,
            Dictionary<string, RegistryAuthEntry> cache)
        {
            if (!ExtensionParser.FileExistsForAuthLookup(filePath))
                return;

            try
            {
                var jsonContent = File.ReadAllText(filePath);
                var json = JObject.Parse(jsonContent);
                foreach (var entry in EnumerateRegistryEntries(json))
                {
                    var name = entry["name"]?.ToString();
                    if (string.IsNullOrWhiteSpace(name))
                        continue;

                    var users = ParseStringArray(entry["authusers"]);
                    var groups = ParseStringArray(entry["authgroups"]);
                    if (users.Count == 0 && groups.Count == 0)
                        continue;

                    if (!cache.TryGetValue(name, out var authEntry))
                    {
                        authEntry = new RegistryAuthEntry();
                        cache[name] = authEntry;
                    }

                    MergeAuthList(authEntry.AuthorizedUsers, users);
                    MergeAuthList(authEntry.AuthorizedGroups, groups);
                }
            }
            catch (Exception ex)
            {
                ExtensionParser.LogParseExceptionForAuthLookup(filePath, ex);
            }
        }

        private static IEnumerable<JObject> EnumerateRegistryEntries(JObject json)
        {
            var extensionsArray = json["extensions"] as JArray;
            if (extensionsArray != null)
            {
                foreach (var item in extensionsArray)
                {
                    if (item is JObject entry)
                        yield return entry;
                }

                yield break;
            }

            yield return json;
        }

        private static List<string> ParseStringArray(JToken token)
        {
            var values = new List<string>();
            var array = token as JArray;
            if (array == null)
                return values;

            foreach (var item in array)
            {
                var value = item?.ToString();
                if (!string.IsNullOrWhiteSpace(value))
                    values.Add(value);
            }

            return values;
        }

        private static void MergeAuthList(ref List<string> target, List<string> source)
        {
            if (source == null || source.Count == 0)
                return;

            if (target == null)
                target = new List<string>();

            MergeAuthList(target, source);
        }

        private static void MergeAuthList(List<string> target, List<string> source)
        {
            foreach (var value in source)
            {
                if (!target.Exists(x => string.Equals(x, value, StringComparison.OrdinalIgnoreCase)))
                    target.Add(value);
            }
        }

        private static bool IsUnderRoot(string fullPath, string root)
        {
            var fullRoot = Path.GetFullPath(root);
            if (!fullRoot.EndsWith(Path.DirectorySeparatorChar.ToString()))
                fullRoot += Path.DirectorySeparatorChar;

            return fullPath.StartsWith(fullRoot, StringComparison.OrdinalIgnoreCase);
        }
    }
}
