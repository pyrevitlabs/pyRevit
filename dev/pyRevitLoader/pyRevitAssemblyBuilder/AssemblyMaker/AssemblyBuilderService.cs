using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Text;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using pyRevitExtensionParser;
using pyRevitAssemblyBuilder.SessionManager;

namespace pyRevitAssemblyBuilder.AssemblyMaker
{
    /// <summary>
    /// Enumeration of available assembly build strategies.
    /// </summary>
    public enum AssemblyBuildStrategy
    {
        /// <summary>
        /// Build using Roslyn compiler (C# code generation).
        /// </summary>
        Roslyn
    }

    /// <summary>
    /// Service for building extension assemblies from parsed extensions.
    /// </summary>
    public class AssemblyBuilderService : IAssemblyBuilderService
    {
        private readonly ILogger _logger;
        private readonly string _revitVersion;
        private readonly AssemblyBuildStrategy _buildStrategy;
        private static readonly string _executingAssemblyLocation = Assembly.GetExecutingAssembly().Location;
        private static readonly string _baseDir = Path.GetDirectoryName(_executingAssemblyLocation);

        /// <summary>
        /// Initializes a new instance of the <see cref="AssemblyBuilderService"/> class.
        /// </summary>
        /// <param name="revitVersion">The Revit version number (e.g., "2024").</param>
        /// <param name="buildStrategy">The build strategy to use for creating assemblies.</param>
        /// <param name="logger">The logger instance.</param>
        /// <exception cref="ArgumentNullException">Thrown when revitVersion or logger is null.</exception>
        public AssemblyBuilderService(string revitVersion, AssemblyBuildStrategy buildStrategy, ILogger logger)
        {
            _revitVersion = revitVersion ?? throw new ArgumentNullException(nameof(revitVersion));
            _buildStrategy = buildStrategy;
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
        }

        /// <summary>
        /// Builds an assembly for the specified extension.
        /// </summary>
        /// <param name="extension">The parsed extension to build an assembly for.</param>
        /// <param name="libraryExtensions">Optional collection of library extensions to include as references.</param>
        /// <param name="rocketMode">Whether rocket mode is enabled globally.</param>
        /// <returns>Information about the built assembly.</returns>
        /// <exception cref="ArgumentNullException">Thrown when extension is null.</exception>
        /// <exception cref="Exception">Thrown when assembly building fails.</exception>
        public ExtensionAssemblyInfo BuildExtensionAssembly(ParsedExtension extension, IEnumerable<ParsedExtension> libraryExtensions = null, bool rocketMode = false)
        {
            if (extension == null)
                throw new ArgumentNullException(nameof(extension));

            // Check if any assembly for this extension is already loaded in the AppDomain.
            // This determines if we are reloading (extension was already loaded previously).
            // Matches pythonic loader's _is_any_ext_asm_loaded() check in asmmaker.py
            bool isReloading = IsAnyExtensionAssemblyLoaded(extension);
            if (isReloading)
            {
                _logger.Debug($"Extension '{extension.Name}' is being reloaded (assembly already loaded in AppDomain).");
            }

            // Pre-load module DLLs before building the assembly
            // This matches the pythonic loader's approach: collect modules and load them
            // so they're available in the AppDomain for CLREngine to reference
            LoadExtensionModules(extension);

            // Include generation-time inputs that affect emitted command types, so cache invalidates
            // when runtime behavior changes (e.g. rocket mode toggles or loader binary updates).
            string strategySeed = string.Join("|",
                _buildStrategy.ToString(),
                $"rocket:{rocketMode}",
                $"rocket_compat:{extension.RocketModeCompatible}",
                $"builder:{GetAssemblyBuildFingerprint()}");
            string hash = GetStableHash(extension.GetHash(strategySeed) + _revitVersion).Substring(0, 16);
            string fileName = $"pyRevit_{_revitVersion}_{hash}_{extension.Name}.dll";

            string outputDir = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                "pyRevit",
                _revitVersion);
            Directory.CreateDirectory(outputDir);

            string outputPath = Path.Combine(outputDir, fileName);

            // Check if assembly file already exists (hash-based caching)
            if (File.Exists(outputPath))
            {
                _logger.Debug($"Found cached assembly: {outputPath}");
                try
                {
                    var assemblyName = AssemblyName.GetAssemblyName(outputPath);
                    return new ExtensionAssemblyInfo(extension.Name, outputPath, isReloading);
                }
                catch (Exception ex)
                {
                    // If file is corrupted or invalid, delete it and rebuild
                    _logger.Debug($"Cached assembly file is corrupted or invalid: {outputPath}");
                    _logger.Debug($"Exception: {ex.Message}");
                    try
                    {
                        File.Delete(outputPath);
                        _logger.Debug($"Deleted corrupted assembly file: {outputPath}");
                    }
                    catch (Exception deleteEx)
                    {
                        _logger.Warning($"Failed to delete corrupted assembly file: {outputPath} | {deleteEx.Message}");
                        // Ignore delete errors, build will overwrite
                    }
                }
            }

            try
            {
                BuildWithRoslyn(extension, outputPath, libraryExtensions, rocketMode);

                return new ExtensionAssemblyInfo(extension.Name, outputPath, isReloading);
            }
            catch
            {
                throw;
            }
        }

        /// <summary>
        /// Cached list of loaded pyRevit assembly names, built once per session on first access.
        /// </summary>
        /// <remarks>
        /// Perf fix for #3268 issue #4: The original code called
        /// <c>AppDomain.CurrentDomain.GetAssemblies()</c> and iterated every loaded assembly
        /// (hundreds in a typical Revit session) for <em>each</em> extension.  This field stores
        /// only the pyRevit-prefixed names (~10-20) so per-extension checks are O(N) over a
        /// tiny set instead of O(M) over the full AppDomain.
        /// </remarks>
        private List<string> _loadedPyRevitAssemblyNames;

        private void EnsureLoadedAssemblyNamesCached()
        {
            if (_loadedPyRevitAssemblyNames != null)
                return;

            const string PYREVIT_PREFIX = "pyRevit_";
            _loadedPyRevitAssemblyNames = new List<string>();

            foreach (var loadedAsm in AppDomain.CurrentDomain.GetAssemblies())
            {
                try
                {
                    var asmName = loadedAsm.GetName().Name;
                    if (asmName != null && asmName.StartsWith(PYREVIT_PREFIX))
                        _loadedPyRevitAssemblyNames.Add(asmName);
                }
                catch
                {
                    // Some dynamic/collectible assemblies throw — skip silently
                }
            }
        }

        /// <summary>
        /// Checks if any assembly for this extension is already loaded in the AppDomain.
        /// This is used to detect if we are reloading an extension.
        /// </summary>
        /// <param name="extension">The extension to check.</param>
        /// <returns>True if an assembly for this extension is already loaded.</returns>
        private bool IsAnyExtensionAssemblyLoaded(ParsedExtension extension)
        {
            EnsureLoadedAssemblyNamesCached();

            // Assembly names follow: pyRevit_{revitVersion}_{hash}_{extensionName}
            foreach (var name in _loadedPyRevitAssemblyNames)
            {
                if (name.EndsWith(extension.Name, StringComparison.OrdinalIgnoreCase))
                {
                    _logger.Debug($"Found loaded extension assembly: {name}");
                    return true;
                }
            }

            return false;
        }

        /// <summary>
        /// Pre-loads module DLLs for all commands in the extension.
        /// Mimics the pythonic loader's approach: assmutils.load_asm_files(ui_ext_modules)
        /// This makes the modules available in the AppDomain for CLREngine to reference.
        /// </summary>
        private void LoadExtensionModules(ParsedExtension extension)
        {
            var loadedModules = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            // Collect all module DLLs from all commands
            foreach (var cmd in extension.CollectCommandComponents())
            {
                if (cmd.Modules == null || cmd.Modules.Count == 0)
                    continue;

                foreach (var moduleName in cmd.Modules)
                {
                    // Find the module DLL using binary paths
                    var modulePath = extension.FindModuleDll(moduleName, cmd);
                    
                    if (string.IsNullOrEmpty(modulePath))
                        continue;

                    // Skip if already loaded
                    if (loadedModules.Contains(modulePath))
                        continue;

                    try
                    {
                        // Load the module DLL into the AppDomain
                        Assembly.LoadFrom(modulePath);
                        loadedModules.Add(modulePath);
                        _logger.Debug($"Loaded module: {modulePath}");
                    }
                    catch (Exception ex)
                    {
                        _logger.Error($"Failed to load module: {modulePath} | {ex.Message}");
                    }
                }
            }

            // Update the environment dictionary with loaded module paths
            // This matches pythonic loader's sessioninfo.update_loaded_pyrevit_referenced_modules()
            if (loadedModules.Count > 0)
                UpdateReferencedAssemblies(loadedModules);
        }

        /// <summary>
        /// Updates the AppDomain's environment dictionary with referenced assemblies.
        /// Mimics pythonic loader's sessioninfo.update_loaded_pyrevit_referenced_modules()
        /// </summary>
        private void UpdateReferencedAssemblies(HashSet<string> newModulePaths)
        {
            try
            {
                // Get the environment dictionary from AppDomain
                const string envDictKey = SessionManager.Constants.ENV_DICT_KEY;
                const string refedAssmsKey = SessionManager.Constants.REFED_ASSMS_KEY;

                var envDict = AppDomain.CurrentDomain.GetData(envDictKey) as IDictionary<object, object>;
                if (envDict == null)
                    return;

                // Get existing referenced assemblies
                var existingAssemblies = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                if (envDict.ContainsKey(refedAssmsKey))
                {
                    var existingValue = envDict[refedAssmsKey] as string;
                    if (!string.IsNullOrEmpty(existingValue))
                    {
                        foreach (var path in existingValue.Split(Path.PathSeparator))
                        {
                            if (!string.IsNullOrWhiteSpace(path))
                                existingAssemblies.Add(path);
                        }
                    }
                }

                // Add new module paths
                existingAssemblies.UnionWith(newModulePaths);

                // Update the environment dictionary
                var updatedValue = string.Join(Path.PathSeparator.ToString(), existingAssemblies);
                envDict[refedAssmsKey] = updatedValue;
            }
            catch (Exception ex)
            {
                _logger.Error($"Failed to update referenced assemblies in AppDomain: {ex.Message}");
            }
        }

        /// <summary>
        /// Builds an extension assembly using the Roslyn compiler (C# code generation approach).
        /// </summary>
        /// <param name="extension">The parsed extension to build.</param>
        /// <param name="outputPath">The output path for the compiled assembly.</param>
        /// <param name="libraryExtensions">Optional library extensions to reference.</param>
        /// <param name="rocketMode">Whether rocket mode is enabled globally.</param>
        /// <exception cref="Exception">Thrown when Roslyn compilation fails.</exception>
        private void BuildWithRoslyn(ParsedExtension extension, string outputPath, IEnumerable<ParsedExtension> libraryExtensions, bool rocketMode)
        {
            var generator = new RoslynCommandTypeGenerator();
            string code = generator.GenerateExtensionCode(extension, _revitVersion, libraryExtensions, rocketMode);
            var csPath = Path.Combine(Path.GetDirectoryName(outputPath), $"{extension.Name}.cs");
            File.WriteAllText(csPath, code);
            _logger.Debug($"Generated C# code file: {csPath}");

            var tree = CSharpSyntaxTree.ParseText(code);
            var compilation = CSharpCompilation.Create(
                Path.GetFileNameWithoutExtension(outputPath),
                new[] { tree },
                ResolveRoslynReferences(),
                new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary, optimizationLevel: OptimizationLevel.Release));

            using var fs = new FileStream(outputPath, FileMode.Create);
            var result = compilation.Emit(fs);
            
            if (!result.Success)
            {
                _logger.Error($"Roslyn compilation failed for: {extension.Name}");
                foreach (var diagnostic in result.Diagnostics.Where(d => d.Severity == DiagnosticSeverity.Error))
                    _logger.Error($"  {diagnostic}");
                throw new Exception("Roslyn compilation failed.");
            }
        }

        /// <summary>
        /// Resolves and returns the metadata references required for Roslyn compilation.
        /// </summary>
        /// <remarks>
        /// <para>
        /// Includes references to core .NET assemblies, Revit API assemblies, and pyRevit runtime.
        /// </para>
        /// <para>
        /// Perf fix for #3268 issue #3: <c>MetadataReference.CreateFromFile()</c> reads assembly
        /// metadata from disk on every call.  These references never change during a Revit session,
        /// so they are built once and cached statically.  A version guard ensures correctness if
        /// the static field somehow survives across different Revit version contexts (it won't in
        /// practice, but defensive coding costs nothing here).
        /// </para>
        /// </remarks>
        /// <returns>A list of metadata references for the Roslyn compiler.</returns>
        private static List<MetadataReference> _cachedRoslynRefs;
        private static string _cachedRoslynRefsVersion;
        private static readonly object _roslynRefsLock = new object();

        private List<MetadataReference> ResolveRoslynReferences()
        {
            // Fast path — already cached for this Revit version
            if (_cachedRoslynRefs != null && _cachedRoslynRefsVersion == _revitVersion)
                return _cachedRoslynRefs;

            lock (_roslynRefsLock)
            {
                if (_cachedRoslynRefs != null && _cachedRoslynRefsVersion == _revitVersion)
                    return _cachedRoslynRefs;

                string baseDir = _baseDir;
                var refs = new List<MetadataReference>
                {
                    MetadataReference.CreateFromFile(typeof(object).Assembly.Location),
                    MetadataReference.CreateFromFile(typeof(Console).Assembly.Location),
                    MetadataReference.CreateFromFile(Path.Combine(AppContext.BaseDirectory, "RevitAPI.dll")),
                    MetadataReference.CreateFromFile(Path.Combine(AppContext.BaseDirectory, "RevitAPIUI.dll")),
                    MetadataReference.CreateFromFile(Path.Combine(baseDir, $"PyRevitLabs.PyRevit.Runtime.{_revitVersion}.dll"))
                };
                string sys = Path.Combine(Path.GetDirectoryName(typeof(object).Assembly.Location), "System.Runtime.dll");
                if (File.Exists(sys)) refs.Add(MetadataReference.CreateFromFile(sys));

                _cachedRoslynRefs = refs;
                _cachedRoslynRefsVersion = _revitVersion;
                return _cachedRoslynRefs;
            }
        }

        /// <summary>
        /// Generates a stable SHA1 hash from the input string.
        /// </summary>
        /// <remarks>
        /// This method creates a deterministic hash that is used for assembly caching.
        /// The hash is computed using SHA1 algorithm and returns a 40-character hexadecimal string.
        /// The input should include:
        /// - Extension structure hash (from extension.GetHash())
        /// - Build strategy seed ("Roslyn")
        /// - Revit version
        /// 
        /// This ensures that assemblies are only regenerated when:
        /// 1. The extension structure changes
        /// 2. The Revit version changes
        /// </remarks>
        /// <param name="input">The string to hash, typically a concatenation of extension hash, strategy seed, and Revit version.</param>
        /// <returns>A 40-character lowercase hexadecimal string representing the SHA1 hash.</returns>
        private static string GetStableHash(string input)
        {
            using var sha1 = System.Security.Cryptography.SHA1.Create();
            var hash = sha1.ComputeHash(Encoding.UTF8.GetBytes(input));
            return BitConverter.ToString(hash).Replace("-", string.Empty).ToLowerInvariant();
        }

        // Perf fix for #3268 issue #7: The executing assembly never changes during a
        // Revit session — cache the fingerprint once as a static readonly instead of
        // re-reading file metadata and assembly version on every extension build.
        private static readonly string _assemblyBuildFingerprint = ComputeAssemblyBuildFingerprint();

        private static string GetAssemblyBuildFingerprint() => _assemblyBuildFingerprint;

        private static string ComputeAssemblyBuildFingerprint()
        {
            try
            {
                var asmPath = _executingAssemblyLocation;
                var writeTime = File.Exists(asmPath)
                    ? File.GetLastWriteTimeUtc(asmPath).Ticks.ToString()
                    : "0";
                var version = Assembly.GetExecutingAssembly().GetName().Version?.ToString() ?? "0";
                return string.Join("-", version, writeTime);
            }
            catch
            {
                return "0";
            }
        }

        /// <summary>
        /// Loads an assembly into the current AppDomain.
        /// </summary>
        /// <param name="info">Information about the assembly to load.</param>
        /// <exception cref="FileNotFoundException">Thrown when the assembly file is not found.</exception>
        /// <exception cref="Exception">Thrown when assembly loading fails.</exception>
        public void LoadAssembly(ExtensionAssemblyInfo info)
        {
            if (!File.Exists(info.Location))
                throw new FileNotFoundException("Assembly not found", info.Location);
            Assembly.LoadFrom(info.Location);
        }
    }
}
