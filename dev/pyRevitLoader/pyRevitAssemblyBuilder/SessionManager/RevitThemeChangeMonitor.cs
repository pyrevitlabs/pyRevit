#nullable enable
using System;
using System.Linq.Expressions;
using System.Reflection;
using Autodesk.Revit.UI;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Monitors Revit's application theme and requests a pyRevit UI refresh when it changes.
    /// </summary>
    public sealed class RevitThemeChangeMonitor : IDisposable
    {
        private readonly IRevitThemeSource _themeSource;
        private readonly ILogger _logger;
        private readonly Action<string> _themeChanged;
        private readonly Action _clearThemeCache;
        private string? _lastTheme;
        private string? _pendingTheme;
        private bool _sessionReady;
        private bool _started;
        private bool _disposed;

        /// <summary>
        /// Creates a monitor for the supplied Revit UI application.
        /// </summary>
        public RevitThemeChangeMonitor(
            UIApplication uiApplication,
            ILogger logger,
            Action<string> themeChanged)
            : this(
                new ReflectionRevitThemeSource(uiApplication),
                logger,
                themeChanged,
                RevitThemeDetector.ClearCache)
        {
        }

        internal RevitThemeChangeMonitor(
            IRevitThemeSource themeSource,
            ILogger logger,
            Action<string> themeChanged,
            Action clearThemeCache)
        {
            _themeSource = themeSource ?? throw new ArgumentNullException(nameof(themeSource));
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _themeChanged = themeChanged ?? throw new ArgumentNullException(nameof(themeChanged));
            _clearThemeCache = clearThemeCache ?? throw new ArgumentNullException(nameof(clearThemeCache));
        }

        /// <summary>
        /// Starts observing Revit theme changes.
        /// </summary>
        public void Start()
        {
            if (_disposed)
                throw new ObjectDisposedException(nameof(RevitThemeChangeMonitor));

            if (_started)
                return;

            try
            {
                _lastTheme = _themeSource.GetCurrentTheme();
                _started = _themeSource.Subscribe(OnThemeChanged);

                if (_started)
                {
                    _logger.Debug($"Monitoring Revit UI theme changes. Initial theme: {_lastTheme ?? "Unknown"}");
                }
                else
                {
                    _logger.Debug("Revit UI theme change notifications are not available.");
                }
            }
            catch (Exception ex)
            {
                _themeSource.Unsubscribe();
                _logger.Warning($"Revit UI theme monitoring could not be started: {ex.Message}");
            }
        }

        /// <summary>
        /// Enables user notifications after the initial pyRevit session has loaded.
        /// </summary>
        public void SetSessionReady()
        {
            _sessionReady = true;

            if (!string.IsNullOrEmpty(_pendingTheme))
            {
                var theme = _pendingTheme;
                _pendingTheme = null;
                RequestThemeRefresh(theme!);
            }
        }

        private void OnThemeChanged(object? sender, EventArgs eventArgs)
        {
            try
            {
                var currentTheme = _themeSource.GetCurrentTheme();
                if (string.IsNullOrEmpty(currentTheme))
                    return;

                var previousTheme = _lastTheme;
                _lastTheme = currentTheme;

                // Comparing the actual UI theme also filters canvas-only events on Revit 2024,
                // where ThemeChangedEventArgs does not identify which theme changed.
                if (string.IsNullOrEmpty(previousTheme) ||
                    string.Equals(previousTheme, currentTheme, StringComparison.OrdinalIgnoreCase))
                {
                    return;
                }

                _clearThemeCache();
                _logger.Info($"Revit UI theme changed from {previousTheme} to {currentTheme}.");

                if (_sessionReady)
                {
                    RequestThemeRefresh(currentTheme!);
                }
                else
                {
                    _pendingTheme = currentTheme;
                }
            }
            catch (Exception ex)
            {
                _logger.Error($"Failed to process Revit UI theme change: {ex.Message}");
            }
        }

        private void RequestThemeRefresh(string theme)
        {
            try
            {
                _themeChanged(theme);
            }
            catch (Exception ex)
            {
                _logger.Error($"Failed to request a pyRevit theme refresh: {ex.Message}");
            }
        }

        /// <inheritdoc/>
        public void Dispose()
        {
            if (_disposed)
                return;

            _disposed = true;
            try
            {
                _themeSource.Unsubscribe();
            }
            catch (Exception ex)
            {
                _logger.Warning($"Revit UI theme monitoring could not be stopped cleanly: {ex.Message}");
            }
            _started = false;
        }
    }

    internal interface IRevitThemeSource
    {
        string? GetCurrentTheme();
        bool Subscribe(EventHandler handler);
        void Unsubscribe();
    }

    internal sealed class ReflectionRevitThemeSource : IRevitThemeSource
    {
        private readonly object _uiApplication;
        private readonly Type _revitUiApplicationType;
        private EventInfo? _themeChangedEvent;
        private Delegate? _themeChangedDelegate;
        private EventHandler? _handler;

        public ReflectionRevitThemeSource(UIApplication uiApplication)
            : this(uiApplication, typeof(UIApplication))
        {
        }

        internal ReflectionRevitThemeSource(object uiApplication, Type revitUiApplicationType)
        {
            _uiApplication = uiApplication ?? throw new ArgumentNullException(nameof(uiApplication));
            _revitUiApplicationType = revitUiApplicationType
                ?? throw new ArgumentNullException(nameof(revitUiApplicationType));
        }

        public string? GetCurrentTheme()
        {
            var themeManagerType = _revitUiApplicationType.Assembly.GetType(
                "Autodesk.Revit.UI.UIThemeManager");
            var currentThemeProperty = themeManagerType?.GetProperty(
                "CurrentTheme",
                BindingFlags.Public | BindingFlags.Static);
            return currentThemeProperty?.GetValue(null)?.ToString();
        }

        public bool Subscribe(EventHandler handler)
        {
            _themeChangedEvent = _uiApplication.GetType().GetEvent(
                "ThemeChanged",
                BindingFlags.Public | BindingFlags.Instance);
            var eventHandlerType = _themeChangedEvent?.EventHandlerType;
            if (eventHandlerType == null)
                return false;

            _handler = handler;
            _themeChangedDelegate = CreateEventDelegate(eventHandlerType);
            _themeChangedEvent!.AddEventHandler(_uiApplication, _themeChangedDelegate);
            return true;
        }

        public void Unsubscribe()
        {
            if (_themeChangedEvent != null && _themeChangedDelegate != null)
            {
                _themeChangedEvent.RemoveEventHandler(_uiApplication, _themeChangedDelegate);
            }

            _themeChangedEvent = null;
            _themeChangedDelegate = null;
            _handler = null;
        }

        private Delegate CreateEventDelegate(Type eventHandlerType)
        {
            var invokeMethod = eventHandlerType.GetMethod("Invoke")
                ?? throw new InvalidOperationException("ThemeChanged event has no invoke method.");
            var parameters = invokeMethod.GetParameters();
            if (parameters.Length != 2)
                throw new InvalidOperationException("ThemeChanged event has an unexpected signature.");

            var senderParameter = Expression.Parameter(parameters[0].ParameterType, "sender");
            var eventArgsParameter = Expression.Parameter(parameters[1].ParameterType, "eventArgs");
            var callback = GetType().GetMethod(
                nameof(ForwardThemeChanged),
                BindingFlags.NonPublic | BindingFlags.Instance)
                ?? throw new InvalidOperationException("ThemeChanged callback could not be resolved.");

            var body = Expression.Call(
                Expression.Constant(this),
                callback,
                Expression.Convert(senderParameter, typeof(object)),
                Expression.Convert(eventArgsParameter, typeof(EventArgs)));

            return Expression.Lambda(
                eventHandlerType,
                body,
                senderParameter,
                eventArgsParameter).Compile();
        }

        private void ForwardThemeChanged(object sender, EventArgs eventArgs)
        {
            _handler?.Invoke(sender, eventArgs);
        }
    }
}
