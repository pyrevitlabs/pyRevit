#nullable enable
using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using Autodesk.Revit.UI;
using pyRevitExtensionParser;
using pyRevitLabs.NLog;
using AdwRibbonCheckBox = Autodesk.Windows.RibbonCheckBox;

namespace pyRevitAssemblyBuilder.UIManager
{
    /// <summary>
    /// State and metadata of a .checkbox bundle, passed as <c>ctx</c> to its script's handlers.
    /// </summary>
    /// <remarks>
    /// Note: member names are snake_case because Python handlers read them directly, matching
    /// <see cref="ComboBoxContext"/>.
    /// </remarks>
    public class CheckBoxContext
    {
        private readonly ParsedComponent _component;

        /// <summary>
        /// Initializes a new instance of the <see cref="CheckBoxContext"/> class.
        /// </summary>
        public CheckBoxContext(AdwRibbonCheckBox checkBox, ParsedComponent component, UIApplication uiApp)
        {
            checkbox = checkBox;
            _component = component;
            uiapp = uiApp;
        }

        public AdwRibbonCheckBox checkbox { get; }

        /// <summary>
        /// Gets or sets the checked state.
        /// </summary>
        /// <remarks>
        /// Warning: setting a new value raises <c>__chk_on_change__</c> the same way a click does,
        /// so a change handler that sets it calls itself again. Inside <c>__chk_init__</c> it does not,
        /// because the change handler is attached only after <c>__chk_init__</c> returns.
        /// </remarks>
        public bool is_checked
        {
            get => checkbox.IsChecked == true;
            set => checkbox.IsChecked = value;
        }

        public string text
        {
            get => checkbox.Text;
            set => checkbox.Text = value;
        }

        public bool enabled
        {
            get => checkbox.IsEnabled;
            set => checkbox.IsEnabled = value;
        }

        public bool visible
        {
            get => checkbox.IsVisible;
            set => checkbox.IsVisible = value;
        }

        public UIApplication uiapp { get; }

        public string directory => _component?.Directory ?? string.Empty;

        /// <summary>Gets the bundle folder name without its suffix or spaces, such as <c>TestCheckBox</c>.</summary>
        public string name => _component?.Name ?? string.Empty;

        /// <summary>Gets the bundle folder name without its suffix, such as <c>Test CheckBox</c>.</summary>
        public string display_name => _component?.DisplayName ?? string.Empty;

        /// <summary>Gets a dictionary handlers can use to keep data between calls until the next reload.</summary>
        /// <remarks>
        /// Note: it is a .NET dictionary, as on <see cref="ComboBoxContext"/>, not a Python dict. On
        /// IronPython 2.7 it has no <c>get</c> or <c>setdefault</c>, so handlers check keys with
        /// <c>ContainsKey</c> and read them by index.
        /// </remarks>
        public Dictionary<string, object> user_data { get; } = new Dictionary<string, object>();
    }

    /// <summary>
    /// Runs a .checkbox bundle's <c>script.py</c> through <c>PyRevitLoader.CheckBoxExecutor</c>.
    /// </summary>
    /// <remarks>
    /// The executor lives in the IronPython-specific pyRevitLoader assembly, which this assembly
    /// cannot reference, so it is created and called through reflection.
    /// Invariant: <see cref="ExecutorTypeName"/> and the <c>ExecuteEventHandlerSetup</c> and
    /// <c>ReleasePreviousSession</c> signatures must match <c>dev/pyRevitLoader/Source/CheckBoxExecutor.cs</c>.
    /// </remarks>
    public class CheckBoxScriptInitializer
    {
        private const string ExecutorTypeName = "PyRevitLoader.CheckBoxExecutor";

        private static readonly Logger nlog = LogManager.GetCurrentClassLogger();
        private readonly SessionManager.ILogger _logger;
        private readonly UIApplication _uiApp;
        private readonly Type? _executorType;
        private readonly Lazy<List<string>> _libraryExtensionPaths;
        private object? _executor;
        private MethodInfo? _executeMethod;

        /// <summary>
        /// Initializes a new instance of the <see cref="CheckBoxScriptInitializer"/> class.
        /// </summary>
        /// <param name="libraryPathsProvider">Supplies the search paths of the installed library extensions; read once, on first use.</param>
        /// <remarks>
        /// Important: construct exactly one per session load. Construction releases the handlers
        /// and engine of the previous load, even when this load has no checkboxes.
        /// </remarks>
        public CheckBoxScriptInitializer(
            UIApplication uiApp,
            SessionManager.ILogger logger,
            Func<IEnumerable<string>>? libraryPathsProvider = null)
        {
            _uiApp = uiApp;
            _logger = logger;
            _libraryExtensionPaths = new Lazy<List<string>>(
                () => new List<string>(libraryPathsProvider?.Invoke() ?? Array.Empty<string>()));
            _executorType = SessionManager.AssemblyCache.GetByPrefix("pyRevitLoader")?.GetType(ExecutorTypeName);
            ReleasePreviousSessionExecutor();
        }

        /// <summary>
        /// Runs the bundle's script and wires its handlers to <paramref name="checkBox"/>.
        /// </summary>
        /// <returns>False when the bundle has a script and the executor is unavailable or the script fails; true otherwise, including when the bundle has no script.</returns>
        /// <remarks>
        /// The script can import from the bundle's ancestor <c>lib</c> folders and from installed library
        /// extensions, and it gets the identity values a command gets (<c>__commandname__</c> and the rest)
        /// in its own module scope, so <c>EXEC_PARAMS</c> resolves each checkbox separately, also in a
        /// handler imported from another module, because the executor calls handlers through a function
        /// defined with the same values. <c>__scriptruntime__</c> is None there because a handler call is
        /// not a command run.
        /// Note: the executor is called even for a bundle without a script, so it can drop the handler an
        /// earlier bundle wired on the same control.
        /// </remarks>
        public bool ExecuteEventHandlerSetup(ParsedComponent component, AdwRibbonCheckBox checkBox)
        {
            var scriptPath = FindScriptPath(component);
            if (scriptPath == null)
                _logger.Debug($"No script.py found for CheckBox '{component.DisplayName}'.");

            if (!EnsureExecutor())
                return scriptPath == null;

            var context = new CheckBoxContext(checkBox, component, _uiApp);
            var searchPaths = CollectLibPaths(component);
            searchPaths.AddRange(_libraryExtensionPaths.Value);
            try
            {
                var result = _executeMethod!.Invoke(
                    _executor,
                    new object?[] { scriptPath, context, checkBox, searchPaths, ScriptIdentityScope.Build(component) });
                ExecutorFailure.ReportIfFailed(_executor!, "CheckBox", component.DisplayName, _logger);
                return result is bool succeeded ? succeeded : true;
            }
            catch (TargetInvocationException ex)
            {
                _logger.Error($"Error setting up CheckBox event handlers: {ex.InnerException?.Message ?? ex.Message}");
                return false;
            }
        }

        private void ReleasePreviousSessionExecutor()
        {
            try
            {
                Action<string> onError = message => nlog.Warn(message);
                _executorType?.GetMethod("ReleasePreviousSession", BindingFlags.Public | BindingFlags.Static)
                    ?.Invoke(null, new object[] { onError });
            }
            catch (Exception ex)
            {
                nlog.Warn($"Failed to release the previous session's CheckBox executor: {ex.Message}");
            }
        }

        private bool EnsureExecutor()
        {
            if (_executor != null && _executeMethod != null)
                return true;

            if (_executorType == null)
            {
                _logger.Warning($"PyRevitLoader assembly or {ExecutorTypeName} type not found.");
                return false;
            }

            try
            {
                Action<string> logAction = message => nlog.Info(message);
                _executor = Activator.CreateInstance(_executorType, _uiApp, logAction);
                _executeMethod = _executorType.GetMethod("ExecuteEventHandlerSetup");
                return _executor != null && _executeMethod != null;
            }
            catch (Exception ex)
            {
                _logger.Error($"Failed to create {ExecutorTypeName}: {ex.Message}");
                return false;
            }
        }

        private static string? FindScriptPath(ParsedComponent component)
        {
            if (string.IsNullOrEmpty(component.Directory))
                return null;

            var scriptPath = Path.Combine(component.Directory, "script.py");
            if (File.Exists(scriptPath))
                return scriptPath;

            var componentScript = component.ScriptPath;
            if (!string.IsNullOrEmpty(componentScript) &&
                componentScript.EndsWith(".py", StringComparison.OrdinalIgnoreCase) &&
                File.Exists(componentScript))
                return componentScript;

            return null;
        }

        private static List<string> CollectLibPaths(ParsedComponent component)
        {
            var libPaths = new List<string>();
            if (string.IsNullOrEmpty(component.Directory))
                return libPaths;

            var current = new DirectoryInfo(component.Directory);
            while (current != null)
            {
                var libPath = Path.Combine(current.FullName, "lib");
                if (Directory.Exists(libPath) && !libPaths.Contains(libPath))
                    libPaths.Add(libPath);

                if (current.Name.EndsWith(".extension", StringComparison.OrdinalIgnoreCase))
                    break;
                current = current.Parent;
            }

            return libPaths;
        }
    }
}
