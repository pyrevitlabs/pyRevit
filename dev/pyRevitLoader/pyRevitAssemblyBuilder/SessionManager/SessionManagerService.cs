using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Reflection;
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitExtensionParser;
using pyRevitLabs.NLog;

namespace pyRevitAssemblyBuilder.SessionManager
{
    public class SessionManagerService
    {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();
        
        private readonly AssemblyBuilderService _assemblyBuilder;
        private readonly ExtensionManagerService _extensionManager;
        private readonly HookManager _hookManager;
        private readonly UIManagerService _uiManager;
        private readonly UIApplication _uiApp;
        private readonly object _outputWindow;
        private Assembly _runtimeAssembly;
        private string _pyRevitRoot;
        private string _binDir;
        private Type _scriptDataType;
        private Type _scriptRuntimeConfigsType;
        private Type _scriptExecutorType;
        private Type _scriptExecutorConfigsType;
        private MethodInfo _executeScriptMethod;
        private PropertyInfo _externalCommandDataAppProperty;
        private Dictionary<string, bool> _directoryExistsCache = new Dictionary<string, bool>();

        public SessionManagerService(
            AssemblyBuilderService assemblyBuilder,
            ExtensionManagerService extensionManager,
            HookManager hookManager,
            UIManagerService uiManager,
            object outputWindow = null)
        {
            _assemblyBuilder = assemblyBuilder;
            _extensionManager = extensionManager;
            _hookManager = hookManager;
            _uiManager = uiManager;
            _outputWindow = outputWindow;
            
            // Get UIApplication from UIManagerService
            var uiAppField = typeof(UIManagerService).GetField("_uiApp", 
                BindingFlags.NonPublic | BindingFlags.Instance);
            _uiApp = (UIApplication)uiAppField?.GetValue(uiManager);
            
            // Redirect Console.Out to the output window's stream if provided
            if (_outputWindow != null)
            {
                RedirectConsoleToOutputWindow();
            }
        }

        private void RedirectConsoleToOutputWindow()
        {
            try
            {
                // Get the OutputStream property from the output window
                var outputStreamProperty = _outputWindow.GetType().GetProperty("OutputStream");
                if (outputStreamProperty != null)
                {
                    var outputStream = outputStreamProperty.GetValue(_outputWindow);
                    if (outputStream != null)
                    {
                        // Redirect Console.Out to the output stream
                        var streamWriter = new System.IO.StreamWriter((System.IO.Stream)outputStream);
                        streamWriter.AutoFlush = true;
                        Console.SetOut(streamWriter);
                        
                        // Configure NLog to write to the same output stream
                        ConfigureNLogForOutputWindow();
                        
                        Trace.WriteLine("Console output and NLog redirected to output window stream");
                    }
                }
            }
            catch (Exception ex)
            {
                Trace.WriteLine($"Failed to redirect console output: {ex.Message}");
            }
        }
        
        private void ConfigureNLogForOutputWindow()
        {
            try
            {
                // Create a new NLog configuration that writes to Console.Out (which we just redirected)
                var config = new pyRevitLabs.NLog.Config.LoggingConfiguration();
                
                // Create a console target that writes to Console.Out
                var consoleTarget = new pyRevitLabs.NLog.Targets.ConsoleTarget("console")
                {
                    Layout = "${level:uppercase=true}: [${logger}] ${message}"
                };
                
                config.AddTarget(consoleTarget);
                config.AddRuleForAllLevels(consoleTarget);
                
                // Apply the configuration to LogManager
                pyRevitLabs.NLog.LogManager.Configuration = config;
                
                Trace.WriteLine("NLog configured to write to output window");
            }
            catch (Exception ex)
            {
                Trace.WriteLine($"Failed to configure NLog: {ex.Message}");
            }
        }

        public void LoadSession()
        {
            // Initialize the ScriptExecutor before executing any scripts
            InitializeScriptExecutor();
            
            // Get all library extensions first - they need to be available to all UI extensions
            var libraryExtensions = _extensionManager.GetInstalledLibraryExtensions().ToList();
            
            // Get UI extensions
            var uiExtensions = _extensionManager.GetInstalledUIExtensions();

            foreach (var ext in uiExtensions)
            {
                var assmInfo = _assemblyBuilder.BuildExtensionAssembly(ext, libraryExtensions);
                _assemblyBuilder.LoadAssembly(assmInfo);
                logger.Info($"Extension assembly created: {ext.Name}");
                
                // Execute startup script after building assembly but before creating UI
                // This matches the Python loader flow
                if (!string.IsNullOrEmpty(ext.StartupScript))
                {
                    logger.Info($"Running startup tasks for {ext.Name}");
                    ExecuteExtensionStartupScript(ext, libraryExtensions);
                }
                
                _uiManager.BuildUI(ext, assmInfo);
                logger.Info($"UI created for extension: {ext.Name}");
                // _hookManager.RegisterHooks(ext);
            }
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
            
            if (_scriptDataType != null && _scriptRuntimeConfigsType != null && _scriptExecutorType != null)
            {
                _executeScriptMethod = _scriptExecutorType.GetMethod("ExecuteScript",
                    new[] { _scriptDataType, _scriptRuntimeConfigsType, _scriptExecutorConfigsType });
            }
            
            var externalCommandDataType = typeof(Autodesk.Revit.UI.ExternalCommandData);
            _externalCommandDataAppProperty = externalCommandDataType.GetProperty("Application");
        }

        private Assembly FindRuntimeAssembly()
        {
            // Search through all loaded assemblies for the PyRevit Runtime assembly
            foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                var name = assembly.GetName().Name;
                if (name != null && name.StartsWith("pyRevitLabs.PyRevit.Runtime"))
                {
                    return assembly;
                }
            }
            
            // If not found in loaded assemblies, try to load from the bin directory
            var binDir = System.IO.Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            var runtimeDlls = System.IO.Directory.GetFiles(binDir, "pyRevitLabs.PyRevit.Runtime*.dll");
            if (runtimeDlls.Length > 0)
            {
                return Assembly.LoadFrom(runtimeDlls[0]);
            }
            
            return null;
        }

        private void ExecuteExtensionStartupScript(ParsedExtension extension, List<ParsedExtension> libraryExtensions)
        {
            if (string.IsNullOrEmpty(extension.StartupScript))
                return;
            
            try
            {
                // Build search paths for the startup script
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
                    var pyRevitLibDir = System.IO.Path.Combine(_pyRevitRoot, "pyrevitlib");
                    if (DirectoryExistsCached(pyRevitLibDir))
                    {
                        searchPaths.Add(pyRevitLibDir);
                    }

                    var sitePackagesDir = System.IO.Path.Combine(_pyRevitRoot, "site-packages");
                    if (DirectoryExistsCached(sitePackagesDir))
                    {
                        searchPaths.Add(sitePackagesDir);
                    }
                }

                // Validate cached types
                if (_scriptDataType == null || _scriptRuntimeConfigsType == null || _executeScriptMethod == null)
                {
                    throw new Exception("Reflection types not properly cached during initialization");
                }
                
                // Create ScriptData using cached type
                var scriptData = Activator.CreateInstance(_scriptDataType);
                SetMemberValue(_scriptDataType, scriptData, "ScriptPath", extension.StartupScript);
                SetMemberValue(_scriptDataType, scriptData, "ConfigScriptPath", null);
                SetMemberValue(_scriptDataType, scriptData, "CommandUniqueId", string.Empty);
                SetMemberValue(_scriptDataType, scriptData, "CommandName", $"Starting {extension.Name}");
                SetMemberValue(_scriptDataType, scriptData, "CommandBundle", string.Empty);
                SetMemberValue(_scriptDataType, scriptData, "CommandExtension", extension.Name);
                SetMemberValue(_scriptDataType, scriptData, "HelpSource", string.Empty);
                // Create temporary ExternalCommandData using cached property
                var tmpCommandData = System.Runtime.Serialization.FormatterServices
                    .GetUninitializedObject(typeof(Autodesk.Revit.UI.ExternalCommandData));
                    
                if (_externalCommandDataAppProperty == null)
                    throw new Exception("Could not find Application property on ExternalCommandData");
                    
                _externalCommandDataAppProperty.SetValue(tmpCommandData, _uiApp);
                // Create ScriptRuntimeConfigs using cached type
                var scriptRuntimeConfigs = Activator.CreateInstance(_scriptRuntimeConfigsType);
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
                
                // Execute the script using cached method
                if (scriptData == null || scriptRuntimeConfigs == null || _executeScriptMethod == null)
                {
                    throw new Exception("One or more required objects is null");
                }
                
                try
                {
                    logger.Info($"Executing startup script for extension: {extension.Name}");
                    _executeScriptMethod.Invoke(null, new[] { scriptData, scriptRuntimeConfigs, null });
                    logger.Info($"Startup script completed for extension: {extension.Name}");
                }
                catch (System.Reflection.TargetInvocationException tie)
                {
                    var ex = tie.InnerException ?? tie;
                    logger.Error(ex, $"Startup script failed for extension: {extension.Name}");
                    throw ex;
                }
            }
            catch (Exception ex)
            {
                logger.Error(ex, $"Startup script '{extension?.Name}' failed");
                Trace.WriteLine($"Startup script '{extension?.Name}' failed: {ex}");
            }
        }

        private static void SetMemberValue(Type targetType, object instance, string memberName, object value)
        {
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
        
        private static string FindPyRevitRoot(params string[] hintPaths)
        {
            foreach (var hint in hintPaths)
            {
                if (string.IsNullOrEmpty(hint))
                    continue;

                var current = new System.IO.DirectoryInfo(hint);
                while (current != null)
                {
                    var pyRevitMarker = System.IO.Path.Combine(current.FullName, "pyRevitfile");
                    var pyRevitLibDir = System.IO.Path.Combine(current.FullName, "pyrevitlib");
                    if (System.IO.File.Exists(pyRevitMarker) || System.IO.Directory.Exists(pyRevitLibDir))
                        return current.FullName;

                    current = current.Parent;
                }
            }

            return null;
        }
    }
}