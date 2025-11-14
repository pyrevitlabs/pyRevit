using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParser 
{
    public class ParsedExtension : ParsedComponent
    {
        public new string Directory { get; set; }
        public Dictionary<string, string> Titles { get; set; }
        public Dictionary<string, string> Tooltips { get; set; }
        public string MinRevitVersion { get; set; }
        public EngineConfig Engine { get; set; }
        public ExtensionConfig Config { get; set; }
        
        /// <summary>
        /// Calculates a hash based on the modification times of all relevant files in the extension directory.
        /// This matches the Python implementation in coreutils.calculate_dir_hash()
        /// </summary>
        /// <param name="seed">Optional seed to include in hash calculation. Use empty string for Python, 'ILPack' for ILPack, 'Roslyn' for Roslyn</param>
        public string GetHash(string seed = "")
        {
            if (string.IsNullOrEmpty(Directory) || !System.IO.Directory.Exists(Directory))
                return Directory?.GetHashCode().ToString("X") ?? "0";

            try
            {
                long mtimeSum = 0;

                // Walk through all subdirectories
                foreach (var dir in System.IO.Directory.GetDirectories(Directory, "*", SearchOption.AllDirectories))
                {
                    var dirName = Path.GetFileName(dir);
                    
                    // Skip directories with .extension in name (like Python's dir_filter)
                    if (!dirName.EndsWith(".extension", StringComparison.OrdinalIgnoreCase))
                    {
                        mtimeSum += System.IO.Directory.GetLastWriteTimeUtc(dir).Ticks;
                    }
                }

                // Process all files
                foreach (var file in System.IO.Directory.GetFiles(Directory, "*.*", SearchOption.AllDirectories))
                {
                    var fileName = Path.GetFileName(file);
                    var ext = Path.GetExtension(file).ToLowerInvariant();
                    
                    // Include relevant script files (matching Python's file_filter)
                    if (ext == ".py" || ext == ".cs" || ext == ".vb" || ext == ".rb" || 
                        ext == ".dyn" || ext == ".gh" || ext == ".ghx" ||
                        ext == ".xaml" || ext == ".yaml" || ext == ".json")
                    {
                        mtimeSum += File.GetLastWriteTimeUtc(file).Ticks;
                    }
                }

                // Use MD5 hash like Python's get_str_hash()
                // Include the seed in the hash to differentiate between build strategies
                using (var md5 = MD5.Create())
                {
                    var inputString = mtimeSum.ToString() + seed;
                    var bytes = Encoding.UTF8.GetBytes(inputString);
                    var hashBytes = md5.ComputeHash(bytes);
                    return BitConverter.ToString(hashBytes).Replace("-", "").ToLowerInvariant();
                }
            }
            catch
            {
                // Fallback to simple hash if directory scanning fails
                return Directory.GetHashCode().ToString("X");
            }
        }
        
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
        /// Collects all lib/ folder paths from the component hierarchy (extension -> tab -> panel -> button)
        /// matching Python's behavior where each component can have its own lib/ folder
        /// </summary>
        public List<string> CollectLibraryPaths(ParsedComponent command)
        {
            var libPaths = new List<string>();
            
            // Start with extension's lib folder
            var extLib = Path.Combine(this.Directory, "lib");
            if (System.IO.Directory.Exists(extLib))
                libPaths.Add(extLib);
            
            // Collect lib paths from component hierarchy
            CollectLibPathsRecursive(this.Children, command, libPaths);
            
            return libPaths;
        }
        
        private bool CollectLibPathsRecursive(IEnumerable<ParsedComponent> siblings, ParsedComponent target, List<string> libPaths)
        {
            if (siblings == null) return false;
            
            foreach (var comp in siblings)
            {
                // Check if this component has a lib folder
                if (!string.IsNullOrEmpty(comp.Directory))
                {
                    var compLib = Path.Combine(comp.Directory, "lib");
                    if (System.IO.Directory.Exists(compLib) && !libPaths.Contains(compLib))
                        libPaths.Add(compLib);
                }
                
                // If this is our target command, we're done
                if (comp == target)
                    return true;
                
                // Otherwise, recurse into children
                if (comp.Children != null && CollectLibPathsRecursive(comp.Children, target, libPaths))
                    return true;
            }
            
            return false;
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
