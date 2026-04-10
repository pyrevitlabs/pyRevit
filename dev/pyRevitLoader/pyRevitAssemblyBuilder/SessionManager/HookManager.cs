#nullable enable
using pyRevitExtensionParser;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.RegularExpressions;

namespace pyRevitAssemblyBuilder.SessionManager
{
    public class HookManager : IHookManager
    {
        private readonly ILogger _logger;

        // Matches Python SUPPORTED_LANGUAGES: .py, .cs, .vb
        private static readonly HashSet<string> SupportedLanguages = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            ".py", ".cs", ".vb"
        };

        // Matches Python _get_hook_parts regex:
        //   r'([a-z -]+)\[?([A-Z _]+)?\]?\..+'
        // Group 1: hook event name (e.g., "doc-opened", "command-before-exec")
        // Group 2: optional target in brackets (e.g., "ID_INPLACE_COMPONENT")
        private static readonly Regex HookPartsRegex = new Regex(
            @"^([a-z -]+)\[?([A-Z _]+)?\]?\..+$",
            RegexOptions.Compiled);

        // Cached reflection members for EventHooks.RegisterHook()
        private Type? _eventHooksType;
        private MethodInfo? _registerHookMethod;
        private object? _eventHooksInstance;

        public HookManager(ILogger logger)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
        }

        /// <summary>
        /// Registers hooks for the specified extension.
        /// Replicates Python hooks.register_hooks() → EventHooks.RegisterHook().
        /// See: pyrevitlib/pyrevit/loader/hooks.py
        /// </summary>
        public void RegisterHooks(
            ParsedExtension extension,
            List<ParsedExtension> libraryExtensions,
            Assembly runtimeAssembly,
            string? pyRevitRoot)
        {
            if (extension == null) return;

            var hooksDir = Path.Combine(extension.Directory, "hooks");
            if (!Directory.Exists(hooksDir))
            {
                _logger.Debug($"No hooks directory for extension '{extension.Name}'");
                return;
            }

            // Initialize reflection targets on first call
            if (_eventHooksType == null)
            {
                InitializeReflection(runtimeAssembly);
            }

            if (_registerHookMethod == null || _eventHooksInstance == null)
            {
                _logger.Warning("Cannot register hooks: EventHooks reflection initialization failed.");
                return;
            }

            // Build search paths for hook scripts (same paths hooks get at execution time)
            var searchPaths = BuildHookSearchPaths(extension, libraryExtensions, pyRevitRoot);

            // Discover and register each hook script
            var hookScripts = Directory.GetFiles(hooksDir);
            foreach (var hookScript in hookScripts)
            {
                try
                {
                    var ext = Path.GetExtension(hookScript);
                    if (!SupportedLanguages.Contains(ext))
                        continue;

                    var fileName = Path.GetFileName(hookScript);
                    if (!TryParseHookFileName(fileName, out var eventName, out var eventTarget))
                    {
                        _logger.Debug($"Hook script '{fileName}' does not match naming convention — skipped.");
                        continue;
                    }

                    // Build hook unique ID matching Python _create_hook_id():
                    //   cleanup_string(UNIQUE_ID_SEPARATOR.join([ext.unique_name, basename(hook_script)]), skip=['_']).lower()
                    var hookId = CreateHookId(extension, fileName);

                    // Call EventHooks.RegisterHook() via reflection
                    _registerHookMethod.Invoke(_eventHooksInstance, new object[]
                    {
                        hookId,                   // uniqueId
                        eventName,                // eventName
                        eventTarget,              // eventTarget
                        hookScript,               // scriptPath (full path)
                        searchPaths,              // searchPaths (string[])
                        extension.Name            // extensionName
                    });

                    _logger.Debug($"Registered hook: {hookId} ({eventName}) for extension '{extension.Name}'");
                }
                catch (Exception ex)
                {
                    _logger.Error($"Failed registering hook script {hookScript} | {ex.Message}");
                }
            }
        }

        /// <summary>
        /// Parses a hook script basename using the same rules as Python hooks._get_hook_parts().
        /// </summary>
        /// <param name="fileName">Basename only (e.g. doc-opened.py).</param>
        internal static bool TryParseHookFileName(string fileName, out string eventName, out string eventTarget)
        {
            eventName = "";
            eventTarget = "";
            var match = HookPartsRegex.Match(fileName);
            if (!match.Success)
                return false;
            eventName = match.Groups[1].Value;
            eventTarget = match.Groups[2].Success ? match.Groups[2].Value : "";
            return true;
        }

        /// <summary>
        /// Creates a hook unique ID matching the legacy Python _create_hook_id().
        /// Format: cleanup_string("{extension.unique_name}_{hook_filename}", skip=['_']).lower()
        /// </summary>
        internal static string CreateHookId(ParsedExtension extension, string hookFileName)
        {
            // extension.UniqueId is already the sanitized unique name (from ExtensionParser)
            // Join with '_' separator, then sanitize the hook filename part
            var pieces = extension.UniqueId + "_" + hookFileName;

            // SanitizeClassName replicates cleanup_string(skip=['_'])
            return ExtensionParser.SanitizeClassName(pieces).ToLowerInvariant();
        }

        /// <summary>
        /// Builds search paths for hook script execution.
        /// Matches Python hooks.register_hooks() which passes extension.module_paths.
        /// module_paths = [extension.lib/, extension.bin/] + library extension lib/ paths.
        /// </summary>
        internal string[] BuildHookSearchPaths(
            ParsedExtension extension,
            List<ParsedExtension> libraryExtensions,
            string? pyRevitRoot)
        {
            var paths = new List<string>();

            // Extension's own lib/ directory
            var extLib = Path.Combine(extension.Directory, "lib");
            if (Directory.Exists(extLib))
                paths.Add(extLib);

            // Extension's own bin/ directory
            var extBin = Path.Combine(extension.Directory, "bin");
            if (Directory.Exists(extBin))
                paths.Add(extBin);

            // Library extensions' lib/ directories
            if (libraryExtensions != null)
            {
                foreach (var libExt in libraryExtensions)
                {
                    var libExtLib = Path.Combine(libExt.Directory, "lib");
                    if (Directory.Exists(libExtLib))
                        paths.Add(libExtLib);
                }
            }

            // Core pyRevit paths (pyrevitlib + site-packages)
            if (!string.IsNullOrEmpty(pyRevitRoot))
            {
                var pyRevitLibDir = Path.Combine(pyRevitRoot, "pyrevitlib");
                if (Directory.Exists(pyRevitLibDir))
                    paths.Add(pyRevitLibDir);

                var sitePackagesDir = Path.Combine(pyRevitRoot, "site-packages");
                if (Directory.Exists(sitePackagesDir))
                    paths.Add(sitePackagesDir);
            }

            return paths.ToArray();
        }

        /// <summary>
        /// Initializes reflection handles for EventHooks.RegisterHook().
        /// The loader assembly has no compile-time reference to the Runtime, so we
        /// use the same reflection pattern as ScriptExecutor invocation.
        /// </summary>
        private void InitializeReflection(Assembly runtimeAssembly)
        {
            try
            {
                _eventHooksType = runtimeAssembly.GetType("PyRevitLabs.PyRevit.Runtime.EventHooks");
                if (_eventHooksType == null)
                {
                    _logger.Error("Could not find EventHooks type in runtime assembly.");
                    return;
                }

                // EventHooks constructor takes a string handlerId (can be anything —
                // RegisterHook reads from AppDomain data directly, not from the instance)
                _eventHooksInstance = Activator.CreateInstance(_eventHooksType, new object[] { "CSharpLoader" });

                _registerHookMethod = _eventHooksType.GetMethod("RegisterHook", new Type[]
                {
                    typeof(string),     // uniqueId
                    typeof(string),     // eventName
                    typeof(string),     // eventTarget
                    typeof(string),     // scriptPath
                    typeof(string[]),   // searchPaths
                    typeof(string)      // extensionName
                });

                if (_registerHookMethod == null)
                {
                    _logger.Error("Could not find RegisterHook method on EventHooks type.");
                }
            }
            catch (Exception ex)
            {
                _logger.Error($"Failed to initialize EventHooks reflection: {ex.Message}");
            }
        }
    }
}