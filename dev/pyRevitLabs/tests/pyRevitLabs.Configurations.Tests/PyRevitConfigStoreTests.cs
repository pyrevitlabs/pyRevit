using System;
using System.IO;
using System.Threading;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Sections;

namespace pyRevitLabs.Configurations.Tests;

/// <summary>
/// Covers the process-wide shared-service cache: build-once caching, concurrent
/// first access, failed-build eviction, and reload/reset invalidation. The store
/// is static global state, so each test resets it and the class is non-parallel.
/// </summary>
[Collection("PyRevitConfigStore")]
[Trait("Environment", "HostFree")]
[Trait("Level", "Integration")]
public class PyRevitConfigStoreTests : IDisposable {
    public PyRevitConfigStoreTests() => PyRevitConfigStore.Reset();
    public void Dispose() => PyRevitConfigStore.Reset();

    [Fact]
    public void GetShared_BuildsOnce_AndReturnsSameInstance() {
        int builds = 0;
        PyRevitConfigStore.SetFactory(() => CountingService(ref builds));

        var first = PyRevitConfigStore.GetShared();
        var second = PyRevitConfigStore.GetShared();

        Assert.Same(first, second);
        Assert.Equal(1, builds);
    }

    [Fact]
    public void Reload_RebuildsOnNextAccess() {
        int builds = 0;
        PyRevitConfigStore.SetFactory(() => CountingService(ref builds));

        var first = PyRevitConfigStore.GetShared();
        PyRevitConfigStore.Reload();
        var second = PyRevitConfigStore.GetShared();

        Assert.NotSame(first, second);
        Assert.Equal(2, builds);
    }

    [Fact]
    public void GetShared_WithoutFactory_Throws() {
        Assert.False(PyRevitConfigStore.HasFactory);
        Assert.Throws<InvalidOperationException>(() => PyRevitConfigStore.GetShared());
    }

    [Fact]
    public void SetFactory_Null_Throws() {
        Assert.Throws<ArgumentNullException>(() => PyRevitConfigStore.SetFactory(null!));
    }

    /// <summary>
    /// Concurrent callers must share one configuration build before any can return.
    /// </summary>
    [Fact]
    public void GetShared_ConcurrentFirstAccess_BuildsOnce() {
        int builds = 0;
        using var start = new ManualResetEventSlim();
        using var factoryEntered = new ManualResetEventSlim();
        using var releaseFactory = new ManualResetEventSlim();
        using var ready = new CountdownEvent(8);
        PyRevitConfigStore.SetFactory(() => {
            Interlocked.Increment(ref builds);
            factoryEntered.Set();
            if (!releaseFactory.Wait(TimeSpan.FromSeconds(10)))
                throw new TimeoutException("Configuration build was not released.");
            return new StubService();
        });

        var results = new IConfigurationService[8];
        var threads = new Thread[results.Length];
        for (int i = 0; i < threads.Length; i++) {
            int index = i;
            threads[i] = new Thread(() => {
                ready.Signal();
                start.Wait();
                results[index] = PyRevitConfigStore.GetShared();
            });
            threads[i].IsBackground = true;
            threads[i].Start();
        }

        bool allReady = ready.Wait(TimeSpan.FromSeconds(10));
        start.Set();
        bool entered = factoryEntered.Wait(TimeSpan.FromSeconds(10));
        releaseFactory.Set();
        foreach (Thread thread in threads)
            Assert.True(thread.Join(TimeSpan.FromSeconds(10)), "A concurrent caller did not complete.");

        Assert.True(allReady);
        Assert.True(entered);
        Assert.Equal(1, builds);
        Assert.All(results, item => Assert.Same(results[0], item));
    }

    /// <summary>
    /// A failed build must not be replayed to every later caller.
    /// </summary>
    [Fact]
    public void GetShared_FailedBuild_IsNotCached() {
        int attempts = 0;
        PyRevitConfigStore.SetFactory(() => {
            if (Interlocked.Increment(ref attempts) == 1)
                throw new IOException("config file locked");

            return new StubService();
        });

        Assert.Throws<IOException>(() => PyRevitConfigStore.GetShared());

        Assert.NotNull(PyRevitConfigStore.GetShared());
        Assert.Equal(2, attempts);
    }

    private static IConfigurationService CountingService(ref int builds) {
        Interlocked.Increment(ref builds);
        return new StubService();
    }

    private sealed class StubService : IConfigurationService {
        public bool ReadOnly => false;
        public IConfiguration Configuration => throw new NotImplementedException();

        public CoreSection Core => new();
        public RoutesSection Routes => new();
        public TelemetrySection Telemetry => new();
        public EnvironmentSection Environment => new();
        public ExtensionSection? GetExtensionSection(string extensionName) => null;

        public void ReloadLoadConfigurations() { }
        public T GetSection<T>() => throw new NotImplementedException();
        public void SaveSection<T>(T sectionValue) => throw new NotImplementedException();
        public void ApplySection<T>(T sectionValue) => throw new NotImplementedException();
        public void SetSectionKeyValue<T>(string sectionName, string keyName, T keyValue)
            => throw new NotImplementedException();
        public T? GetSectionKeyValueOrDefault<T>(string sectionName, string keyName, T? defaultValue = default)
            => throw new NotImplementedException();
    }
}
