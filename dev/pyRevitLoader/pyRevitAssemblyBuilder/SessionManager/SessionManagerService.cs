using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Reflection;
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.SessionManager
{
    public class SessionManagerService
    {
        private readonly AssemblyBuilderService _assemblyBuilder;
        private readonly ExtensionManagerService _extensionManager;
        private readonly HookManager _hookManager;
        private readonly UIManagerService _uiManager;
        private readonly UIApplication _uiApp;

        public SessionManagerService(
            AssemblyBuilderService assemblyBuilder,
            ExtensionManagerService extensionManager,
            HookManager hookManager,
            UIManagerService uiManager)
        {
            _assemblyBuilder = assemblyBuilder;
            _extensionManager = extensionManager;
            _hookManager = hookManager;
            _uiManager = uiManager;
            
            // Get UIApplication from UIManagerService
            var uiAppField = typeof(UIManagerService).GetField("_uiApp", 
                BindingFlags.NonPublic | BindingFlags.Instance);
            _uiApp = (UIApplication)uiAppField?.GetValue(uiManager);
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
                
                // Execute startup script after building assembly but before creating UI
                // This matches the Python loader flow
                if (!string.IsNullOrEmpty(ext.StartupScript))
                {
                    ExecuteExtensionStartupScript(ext, libraryExtensions);
                }
                
                _uiManager.BuildUI(ext, assmInfo);
                _hookManager.RegisterHooks(ext);
            }
        }

        private void InitializeScriptExecutor()
        {
            var runtimeAssembly = FindRuntimeAssembly() 
                ?? throw new InvalidOperationException("Could not find PyRevit runtime assembly");

            var scriptExecutorType = runtimeAssembly.GetType("PyRevitLabs.PyRevit.Runtime.ScriptExecutor")
                ?? throw new InvalidOperationException("Could not find ScriptExecutor type");

            var initializeMethod = scriptExecutorType.GetMethod("Initialize", BindingFlags.Public | BindingFlags.Static)
                ?? throw new InvalidOperationException("Could not find ScriptExecutor.Initialize method");

            initializeMethod.Invoke(null, null);
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
                
                // Add extension's lib folder if it exists
                var extLibPath = System.IO.Path.Combine(extension.Directory, "lib");
                if (System.IO.Directory.Exists(extLibPath))
                {
                    searchPaths.Insert(0, extLibPath);
                }
                
                // Add library extension paths
                foreach (var libExt in libraryExtensions)
                {
                    var libExtLibPath = System.IO.Path.Combine(libExt.Directory, "lib");
                    if (System.IO.Directory.Exists(libExtLibPath))
                    {
                        searchPaths.Add(libExtLibPath);
                    }
                }
                
                // Add core pyRevit paths (pyrevitlib + site-packages) by discovering repo root
                var binDir = System.IO.Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
                var pyRevitRoot = FindPyRevitRoot(extension.Directory, binDir);
                if (!string.IsNullOrEmpty(pyRevitRoot))
                {
                    var pyRevitLibDir = System.IO.Path.Combine(pyRevitRoot, "pyrevitlib");
                    if (System.IO.Directory.Exists(pyRevitLibDir))
                    {
                        searchPaths.Add(pyRevitLibDir);
                    }

                    var sitePackagesDir = System.IO.Path.Combine(pyRevitRoot, "site-packages");
                    if (System.IO.Directory.Exists(sitePackagesDir))
                    {
                        searchPaths.Add(sitePackagesDir);
                    }
                }

                // Find the runtime assembly
                var runtimeAssembly = FindRuntimeAssembly();
                if (runtimeAssembly == null)
                {
                    throw new Exception("Could not find PyRevitLabs.PyRevit.Runtime assembly");
                }
                
                // Create ScriptData
                var scriptDataType = runtimeAssembly.GetType("PyRevitLabs.PyRevit.Runtime.ScriptData");
                if (scriptDataType == null)
                    throw new Exception("Could not find ScriptData type");
                    
                var scriptData = Activator.CreateInstance(scriptDataType);
                SetMemberValue(scriptDataType, scriptData, "ScriptPath", extension.StartupScript);
                SetMemberValue(scriptDataType, scriptData, "ConfigScriptPath", null);
                SetMemberValue(scriptDataType, scriptData, "CommandUniqueId", string.Empty);
                SetMemberValue(scriptDataType, scriptData, "CommandName", $"Starting {extension.Name}");
                SetMemberValue(scriptDataType, scriptData, "CommandBundle", string.Empty);
                SetMemberValue(scriptDataType, scriptData, "CommandExtension", extension.Name);
                SetMemberValue(scriptDataType, scriptData, "HelpSource", string.Empty);
                // Create temporary ExternalCommandData (matching Python's create_tmp_commanddata)
                
                var externalCommandDataType = typeof(Autodesk.Revit.UI.ExternalCommandData);
                var tmpCommandData = System.Runtime.Serialization.FormatterServices
                    .GetUninitializedObject(externalCommandDataType);
                    
                var appProp = externalCommandDataType.GetProperty("Application");
                if (appProp == null)
                    throw new Exception("Could not find Application property on ExternalCommandData");
                    
                appProp.SetValue(tmpCommandData, _uiApp);
                // Create ScriptRuntimeConfigs
                var scriptRuntimeConfigsType = runtimeAssembly.GetType("PyRevitLabs.PyRevit.Runtime.ScriptRuntimeConfigs");
                if (scriptRuntimeConfigsType == null)
                    throw new Exception("Could not find ScriptRuntimeConfigs type");
                    
                var scriptRuntimeConfigs = Activator.CreateInstance(scriptRuntimeConfigsType);
                SetMemberValue(scriptRuntimeConfigsType, scriptRuntimeConfigs, "UIApp", _uiApp);
                SetMemberValue(scriptRuntimeConfigsType, scriptRuntimeConfigs, "CommandData", tmpCommandData);
                SetMemberValue(scriptRuntimeConfigsType, scriptRuntimeConfigs, "SelectedElements", null);
                
                // Set search paths as List<string>
                var listType = typeof(List<string>);
                var searchPathsList = Activator.CreateInstance(listType, new object[] { searchPaths });
                SetMemberValue(scriptRuntimeConfigsType, scriptRuntimeConfigs, "SearchPaths", searchPathsList);
                
                // Set empty arguments
                var argumentsList = Activator.CreateInstance(listType, new object[] { new string[0] });
                SetMemberValue(scriptRuntimeConfigsType, scriptRuntimeConfigs, "Arguments", argumentsList);
                
                // Set engine configs for persistent, clean, full-frame IronPython engine (JSON string)
                var engineConfigsJson = "{\"clean\": true, \"full_frame\": true, \"persistent\": true}";
                SetMemberValue(scriptRuntimeConfigsType, scriptRuntimeConfigs, "EngineConfigs", engineConfigsJson);
                
                SetMemberValue(scriptRuntimeConfigsType, scriptRuntimeConfigs, "RefreshEngine", false);
                SetMemberValue(scriptRuntimeConfigsType, scriptRuntimeConfigs, "ConfigMode", false);
                SetMemberValue(scriptRuntimeConfigsType, scriptRuntimeConfigs, "DebugMode", false);
                SetMemberValue(scriptRuntimeConfigsType, scriptRuntimeConfigs, "ExecutedFromUI", false);
                
                // Execute the script
                var scriptExecutorType = runtimeAssembly.GetType("PyRevitLabs.PyRevit.Runtime.ScriptExecutor");
                var executeMethod = scriptExecutorType.GetMethod("ExecuteScript", 
                    new[] { scriptDataType, scriptRuntimeConfigsType, 
                    runtimeAssembly.GetType("PyRevitLabs.PyRevit.Runtime.ScriptExecutorConfigs") });
                    
                if (scriptData == null || scriptRuntimeConfigs == null || executeMethod == null)
                {
                    throw new Exception("One or more required objects is null");
                }
                
                try
                {
                    executeMethod.Invoke(null, new[] { scriptData, scriptRuntimeConfigs, null });
                }
                catch (System.Reflection.TargetInvocationException tie)
                {
                    throw tie.InnerException ?? tie;
                }
            }
            catch (Exception ex)
            {
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