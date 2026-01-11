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
        public ExtensionConfig Config { get; set; }
        
        // Cache directory existence checks to avoid repeated file system calls
        private Dictionary<string, bool> _dirExistsCache = new Dictionary<string, bool>();
        
        // Cache lib/bin paths per command to avoid repeated hierarchy traversal
        private Dictionary<ParsedComponent, List<string>> _libPathsCache = new Dictionary<ParsedComponent, List<string>>();
        private Dictionary<ParsedComponent, List<string>> _binPathsCache = new Dictionary<ParsedComponent, List<string>>();
        
        // Cached helper to check directory existence with memoization
        private bool DirExists(string path)
        {
            if (string.IsNullOrEmpty(path))
                return false;
                
            if (!_dirExistsCache.TryGetValue(path, out bool exists))
            {
                exists = System.IO.Directory.Exists(path);
                _dirExistsCache[path] = exists;
            }
            return exists;
        }
        
        // Static HashSet for O(1) extension lookup - much faster than string comparisons
        private static readonly HashSet<string> _scriptExtensions = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            ".py", ".cs", ".vb", ".rb", ".dyn", ".gh", ".ghx", ".xaml", ".yaml", ".json"
        };
        
        // Cached hash value to avoid recalculation
        private Dictionary<string, string> _cachedHashes = new Dictionary<string, string>();
        
        /// <summary>
        /// Calculates a hash based on the modification times of all relevant files in the extension directory.
        /// This matches the Python implementation in coreutils.calculate_dir_hash()
        /// OPTIMIZED: Uses EnumerateFiles/EnumerateDirectories for lazy evaluation, HashSet for O(1) extension lookup
        /// </summary>
        /// <param name="seed">Optional seed to include in hash calculation. Use empty string for Python, 'Roslyn' for Roslyn build strategy</param>
        public string GetHash(string seed = "")
        {
            // Check cache first
            if (_cachedHashes.TryGetValue(seed, out var cachedHash))
                return cachedHash;
                
            if (string.IsNullOrEmpty(Directory) || !System.IO.Directory.Exists(Directory))
                return Directory?.GetHashCode().ToString("X") ?? "0";

            try
            {
                long mtimeSum = 0;

                // Use EnumerateDirectories for lazy evaluation - doesn't load all paths into memory at once
                foreach (var dir in System.IO.Directory.EnumerateDirectories(Directory, "*", SearchOption.AllDirectories))
                {
                    var dirName = Path.GetFileName(dir);
                    
                    // Skip directories with .extension in name (like Python's dir_filter)
                    if (!dirName.EndsWith(".extension", StringComparison.OrdinalIgnoreCase))
                    {
                        mtimeSum += System.IO.Directory.GetLastWriteTimeUtc(dir).Ticks;
                    }
                }

                // Use EnumerateFiles for lazy evaluation - processes files as they're found
                foreach (var file in System.IO.Directory.EnumerateFiles(Directory, "*.*", SearchOption.AllDirectories))
                {
                    var ext = Path.GetExtension(file);
                    
                    // Use HashSet.Contains for O(1) lookup instead of multiple string comparisons
                    if (_scriptExtensions.Contains(ext))
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
                    var result = BitConverter.ToString(hashBytes).Replace("-", "").ToLowerInvariant();
                    _cachedHashes[seed] = result;
                    return result;
                }
            }
            catch
            {
                // Fallback to simple hash if directory scanning fails
                return Directory.GetHashCode().ToString("X");
            }
        }
        
        // Cached startup script path to avoid repeated file system checks
        private string _startupScript;
        private bool _startupScriptInitialized;
        
        /// <summary>
        /// Gets the path to the startup script if it exists
        /// </summary>
        public string StartupScript
        {
            get
            {
                if (!_startupScriptInitialized)
                {
                    _startupScript = FindStartupScript();
                    _startupScriptInitialized = true;
                }
                return _startupScript;
            }
        }

        // Use HashSet for O(1) type lookup instead of Contains on array
        private static readonly HashSet<CommandComponentType> _allowedTypes = new HashSet<CommandComponentType>
        {
            CommandComponentType.PushButton,
            CommandComponentType.PanelButton,
            CommandComponentType.SmartButton,
            CommandComponentType.UrlButton,
            CommandComponentType.InvokeButton,
            CommandComponentType.ContentButton
        };

        // Cached command components - this is called 3+ times per extension during loading
        private List<ParsedComponent> _cachedCommandComponents;
        
        /// <summary>
        /// Collects all command components from this extension (cached after first call).
        /// Builds control IDs for each component based on hierarchy.
        /// </summary>
        public IEnumerable<ParsedComponent> CollectCommandComponents()
        {
            if (_cachedCommandComponents == null)
            {
                _cachedCommandComponents = new List<ParsedComponent>();
                // Start with no parent control ID - tabs will be the first level
                CollectInto(_cachedCommandComponents, this.Children, null);
            }
            return _cachedCommandComponents;
        }

        // Non-allocating collection method - adds directly to list instead of yielding
        // parentControlId tracks the control ID hierarchy for building correct IDs
        private void CollectInto(List<ParsedComponent> result, IEnumerable<ParsedComponent> list, string parentControlId)
        {
            if (list == null) return;

            foreach (var comp in list)
            {
                // Build control ID for this component
                // Format matches Python: 
                // - For tabs (no parent): "CustomCtrl_%CustomCtrl_%{name}"
                // - For other components: "{parentId}%{name}"
                // - For groups inside groups (like pulldowns inside panels): need special handling
                // IMPORTANT: Use DisplayName (original folder name with spaces) for control IDs,
                // NOT Name (which has spaces stripped). Revit uses the actual folder names.
                string displayName = comp.DisplayName ?? comp.Name;
                
                string currentControlId;
                if (string.IsNullOrEmpty(parentControlId))
                {
                    // Top-level (tab): "CustomCtrl_%CustomCtrl_%{name}"
                    currentControlId = $"CustomCtrl_%CustomCtrl_%{displayName}";
                }
                else if (comp.Type == CommandComponentType.PullDown || 
                         comp.Type == CommandComponentType.SplitButton ||
                         comp.Type == CommandComponentType.SplitPushButton ||
                         comp.Type == CommandComponentType.Stack)
                {
                    // Command groups inside containers need to deepen the hierarchy
                    // This matches Python's GenericUICommandGroup.control_id behavior
                    var deepenedParent = parentControlId.Replace("_%CustomCtrl", "_%CustomCtrl_%CustomCtrl");
                    currentControlId = $"{deepenedParent}%{displayName}";
                }
                else
                {
                    // Normal child: append to parent
                    currentControlId = $"{parentControlId}%{displayName}";
                }
                
                // Set the control ID on the component
                comp.ControlId = currentControlId;

                if (comp.Children != null)
                {
                    CollectInto(result, comp.Children, currentControlId);
                }

                // HashSet.Contains is O(1) vs array Contains which is O(n)
                if (_allowedTypes.Contains(comp.Type))
                    result.Add(comp);
            }
        }
        
        /// <summary>
        /// Collects all lib/ folder paths from the component hierarchy (extension -> tab -> panel -> button)
        /// matching Python's behavior where each component can have its own lib/ folder
        /// </summary>
        public List<string> CollectLibraryPaths(ParsedComponent command)
        {
            // Check cache first
            if (_libPathsCache.TryGetValue(command, out var cached))
                return cached;
                
            var libPaths = new List<string>();
            
            // Start with extension's lib folder
            if (!string.IsNullOrEmpty(this.Directory))
            {
                var extLib = Path.Combine(this.Directory, "lib");
                if (DirExists(extLib))
                    libPaths.Add(extLib);
            }
            
            // Collect lib paths from component hierarchy
            CollectLibPathsRecursive(this.Children, command, libPaths);
            
            // Cache the result
            _libPathsCache[command] = libPaths;
            
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
                    if (DirExists(compLib) && !libPaths.Contains(compLib))
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
        /// Collects all bin/ folder paths from the component hierarchy for locating invoke assemblies.
        /// </summary>
        public List<string> CollectBinaryPaths(ParsedComponent command)
        {
            // Check cache first
            if (_binPathsCache.TryGetValue(command, out var cached))
                return cached;
                
            var binPaths = new List<string>();

            if (!string.IsNullOrEmpty(this.Directory))
            {
                var extBin = Path.Combine(this.Directory, "bin");
                if (DirExists(extBin))
                    binPaths.Add(extBin);
            }

            CollectBinPathsRecursive(this.Children, command, binPaths);

            if (command != null && !string.IsNullOrEmpty(command.Directory))
            {
                var cmdBin = Path.Combine(command.Directory, "bin");
                if (DirExists(cmdBin) && !binPaths.Contains(cmdBin))
                    binPaths.Add(cmdBin);

                if (!binPaths.Contains(command.Directory))
                    binPaths.Add(command.Directory);
            }

            // Cache the result
            _binPathsCache[command] = binPaths;
            
            return binPaths;
        }

        private bool CollectBinPathsRecursive(IEnumerable<ParsedComponent> siblings, ParsedComponent target, List<string> binPaths)
        {
            if (siblings == null)
                return false;

            foreach (var comp in siblings)
            {
                if (!string.IsNullOrEmpty(comp.Directory))
                {
                    var compBin = Path.Combine(comp.Directory, "bin");
                    if (DirExists(compBin) && !binPaths.Contains(compBin))
                        binPaths.Add(compBin);
                }

                if (comp == target)
                    return true;

                if (comp.Children != null && CollectBinPathsRecursive(comp.Children, target, binPaths))
                    return true;
            }

            return false;
        }

        /// <summary>
        /// Finds a module DLL by searching binary paths.
        /// Mimics the pythonic loader's find_bundle_module() function.
        /// </summary>
        public string FindModuleDll(string moduleName, ParsedComponent command)
        {
            // If moduleName is already a full path and exists, return it
            if (Path.IsPathRooted(moduleName) && File.Exists(moduleName))
                return moduleName;

            // Get all binary paths for this command
            var binaryPaths = CollectBinaryPaths(command);

            // Search for the module in each binary path
            foreach (var binPath in binaryPaths)
            {
                var possibleModulePath = Path.Combine(binPath, moduleName);
                if (File.Exists(possibleModulePath))
                    return possibleModulePath;
            }

            return null;
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
}
