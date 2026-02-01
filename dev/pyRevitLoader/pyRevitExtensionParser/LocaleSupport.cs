using System;
using System.Collections.Generic;

namespace pyRevitExtensionParser
{
    internal static class LocaleSupport
    {
        private static readonly HashSet<string> SupportedLocales = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "en_us",
            "de_de",
            "es_es",
            "fr_fr",
            "it_it",
            "nl_nl",
            "nl_be",
            "chinese_s",
            "chinese_t",
            "ja",
            "ko",
            "ru",
            "cs",
            "pl",
            "hu",
            "pt_br",
            "pt_pt",
            "en_gb",
            "bg",
            "fa",
            "ar",
            "uk",
        };

        internal static bool IsSupportedLocale(string localeKey)
        {
            if (string.IsNullOrEmpty(localeKey))
                return false;

            return SupportedLocales.Contains(localeKey);
        }

        internal static string NormalizeLocaleKey(string localeKey)
        {
            if (!IsSupportedLocale(localeKey))
                return null;

            return localeKey.ToLowerInvariant();
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
    }
}
