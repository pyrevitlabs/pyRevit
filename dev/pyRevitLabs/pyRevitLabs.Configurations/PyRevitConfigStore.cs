using pyRevitLabs.Configurations.Abstractions;

namespace pyRevitLabs.Configurations;

/// <summary>
/// Process-wide cache of the shared pyRevit configuration service so the loader,
/// CLI, and script engines read one in-process instance instead of each
/// re-parsing the config file on every access. The host registers a factory that
/// knows how to build the service (discovery, migration, and diagnostics belong
/// to the host that owns those concerns); the store builds it once on first
/// request and returns the same instance until <see cref="Reload"/> invalidates
/// the cache.
/// </summary>
public static class PyRevitConfigStore
{
    private static volatile Lazy<IConfigurationService>? _cached;
    private static volatile Func<IConfigurationService>? _factory;
    private static readonly object _lock = new();

    /// <summary>
    /// True once a host has registered a build factory.
    /// </summary>
    public static bool HasFactory => _factory is not null;

    /// <summary>
    /// Registers the factory used to build the configuration service. Hosts that
    /// share a process must register equivalent discovery so the cached instance
    /// is the same regardless of who touches it first.
    /// </summary>
    public static void SetFactory(Func<IConfigurationService> factory)
    {
        if (factory is null)
            throw new ArgumentNullException(nameof(factory));

        lock (_lock)
            _factory = factory;
    }

    /// <summary>
    /// Returns the shared service, building it on first request. It is built
    /// exactly once even under concurrent first access, since building it seeds,
    /// migrates, and backs up files that two threads must not touch at the same
    /// time. A failed build is not cached: a <see cref="Lazy{T}"/> would replay
    /// the same failure forever, so a failed attempt is dropped and a later call
    /// retries once the cause (disk, ACLs) is resolved.
    /// </summary>
    public static IConfigurationService GetShared()
    {
        Func<IConfigurationService>? factory = _factory;
        if (factory is null)
            throw new InvalidOperationException(
                "PyRevitConfigStore has no factory registered; call SetFactory before GetShared.");

        Lazy<IConfigurationService>? pending = _cached;
        if (pending is null)
        {
            lock (_lock)
                pending = _cached ??= new Lazy<IConfigurationService>(
                    factory, LazyThreadSafetyMode.ExecutionAndPublication);
        }

        try
        {
            return pending.Value;
        }
        catch
        {
            lock (_lock)
            {
                if (ReferenceEquals(_cached, pending))
                    _cached = null;
            }

            throw;
        }
    }

    /// <summary>
    /// Drops the cached service so the next <see cref="GetShared"/> rebuilds from
    /// disk. Called when settings change and a reload is requested.
    /// </summary>
    public static void Reload() => _cached = null;

    /// <summary>
    /// Clears the cache and the registered factory. Intended for test isolation.
    /// </summary>
    public static void Reset()
    {
        lock (_lock)
        {
            _cached = null;
            _factory = null;
        }
    }
}
