using System;
using System.Collections.Generic;
using System.Threading;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Sections;

namespace pyRevitLabs.Configurations.Tests;

/// <summary>
/// Covers the process-wide shared-service cache: build-once caching, collapsing
/// of default-name variants to one instance, distinct override instances, and
/// reload/reset invalidation. The store is static global state, so each test
/// resets it and the class is non-parallel.
/// </summary>
[Collection("PyRevitConfigStore")]
public class PyRevitConfigStoreTests : IDisposable
{
    public PyRevitConfigStoreTests() => PyRevitConfigStore.Reset();
    public void Dispose() => PyRevitConfigStore.Reset();

    [Fact]
    public void GetShared_BuildsOnce_AndReturnsSameInstance()
    {
        int builds = 0;
        PyRevitConfigStore.SetFactory(_ => CountingService(ref builds));

        var first = PyRevitConfigStore.GetShared();
        var second = PyRevitConfigStore.GetShared();

        Assert.Same(first, second);
        Assert.Equal(1, builds);
    }

    [Fact]
    public void GetShared_DefaultNameVariants_ShareOneInstance()
    {
        int builds = 0;
        PyRevitConfigStore.SetFactory(_ => CountingService(ref builds));

        var viaNull = PyRevitConfigStore.GetShared(null);
        var viaEmpty = PyRevitConfigStore.GetShared("");
        var viaDefault = PyRevitConfigStore.GetShared(ConfigurationService.DefaultConfigurationName);

        Assert.Same(viaNull, viaEmpty);
        Assert.Same(viaNull, viaDefault);
        Assert.Equal(1, builds);
    }

    [Fact]
    public void GetShared_DistinctOverrideName_BuildsSeparateInstance()
    {
        int builds = 0;
        PyRevitConfigStore.SetFactory(_ => CountingService(ref builds));

        var def = PyRevitConfigStore.GetShared();
        var override2025 = PyRevitConfigStore.GetShared("2025");

        Assert.NotSame(def, override2025);
        Assert.Equal(2, builds);
    }

    [Fact]
    public void Reload_RebuildsOnNextAccess()
    {
        int builds = 0;
        PyRevitConfigStore.SetFactory(_ => CountingService(ref builds));

        var first = PyRevitConfigStore.GetShared();
        PyRevitConfigStore.Reload();
        var second = PyRevitConfigStore.GetShared();

        Assert.NotSame(first, second);
        Assert.Equal(2, builds);
    }

    [Fact]
    public void GetShared_WithoutFactory_Throws()
    {
        Assert.False(PyRevitConfigStore.HasFactory);
        Assert.Throws<InvalidOperationException>(() => PyRevitConfigStore.GetShared());
    }

    [Fact]
    public void SetFactory_Null_Throws()
    {
        Assert.Throws<ArgumentNullException>(() => PyRevitConfigStore.SetFactory(null!));
    }

    private static IConfigurationService CountingService(ref int builds)
    {
        Interlocked.Increment(ref builds);
        return new StubService();
    }

    private sealed class StubService : IConfigurationService
    {
        public bool ReadOnly => false;
        public IEnumerable<string> ConfigurationNames => Array.Empty<string>();
        public IEnumerable<IConfiguration> Configurations => Array.Empty<IConfiguration>();
        public IConfiguration this[string configurationName] => throw new NotImplementedException();

        public CoreSection Core => new();
        public RoutesSection Routes => new();
        public TelemetrySection Telemetry => new();
        public EnvironmentSection Environment => new();

        public void ReloadLoadConfigurations() { }
        public T GetSection<T>() => throw new NotImplementedException();
        public void SaveSection<T>(string configurationName, T sectionValue) => throw new NotImplementedException();
        public void SetSectionKeyValue<T>(string configurationName, string sectionName, string keyName, T keyValue)
            => throw new NotImplementedException();
        public T? GetSectionKeyValueOrDefault<T>(string configurationName, string sectionName, string keyName, T? defaultValue = default)
            => throw new NotImplementedException();
    }
}
