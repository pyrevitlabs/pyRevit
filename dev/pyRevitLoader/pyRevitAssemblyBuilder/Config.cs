using System;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;

namespace pyRevitAssemblyBuilder.Config
{
    public class PyRevitConfig
    {
        public List<string> UserExtensions { get; } = new List<string>();

        public static PyRevitConfig Load(string configPath)
        {
            var config = new PyRevitConfig();

            if (!File.Exists(configPath))
                return config;

            string currentSection = "";
            foreach (var line in File.ReadAllLines(configPath))
            {
                var trimmed = line.Trim();

                if (string.IsNullOrEmpty(trimmed) || trimmed.StartsWith(";"))
                    continue;

                if (trimmed.StartsWith("[") && trimmed.EndsWith("]"))
                {
                    currentSection = trimmed.Trim('[', ']');
                }
                else if (currentSection == "core")
                {
                    var match = Regex.Match(trimmed, @"userextensions\s*=\s*\[(.*?)\]");
                    if (match.Success)
                    {
                        var list = match.Groups[1].Value;
                        var paths = Regex.Matches(list, "\"(.*?)\"");
                        foreach (Match p in paths)
                        {
                            config.UserExtensions.Add(p.Groups[1].Value);
                        }
                    }
                }
            }

            return config;
        }
    }
}