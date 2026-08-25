using System;
using System.Collections.Generic;
using System.Linq;

namespace pyRevitExtensionParser
{
    internal static class LocaleSupport
    {
        private static readonly Dictionary<string, string> LocaleAliases =
            new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
            {
                ["en_us"] = "en_us",
                ["english"] = "en_us",
                ["de_de"] = "de_de",
                ["german"] = "de_de",
                ["es_es"] = "es_es",
                ["spanish"] = "es_es",
                ["fr_fr"] = "fr_fr",
                ["french"] = "fr_fr",
                ["it_it"] = "it_it",
                ["italian"] = "it_it",
                ["nl_nl"] = "nl_nl",
                ["nl_be"] = "nl_be",
                ["dutch"] = "nl_nl",
                ["chinese_s"] = "chinese_s",
                ["chinese_t"] = "chinese_t",
                ["chinese"] = "chinese_s",
                ["ja"] = "ja",
                ["japanese"] = "ja",
                ["ko"] = "ko",
                ["korean"] = "ko",
                ["ru"] = "ru",
                ["russian"] = "ru",
                ["cs"] = "cs",
                ["czech"] = "cs",
                ["pl"] = "pl",
                ["polish"] = "pl",
                ["hu"] = "hu",
                ["hungarian"] = "hu",
                ["pt_br"] = "pt_br",
                ["portuguese_brazil"] = "pt_br",
                ["brazilian"] = "pt_br",
                ["pt_pt"] = "pt_pt",
                ["portuguese"] = "pt_pt",
                ["en_gb"] = "en_gb",
                ["bg"] = "bg",
                ["bulgarian"] = "bg",
                ["fa"] = "fa",
                ["farsi"] = "fa",
                ["persian"] = "fa",
                ["ar"] = "ar",
                ["arabic"] = "ar",
                ["uk"] = "uk",
                ["ukrainian"] = "uk",
            };

        private static readonly Dictionary<string, string[]> LocaleGroups =
            new Dictionary<string, string[]>(StringComparer.OrdinalIgnoreCase)
            {
                ["en_us"] = new[] { "en_us", "english" },
                ["de_de"] = new[] { "de_de", "german" },
                ["es_es"] = new[] { "es_es", "spanish" },
                ["fr_fr"] = new[] { "fr_fr", "french" },
                ["it_it"] = new[] { "it_it", "italian" },
                ["nl_nl"] = new[] { "nl_nl", "dutch" },
                ["nl_be"] = new[] { "nl_be", "dutch" },
                ["chinese_s"] = new[] { "chinese_s", "chinese" },
                ["chinese_t"] = new[] { "chinese_t", "chinese" },
                ["ja"] = new[] { "ja", "japanese" },
                ["ko"] = new[] { "ko", "korean" },
                ["ru"] = new[] { "ru", "russian" },
                ["cs"] = new[] { "cs", "czech" },
                ["pl"] = new[] { "pl", "polish" },
                ["hu"] = new[] { "hu", "hungarian" },
                ["pt_br"] = new[] { "pt_br", "portuguese_brazil", "brazilian", "portuguese" },
                ["pt_pt"] = new[] { "pt_pt", "portuguese" },
                ["en_gb"] = new[] { "en_gb" },
                ["bg"] = new[] { "bg", "bulgarian" },
                ["fa"] = new[] { "fa", "farsi", "persian" },
                ["ar"] = new[] { "ar", "arabic" },
                ["uk"] = new[] { "uk", "ukrainian" },
            };

        internal static bool IsSupportedLocale(string localeKey)
        {
            if (string.IsNullOrEmpty(localeKey))
                return false;

            return LocaleAliases.ContainsKey(localeKey);
        }

        internal static string NormalizeLocaleKey(string localeKey)
        {
            if (string.IsNullOrEmpty(localeKey))
                return null;

            return LocaleAliases.TryGetValue(localeKey, out var canonical)
                ? canonical
                : null;
        }

        internal static Dictionary<string, string> NormalizeLocaleDict(Dictionary<string, string> localizedValues)
        {
            if (localizedValues == null || localizedValues.Count == 0)
                return localizedValues;

            var normalized = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            foreach (var kvp in localizedValues)
            {
                var key = NormalizeLocaleKey(kvp.Key);
                if (key == null)
                    continue;

                normalized[key] = kvp.Value;
            }

            return normalized.Count > 0 ? normalized : null;
        }

        internal static IEnumerable<string> GetLocaleSearchOrder(string preferredLocale, string defaultLocale)
        {
            var order = new List<string>();
            AddLocaleCandidates(order, preferredLocale);

            if (!string.Equals(preferredLocale, defaultLocale, StringComparison.OrdinalIgnoreCase))
                AddLocaleCandidates(order, defaultLocale);

            return order;
        }

        private static void AddLocaleCandidates(List<string> output, string localeOrAlias)
        {
            if (string.IsNullOrEmpty(localeOrAlias))
                return;

            var canonical = NormalizeLocaleKey(localeOrAlias) ?? localeOrAlias.ToLowerInvariant();
            if (!LocaleGroups.TryGetValue(canonical, out var candidates))
                candidates = new[] { canonical };

            foreach (var candidate in candidates.Select(x => x.ToLowerInvariant()))
            {
                if (!output.Contains(candidate))
                    output.Add(candidate);
            }
        }
    }
}
