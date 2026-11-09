using System;
using System.Collections.Generic;
using System.Linq;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Revit-free rules for turning agent-supplied names into Revit objects and sizes.
    /// </summary>
    /// <remarks>
    /// Kept free of Revit API types so host-free tests can cover them.
    /// </remarks>
    internal static class AgentSelectors {
        /// <summary>
        /// Finds what a view selector names: the view with that id when the selector is an id
        /// of a view, otherwise every view whose name matches, ignoring case.
        /// </summary>
        /// <returns>
        /// No match, the single match, or several views sharing the name, which the caller must
        /// report as ambiguous instead of picking one.
        /// </returns>
        /// <remarks>
        /// A digits-only selector that is not a view id falls back to the name, so a view named
        /// "12345" stays reachable.
        /// </remarks>
        internal static List<T> FindView<T>(string selector, Func<long, T> byId, IEnumerable<T> views, Func<T, string> nameOf)
            where T : class {
            if (long.TryParse(selector, out var id) && byId(id) is T found)
                return new List<T> { found };
            return views.Where(view => string.Equals(nameOf(view), selector, StringComparison.OrdinalIgnoreCase)).ToList();
        }

        /// <summary>
        /// Parses one declared member name of <typeparamref name="TEnum"/>, ignoring case.
        /// </summary>
        /// <remarks>
        /// Rejects what <see cref="Enum.TryParse{TEnum}(string, bool, out TEnum)"/> accepts but
        /// does not name a single member: comma lists, which it ORs together, and numbers.
        /// </remarks>
        internal static bool TryParseMember<TEnum>(string name, out TEnum value) where TEnum : struct {
            value = default(TEnum);
            if (string.IsNullOrWhiteSpace(name) || name.Contains(","))
                return false;
            return Enum.TryParse(name, true, out value)
                && Enum.GetNames(typeof(TEnum)).Contains(name.Trim(), StringComparer.OrdinalIgnoreCase);
        }

        /// <summary>
        /// Reads an array of integer element ids.
        /// </summary>
        /// <exception cref="AgentException"><c>invalid_params</c> when an entry is not a JSON integer, so "329" and 1.5 are refused.</exception>
        internal static List<long> ParseIntegerIds(JArray ids, string name) {
            var result = new List<long>(ids.Count);
            foreach (var id in ids) {
                if (id.Type != JTokenType.Integer)
                    throw new AgentException("invalid_params", $"'{name}' must contain integer element ids.");
                try {
                    result.Add(id.Value<long>());
                }
                catch (Exception) {
                    throw new AgentException("invalid_params", $"'{name}' must contain integer element ids.");
                }
            }
            return result;
        }

        /// <summary>
        /// Parses category names into distinct members, bounding the number of distinct ones
        /// rather than the number of entries, so a repeated name counts once.
        /// </summary>
        /// <exception cref="AgentException"><c>invalid_params</c> for an unknown name or too many distinct members.</exception>
        internal static List<TEnum> ParseDistinctCategories<TEnum>(IEnumerable<string> names, int max) where TEnum : struct {
            var result = new List<TEnum>();
            foreach (var raw in names) {
                var name = raw ?? string.Empty;
                var enumName = name.StartsWith("OST_", StringComparison.OrdinalIgnoreCase) ? name : "OST_" + name;
                if (!TryParseMember(enumName, out TEnum category))
                    throw new AgentException("invalid_params", $"Unknown category '{name}'. Use BuiltInCategory names such as OST_Windows.");
                if (result.Contains(category))
                    continue;
                if (result.Count >= max)
                    throw new AgentException("invalid_params", $"At most {max} categories per call.");
                result.Add(category);
            }
            return result;
        }

        /// <summary>
        /// The height of an image scaled to <paramref name="scaledWidth"/>, keeping its aspect
        /// ratio and never below one pixel.
        /// </summary>
        internal static int ScaledHeight(int width, int height, int scaledWidth) =>
            Math.Max(1, (int)Math.Round(height * (scaledWidth / (double)width)));
    }
}
