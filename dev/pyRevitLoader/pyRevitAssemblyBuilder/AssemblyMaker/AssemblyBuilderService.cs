using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using System.Text;
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
        /// <returns>Information about the built assembly.</returns>
        /// <exception cref="ArgumentNullException">Thrown when extension is null.</exception>
        /// <exception cref="Exception">Thrown when assembly building fails.</exception>
        public ExtensionAssemblyInfo BuildExtensionAssembly(ParsedExtension extension, IEnumerable<ParsedExtension> libraryExtensions = null)
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

            // Use build strategy as seed to differentiate DLLs built with different strategies
            // This ensures DLLs are only regenerated when extension structure changes or build strategy changes
            string strategySeed = _buildStrategy.ToString();
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
                BuildWithRoslyn(extension, outputPath, libraryExtensions);

                return new ExtensionAssemblyInfo(extension.Name, outputPath, isReloading);
            }
            catch
            {
                throw;
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
            const string PYREVIT_PREFIX = "pyRevit_";
            
            foreach (var loadedAsm in AppDomain.CurrentDomain.GetAssemblies())
            {
                try
                {
                    var asmName = loadedAsm.GetName().Name;
                    if (asmName == null)
                        continue;

                    // Check if this is a pyRevit extension assembly for this extension
                    // Assembly names follow the pattern: pyRevit_{revitVersion}_{hash}_{extensionName}
                    if (asmName.StartsWith(PYREVIT_PREFIX) && asmName.EndsWith(extension.Name))
                    {
                        _logger.Debug($"Found loaded extension assembly: {asmName}");
                        return true;
                    }
                }
                catch (Exception ex)
                {
                    // Some assemblies may throw when getting their name, skip them
                    _logger.Debug($"Error checking assembly: {ex.Message}");
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
        /// <exception cref="Exception">Thrown when Roslyn compilation fails.</exception>
        private void BuildWithRoslyn(ParsedExtension extension, string outputPath, IEnumerable<ParsedExtension> libraryExtensions)
        {
            var generator = new RoslynCommandTypeGenerator();
            string code = generator.GenerateExtensionCode(extension, _revitVersion, libraryExtensions);
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
        /// Includes references to core .NET assemblies, Revit API assemblies, and pyRevit runtime.
        /// </remarks>
        /// <returns>A list of metadata references for the Roslyn compiler.</returns>
        private List<MetadataReference> ResolveRoslynReferences()
        {
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
            return refs;
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
