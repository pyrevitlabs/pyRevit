#nullable enable
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Reflection;
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitAssemblyBuilder.UIManager;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Service for managing pyRevit session loading, including assembly building and UI creation.
    /// </summary>
    public class SessionManagerService : ISessionManagerService
    {
        private readonly IAssemblyBuilderService _assemblyBuilder;
        private readonly IExtensionManagerService _extensionManager;
        private readonly IHookManager _hookManager;
        private readonly IUIManagerService _uiManager;
        private readonly UIApplication _uiApp;
        private readonly ILogger _logger;
        
        // These fields are initialized in InitializeScriptExecutor(), not the constructor
        private Assembly? _runtimeAssembly;
        private string? _pyRevitRoot;
        private string? _binDir;
        private Type? _scriptDataType;
        private Type? _scriptRuntimeConfigsType;
        private Type? _scriptExecutorType;
        private Type? _scriptExecutorConfigsType;
        private MethodInfo? _executeScriptMethod;
        private PropertyInfo? _externalCommandDataAppProperty;
        private Dictionary<string, bool> _directoryExistsCache = new Dictionary<string, bool>();

        /// <summary>
        /// Initializes a new instance of the <see cref="SessionManagerService"/> class.
        /// </summary>
        /// <param name="assemblyBuilder">Service for building extension assemblies.</param>
        /// <param name="extensionManager">Service for managing extensions.</param>
        /// <param name="hookManager">Service for managing hooks.</param>
        /// <param name="uiManager">Service for building UI elements.</param>
        /// <param name="logger">Logger instance for logging.</param>
        /// <exception cref="ArgumentNullException">Thrown when uiManager is null or does not have a valid UIApplication.</exception>
        public SessionManagerService(
            IAssemblyBuilderService assemblyBuilder,
            IExtensionManagerService extensionManager,
            IHookManager hookManager,
            IUIManagerService uiManager,
            ILogger logger)
        {
            _assemblyBuilder = assemblyBuilder ?? throw new ArgumentNullException(nameof(assemblyBuilder));
            _extensionManager = extensionManager ?? throw new ArgumentNullException(nameof(extensionManager));
            _hookManager = hookManager ?? throw new ArgumentNullException(nameof(hookManager));
            _uiManager = uiManager ?? throw new ArgumentNullException(nameof(uiManager));
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            
            // Get UIApplication from UIManagerService via public property
            _uiApp = uiManager.UIApplication 
                ?? throw new ArgumentNullException(nameof(uiManager), "UIManagerService must have a valid UIApplication.");
        }

        /// <summary>
        /// Loads a new pyRevit session by building assemblies and creating UI for all installed extensions.
        /// </summary>
        /// <remarks>
        /// This method:
        /// 1. Initializes the script executor
        /// 2. Gets all library extensions
        /// 3. For each UI extension:
        ///    - Builds the extension assembly
        ///    - Loads the assembly
        ///    - Executes startup scripts if present
        ///    - Creates the UI
        /// </remarks>
        public void LoadSession()
        {
            var totalStopwatch = Stopwatch.StartNew();
            var stepStopwatch = new Stopwatch();
            
            // Initialize the ScriptExecutor before executing any scripts
            stepStopwatch.Restart();
            InitializeScriptExecutor();
            _logger.Debug($"[PERF] InitializeScriptExecutor: {stepStopwatch.ElapsedMilliseconds}ms");
            
            // Get all library extensions first - they need to be available to all UI extensions
            stepStopwatch.Restart();
            var libraryExtensions = _extensionManager?.GetInstalledLibraryExtensions()?.ToList() ?? new List<ParsedExtension>();
            _logger.Debug($"[PERF] GetLibraryExtensions: {stepStopwatch.ElapsedMilliseconds}ms");
            
            // Get UI extensions
            stepStopwatch.Restart();
            var uiExtensions = _extensionManager?.GetInstalledUIExtensions()?.ToList();
            _logger.Debug($"[PERF] GetUIExtensions: {stepStopwatch.ElapsedMilliseconds}ms ({uiExtensions?.Count ?? 0} extensions)");
            
            if (uiExtensions == null || uiExtensions.Count == 0)
            {
                _logger.Warning("No UI extensions found or extension manager is null.");
                return;
            }
            
            foreach (var ext in uiExtensions)
            {
                if (ext == null)
                {
                    _logger.Warning("Skipping null extension.");
                    continue;
                }
                
                var extStopwatch = Stopwatch.StartNew();
                
                try
                {
                    stepStopwatch.Restart();
                    var assmInfo = _assemblyBuilder?.BuildExtensionAssembly(ext, libraryExtensions);
                    var buildTime = stepStopwatch.ElapsedMilliseconds;
                    
                    if (assmInfo == null)
                    {
                        _logger.Error($"Failed to build assembly for extension '{ext.Name}'.");
                        continue;
                    }
                    
                    _logger.Info($"Extension assembly created: {ext.Name}");
                    stepStopwatch.Restart();
                    _assemblyBuilder?.LoadAssembly(assmInfo);
                    var loadTime = stepStopwatch.ElapsedMilliseconds;
                    
                    _logger.Debug($"[PERF] {ext.Name} - Build: {buildTime}ms, Load: {loadTime}ms");
                    
                    // Execute startup script after building assembly but before creating UI
                    // This matches the Python loader flow
                    if (!string.IsNullOrEmpty(ext.StartupScript))
                    {
                        _logger.Info($"Running startup tasks for {ext.Name}");
                        stepStopwatch.Restart();
                        ExecuteExtensionStartupScript(ext, libraryExtensions);
                        _logger.Debug($"[PERF] {ext.Name} - StartupScript: {stepStopwatch.ElapsedMilliseconds}ms");
                    }
                    
                    stepStopwatch.Restart();
                    _uiManager?.BuildUI(ext, assmInfo);
                    _logger.Debug($"[PERF] {ext.Name} - BuildUI: {stepStopwatch.ElapsedMilliseconds}ms");
                    _logger.Info($"UI created for extension: {ext.Name}");
                }
                catch (Exception ex)
                {
                    _logger.Error($"Error processing extension '{ext?.Name ?? "unknown"}': {ex.Message}");
                }
            }
            
            totalStopwatch.Stop();
            _logger.Info($"Session loaded in {totalStopwatch.ElapsedMilliseconds}ms");
        }

        private void InitializeScriptExecutor()
        {
            // Cache runtime assembly lookup - it's used by every extension
            _runtimeAssembly = FindRuntimeAssembly() 
                ?? throw new InvalidOperationException("Could not find PyRevit runtime assembly");

            var scriptExecutorType = _runtimeAssembly.GetType("PyRevitLabs.PyRevit.Runtime.ScriptExecutor")
                ?? throw new InvalidOperationException("Could not find ScriptExecutor type");

            var initializeMethod = scriptExecutorType.GetMethod("Initialize", BindingFlags.Public | BindingFlags.Static)
                ?? throw new InvalidOperationException("Could not find ScriptExecutor.Initialize method");

            initializeMethod.Invoke(null, null);
            
            // Cache bin directory and pyRevit root for repeated use
            _binDir = System.IO.Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            
            // Cache reflection types and methods for startup script execution - HUGE performance boost
            _scriptDataType = _runtimeAssembly.GetType("PyRevitLabs.PyRevit.Runtime.ScriptData");
            _scriptRuntimeConfigsType = _runtimeAssembly.GetType("PyRevitLabs.PyRevit.Runtime.ScriptRuntimeConfigs");
            _scriptExecutorType = _runtimeAssembly.GetType("PyRevitLabs.PyRevit.Runtime.ScriptExecutor");
            _scriptExecutorConfigsType = _runtimeAssembly.GetType("PyRevitLabs.PyRevit.Runtime.ScriptExecutorConfigs");
            
            if (_scriptDataType != null && _scriptRuntimeConfigsType != null && _scriptExecutorType != null && _scriptExecutorConfigsType != null)
            {
                _executeScriptMethod = _scriptExecutorType.GetMethod("ExecuteScript",
                    new Type[] { _scriptDataType, _scriptRuntimeConfigsType, _scriptExecutorConfigsType });
            }
            
            var externalCommandDataType = typeof(Autodesk.Revit.UI.ExternalCommandData);
            _externalCommandDataAppProperty = externalCommandDataType.GetProperty("Application");
        }

        private Assembly? FindRuntimeAssembly()
        {
            // Use cached assembly lookup - much faster than scanning AppDomain every time
            var assembly = AssemblyCache.GetByPrefix("pyRevitLabs.PyRevit.Runtime");
            if (assembly != null)
                return assembly;
            
            // If not found in cache, try to load from the bin directory
            var binDir = System.IO.Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            if (!string.IsNullOrEmpty(binDir))
            {
                var runtimeDlls = System.IO.Directory.GetFiles(binDir, "pyRevitLabs.PyRevit.Runtime*.dll");
                if (runtimeDlls.Length > 0)
                {
                    var loaded = Assembly.LoadFrom(runtimeDlls[0]);
                    AssemblyCache.Add(loaded); // Add to cache for future lookups
                    return loaded;
                }
            }
            
            return null;
        }

        private void ExecuteExtensionStartupScript(ParsedExtension extension, List<ParsedExtension> libraryExtensions)
        {
            if (string.IsNullOrEmpty(extension.StartupScript))
                return;
            
            try
            {
                // Validate cached types
                if (_scriptDataType == null || _scriptRuntimeConfigsType == null || _executeScriptMethod == null)
                {
                    throw new Exception("Reflection types not properly cached during initialization");
                }
                
                // Build search paths for the startup script
                var searchPaths = BuildSearchPaths(extension, libraryExtensions);
                
                // Create ScriptData
                var scriptData = CreateScriptData(extension);
                
                // Create ScriptRuntimeConfigs
                var scriptRuntimeConfigs = CreateScriptRuntimeConfigs(searchPaths);
                
                // Execute the script using cached method
                if (scriptData == null || scriptRuntimeConfigs == null || _executeScriptMethod == null)
                {
                    throw new Exception("One or more required objects is null");
                }
                
                try
                {
                    _logger.Info($"Executing startup script for extension: {extension.Name}");
                    
                    var result = _executeScriptMethod.Invoke(null, new[] { scriptData, scriptRuntimeConfigs, null });
                    
                    // Check if the script execution succeeded (result code 0 = success)
                    if (result != null && (int)result != 0)
                    {
                        _logger.Warning($"Startup script returned non-zero result for extension: {extension.Name}, result: {result}");
                    }
                    else
                    {
                        _logger.Debug($"Startup script completed successfully for extension: {extension.Name}");
                    }
                }
                catch (System.Reflection.TargetInvocationException tie)
                {
                    var ex = tie.InnerException ?? tie;
                    _logger.Error($"Startup script failed for extension: {extension.Name}: {ex.Message}");
                    throw ex;
                }
            }
            catch (Exception ex)
            {
                _logger.Error($"Startup script '{extension?.Name}' failed: {ex.Message}");
                Trace.WriteLine($"Startup script '{extension?.Name}' failed: {ex}");
            }
        }

        /// <summary>
        /// Builds the search paths for a startup script, including extension lib folders and pyRevit core paths.
        /// </summary>
        /// <param name="extension">The extension for which to build search paths.</param>
        /// <param name="libraryExtensions">List of library extensions to include.</param>
        /// <returns>List of search paths.</returns>
        private List<string> BuildSearchPaths(ParsedExtension extension, List<ParsedExtension> libraryExtensions)
        {
            var searchPaths = new List<string> { extension.Directory };
            
            // Add extension's lib folder if it exists (cached)
            var extLibPath = System.IO.Path.Combine(extension.Directory, "lib");
            if (DirectoryExistsCached(extLibPath))
            {
                searchPaths.Insert(0, extLibPath);
            }
            
            // Add library extension paths (cached)
            foreach (var libExt in libraryExtensions)
            {
                var libExtLibPath = System.IO.Path.Combine(libExt.Directory, "lib");
                if (DirectoryExistsCached(libExtLibPath))
                {
                    searchPaths.Add(libExtLibPath);
                }
            }
            
            // Add core pyRevit paths (pyrevitlib + site-packages) by discovering repo root
            // Cache the root lookup - it's the same for all extensions
            if (_pyRevitRoot == null)
            {
                _pyRevitRoot = FindPyRevitRoot(extension.Directory, _binDir) ?? string.Empty;
            }
            
            if (!string.IsNullOrEmpty(_pyRevitRoot))
            {
                var pyRevitLibDir = System.IO.Path.Combine(_pyRevitRoot, Constants.PYREVIT_LIB_DIR);
                if (DirectoryExistsCached(pyRevitLibDir))
                {
                    searchPaths.Add(pyRevitLibDir);
                }

                var sitePackagesDir = System.IO.Path.Combine(_pyRevitRoot, Constants.SITE_PACKAGES_DIR);
                if (DirectoryExistsCached(sitePackagesDir))
                {
                    searchPaths.Add(sitePackagesDir);
                }
            }
            
            return searchPaths;
        }

        /// <summary>
        /// Creates a ScriptData object for executing a startup script.
        /// </summary>
        /// <param name="extension">The extension containing the startup script.</param>
        /// <returns>The created ScriptData object.</returns>
        private object CreateScriptData(ParsedExtension extension)
        {
            if (_scriptDataType == null)
                throw new InvalidOperationException("ScriptData type not initialized");
                
            var scriptData = Activator.CreateInstance(_scriptDataType)
                ?? throw new InvalidOperationException("Failed to create ScriptData instance");
            SetMemberValue(_scriptDataType, scriptData, "ScriptPath", extension.StartupScript);
            SetMemberValue(_scriptDataType, scriptData, "ConfigScriptPath", null);
            SetMemberValue(_scriptDataType, scriptData, "CommandUniqueId", string.Empty);
            SetMemberValue(_scriptDataType, scriptData, "CommandName", $"Starting {extension.Name}");
            SetMemberValue(_scriptDataType, scriptData, "CommandBundle", string.Empty);
            SetMemberValue(_scriptDataType, scriptData, "CommandExtension", extension.Name);
            SetMemberValue(_scriptDataType, scriptData, "HelpSource", string.Empty);
            return scriptData;
        }

        /// <summary>
        /// Creates a ScriptRuntimeConfigs object for executing a startup script.
        /// </summary>
        /// <param name="searchPaths">The search paths to include in the configuration.</param>
        /// <returns>The created ScriptRuntimeConfigs object.</returns>
        private object CreateScriptRuntimeConfigs(List<string> searchPaths)
        {
            // Create temporary ExternalCommandData
#if NETFRAMEWORK
            var tmpCommandData = System.Runtime.Serialization.FormatterServices
                .GetUninitializedObject(typeof(Autodesk.Revit.UI.ExternalCommandData));
#else
            var tmpCommandData = System.Runtime.CompilerServices.RuntimeHelpers
                .GetUninitializedObject(typeof(Autodesk.Revit.UI.ExternalCommandData));
#endif
                
            if (_externalCommandDataAppProperty == null)
                throw new Exception("Could not find Application property on ExternalCommandData");
                
            _externalCommandDataAppProperty.SetValue(tmpCommandData, _uiApp);
            
            // Create ScriptRuntimeConfigs using cached type
            if (_scriptRuntimeConfigsType == null)
                throw new InvalidOperationException("ScriptRuntimeConfigs type not initialized");
                
            var scriptRuntimeConfigs = Activator.CreateInstance(_scriptRuntimeConfigsType)
                ?? throw new InvalidOperationException("Failed to create ScriptRuntimeConfigs instance");
            SetMemberValue(_scriptRuntimeConfigsType, scriptRuntimeConfigs, "UIApp", _uiApp);
            SetMemberValue(_scriptRuntimeConfigsType, scriptRuntimeConfigs, "CommandData", tmpCommandData);
            SetMemberValue(_scriptRuntimeConfigsType, scriptRuntimeConfigs, "SelectedElements", null);
            
            // Set search paths as List<string>
            var listType = typeof(List<string>);
            var searchPathsList = Activator.CreateInstance(listType, new object[] { searchPaths });
            SetMemberValue(_scriptRuntimeConfigsType, scriptRuntimeConfigs, "SearchPaths", searchPathsList);
            
            // Set empty arguments
            var argumentsList = Activator.CreateInstance(listType, new object[] { new string[0] });
            SetMemberValue(_scriptRuntimeConfigsType, scriptRuntimeConfigs, "Arguments", argumentsList);
            
            // Set engine configs for persistent, clean, full-frame IronPython engine (JSON string)
            var engineConfigsJson = "{\"clean\": true, \"full_frame\": true, \"persistent\": true}";
            SetMemberValue(_scriptRuntimeConfigsType, scriptRuntimeConfigs, "EngineConfigs", engineConfigsJson);
            
            SetMemberValue(_scriptRuntimeConfigsType, scriptRuntimeConfigs, "RefreshEngine", false);
            SetMemberValue(_scriptRuntimeConfigsType, scriptRuntimeConfigs, "ConfigMode", false);
            SetMemberValue(_scriptRuntimeConfigsType, scriptRuntimeConfigs, "DebugMode", false);
            SetMemberValue(_scriptRuntimeConfigsType, scriptRuntimeConfigs, "ExecutedFromUI", false);
            
            return scriptRuntimeConfigs;
        }

        private static void SetMemberValue(Type targetType, object? instance, string memberName, object? value)
        {
            if (instance == null)
                throw new ArgumentNullException(nameof(instance));
                
            var property = targetType.GetProperty(memberName, BindingFlags.Public | BindingFlags.Instance);
            if (property != null)
            {
                property.SetValue(instance, value);
                return;
            }

            var field = targetType.GetField(memberName, BindingFlags.Public | BindingFlags.Instance);
            if (field != null)
            {
                field.SetValue(instance, value);
                return;
            }

            throw new Exception($"Could not find member '{memberName}' on type {targetType.FullName}");
        }

        private bool DirectoryExistsCached(string path)
        {
            if (string.IsNullOrEmpty(path))
                return false;
                
            if (!_directoryExistsCache.TryGetValue(path, out bool exists))
            {
                exists = System.IO.Directory.Exists(path);
                _directoryExistsCache[path] = exists;
            }
            return exists;
        }
        
        private static string? FindPyRevitRoot(params string?[] hintPaths)
        {
            foreach (var hint in hintPaths)
            {
                if (string.IsNullOrEmpty(hint))
                    continue;

                var current = new System.IO.DirectoryInfo(hint);
                while (current != null)
                {
                    var pyRevitMarker = System.IO.Path.Combine(current.FullName, Constants.PYREVIT_MARKER_FILE);
                    var pyRevitLibDir = System.IO.Path.Combine(current.FullName, Constants.PYREVIT_LIB_DIR);
                    if (System.IO.File.Exists(pyRevitMarker) || System.IO.Directory.Exists(pyRevitLibDir))
                        return current.FullName;

                    current = current.Parent;
                }
            }

            return null;
        }
    }
}