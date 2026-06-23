using System.Collections.Concurrent;
using pyRevitLabs.Configurations.Abstractions;

namespace pyRevitLabs.Configurations;

/// <summary>
/// Process-wide cache of the shared pyRevit configuration service so the loader,
/// CLI, and script engines read one in-process instance instead of each
/// re-parsing the config file on every access. The host registers a factory that
/// knows how to build a service for a given configuration name (discovery,
/// migration, and diagnostics belong to the host that owns those concerns); the
/// store builds each name once on first request and returns the same instance
/// until <see cref="Reload"/> invalidates the cache.
/// </summary>
public static class PyRevitConfigStore
{
    private static readonly ConcurrentDictionary<string, IConfigurationService> _cache = new();
    private static volatile Func<string, IConfigurationService>? _factory;
    private static readonly object _factoryLock = new();

    /// <summary>
    /// True once a host has registered a build factory.
    /// </summary>
    public static bool HasFactory => _factory is not null;

    /// <summary>
    /// Registers the factory used to build a configuration service for a
    /// configuration name. Hosts that share a process must register equivalent
    /// discovery so the cached instance is the same regardless of who touches it
    /// first.
    /// </summary>
    public static void SetFactory(Func<string, IConfigurationService> factory)
    {
        if (factory is null)
            throw new ArgumentNullException(nameof(factory));

        lock (_factoryLock)
            _factory = factory;
    }

    /// <summary>
    /// Returns the shared service for the given configuration name, building it on
    /// first request. Names that identify the default configuration collapse to a
    /// single shared instance, so a getter and a setter that pass the default name
    /// differently still observe the same object.
    /// </summary>
    public static IConfigurationService GetShared(string? configurationName = null)
    {
        Func<string, IConfigurationService>? factory = _factory;
        if (factory is null)
            throw new InvalidOperationException(
                "PyRevitConfigStore has no factory registered; call SetFactory before GetShared.");

        string key = NormalizeKey(configurationName);
        return _cache.GetOrAdd(key, factory);
    }

    /// <summary>
    /// Drops every cached service so the next <see cref="GetShared"/> rebuilds from
    /// disk. Called when settings change and a reload is requested.
    /// </summary>
    public static void Reload() => _cache.Clear();

    /// <summary>
    /// Clears the cache and the registered factory. Intended for test isolation.
    /// </summary>
    public static void Reset()
    {
        lock (_factoryLock)
        {
            _cache.Clear();
            _factory = null;
        }
    }

    private static string NormalizeKey(string? configurationName) =>
        string.IsNullOrEmpty(configurationName)
        || string.Equals(configurationName, ConfigurationService.DefaultConfigurationName, StringComparison.Ordinal)
            ? ConfigurationService.DefaultConfigurationName
            : configurationName!;
}
