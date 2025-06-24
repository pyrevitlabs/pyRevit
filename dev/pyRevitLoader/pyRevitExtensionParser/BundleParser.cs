using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace pyRevitExtensionParser
{
    class BundleParser
    {
        public class ParsedBundle
        {
            public List<string> LayoutOrder { get; set; } = new List<string>();
            public Dictionary<string, string> Titles { get; set; } = new Dictionary<string, string>();
            public Dictionary<string, string> Tooltips { get; set; } = new Dictionary<string, string>();
            public string Author { get; set; }
            public string MinRevitVersion { get; set; }
            public EngineConfig Engine { get; set; } = new EngineConfig();
        }

        public static class BundleYamlParser
        {
            public static ParsedBundle Parse(string filePath)
            {
                var parsed = new ParsedBundle();
                var lines = File.ReadAllLines(filePath);
                string currentSection = null;

                foreach (var raw in lines)
                {
                    // Trim both leading and trailing whitespace to simplify checks
                    var line = raw.Trim();
                    if (string.IsNullOrWhiteSpace(line))
                        continue;

                    // Top‐level section header (no leading spaces)
                    if (!raw.StartsWith(" ") && line.Contains(":"))
                    {
                        var parts = line.Split(new[] { ':' }, 2);
                        currentSection = parts[0].Trim().ToLowerInvariant();
                        var value = parts[1].Trim();

                        switch (currentSection)
                        {
                            case "author":
                                parsed.Author = value;
                                break;
                            case "min_revit_version":
                                parsed.MinRevitVersion = value;
                                break;
                            case "engine":
                            case "title":
                            case "tooltip":
                            case "layout":
                                break;
                        }
                    }
                    // Layout entries: any line starting with '-' under a layout section
                    else if (currentSection == "layout" && line.StartsWith("-"))
                    {
                        var item = line.Substring(1).Trim();

                        if ((item.StartsWith("\"") && item.EndsWith("\"")) ||
                            (item.StartsWith("'") && item.EndsWith("'")))
                        {
                            item = item.Substring(1, item.Length - 2);
                        }

                        parsed.LayoutOrder.Add(item);
                    }
                    // Titles and tooltips
                    else if ((currentSection == "title" || currentSection == "tooltip") && line.Contains(":"))
                    {
                        var parts = line.Split(new[] { ':' }, 2);
                        var lang = parts[0].Trim();
                        var text = parts[1].Trim();
                        if (currentSection == "title")
                            parsed.Titles[lang] = text;
                        else
                            parsed.Tooltips[lang] = text;
                    }
                    // Engine config options
                    else if (currentSection == "engine" && line.Contains(":"))
                    {
                        var parts = line.Split(new[] { ':' }, 2);
                        var key = parts[0].Trim().ToLowerInvariant();
                        var val = parts[1].Trim().ToLowerInvariant();

                        switch (key)
                        {
                            case "clean":
                                parsed.Engine.Clean = val == "true";
                                break;
                            case "full_frame":
                                parsed.Engine.FullFrame = val == "true";
                                break;
                            case "persistent":
                                parsed.Engine.Persistent = val == "true";
                                break;
                        }
                    }
                }

                return parsed;
            }
        }
    }
}
