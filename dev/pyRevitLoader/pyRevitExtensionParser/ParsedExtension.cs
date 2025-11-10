using System.Collections.Generic;
using System.IO;
using System.Linq;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParser 
{
    public class ParsedExtension : ParsedComponent
    {
        public string Directory { get; set; }
        public Dictionary<string, string> Titles { get; set; }
        public Dictionary<string, string> Tooltips { get; set; }
        public string MinRevitVersion { get; set; }
        public EngineConfig Engine { get; set; }
        public ExtensionConfig Config { get; set; }
        public string GetHash() => Directory.GetHashCode().ToString("X");
        
        /// <summary>
        /// Gets the path to the startup script if it exists
        /// </summary>
        public string StartupScript => FindStartupScript();

        private static readonly CommandComponentType[] _allowedTypes = new[] {
            CommandComponentType.PushButton,
            CommandComponentType.PanelButton,
            CommandComponentType.SmartButton,
            CommandComponentType.UrlButton
        };

        public IEnumerable<ParsedComponent> CollectCommandComponents()
            => Collect(this.Children);

        private IEnumerable<ParsedComponent> Collect(IEnumerable<ParsedComponent> list)
        {
            if (list == null) yield break;

            foreach (var comp in list)
            {
                if (comp.Children != null)
                {
                    foreach (var child in Collect(comp.Children))
                        yield return child;
                }

                if (_allowedTypes.Contains(comp.Type))
                    yield return comp;
            }
        }

        /// <summary>
        /// Finds the startup script in the extension directory
        /// Checks for startup files in order: .py, .cs, .vb, .rb
        /// </summary>
        /// <returns>Full path to the startup script or null if not found</returns>
        private string FindStartupScript()
        {
            if (string.IsNullOrEmpty(Directory) || !System.IO.Directory.Exists(Directory))
                return null;

            // Check for startup scripts in order of preference
            var startupFiles = new[]
            {
                "startup.py",   // Python
                "startup.cs",   // C#
                "startup.vb",   // VB.NET
                "startup.rb"    // Ruby
            };

            foreach (var fileName in startupFiles)
            {
                var fullPath = Path.Combine(Directory, fileName);
                if (File.Exists(fullPath))
                    return fullPath;
            }

            return null;
        }

    }
    public class ExtensionConfig
    {
        public string Name { get; set; }
        public bool Disabled { get; set; }
        public bool PrivateRepo { get; set; }
        public string Username { get; set; }
        public string Password { get; set; }
    }

    public class EngineConfig
    {
        public bool Clean { get; set; }
        public bool FullFrame { get; set; }
        public bool Persistent { get; set; }
    }
}
