using System;
using System.Linq;
using pyRevitLabs.Configurations.Abstractions;

namespace pyRevitLabs.Configurations.Tests;

/// <summary>
/// Covers <see cref="IConfigurationService.ResetToDefaults"/>: stored values are
/// removed so reads fall back to the declared defaults, bookkeeping keys and the
/// environment section survive, and a dry run changes nothing.
/// </summary>
[Trait("Level", "Unit")]
[Trait("Environment", "HostFree")]
public class ResetToDefaultsTests {
    private static IConfigurationService BuildService(Action<InMemoryConfiguration> seed) {
        var configuration = new InMemoryConfiguration();
        seed(configuration);
        return new ConfigurationBuilder(false)
            .AddConfigurationSource(configuration)
            .Build();
    }

    [Fact]
    public void ResetToDefaults_TypedSection_RemovesBoundKeysAndFallsBackToDeclaredDefault() {
        var service = BuildService(config => {
            config.SetValue("core", "rocketmode", false);
            config.SetValue("core", "config_version", 1);
        });

        var removed = service.ResetToDefaults("core");

        Assert.Equal(new[] { "core:rocketmode" }, removed);
        Assert.True(service.Core.RocketMode);
        Assert.True(service.Configuration.HasSectionKey("core", "config_version"));
        Assert.False(service.Configuration.HasSectionKey("core", "rocketmode"));
    }

    [Fact]
    public void ResetToDefaults_RemovesLegacyKeyNames() {
        var service = BuildService(config => {
            config.SetValue("core", "load_beta", true);
            config.SetValue("core", "config_version", 1);
        });

        service.ResetToDefaults("core");

        Assert.False(service.Configuration.HasSectionKey("core", "load_beta"));
        Assert.False(service.Core.LoadBeta);
    }

    [Fact]
    public void ResetToDefaults_TypedSectionLeftEmpty_RemovesTheSection() {
        var service = BuildService(config => config.SetValue("routes", "port", 1234));

        service.ResetToDefaults("routes");

        Assert.False(service.Configuration.HasSection("routes"));
        Assert.Equal(48884, service.Routes.Port);
    }

    [Fact]
    public void ResetToDefaults_AlreadyEmptyTypedSection_IsReportedAndRemoved() {
        var service = BuildService(config => config.AddSection("routes"));

        Assert.Equal(new[] { "routes" }, service.ResetToDefaults("routes", dryRun: true));
        Assert.True(service.Configuration.HasSection("routes"));

        Assert.Equal(new[] { "routes" }, service.ResetToDefaults("routes"));
        Assert.False(service.Configuration.HasSection("routes"));
    }

    [Fact]
    public void ResetToDefaults_UntypedSection_RemovesItWhole() {
        var service = BuildService(config => {
            config.SetValue("MyTool_config", "answer", 42);
            config.SetValue("MyTool_config", "other", "x");
        });

        var removed = service.ResetToDefaults("MyTool_config");

        Assert.Equal(new[] { "MyTool_config" }, removed);
        Assert.False(service.Configuration.HasSection("MyTool_config"));
    }

    [Fact]
    public void ResetToDefaults_NoSection_ResetsEverythingExceptEnvironment() {
        var service = BuildService(config => {
            config.SetValue("core", "rocketmode", false);
            config.SetValue("telemetry", "active", true);
            config.SetValue("MyTool_config", "answer", 42);
            config.SetValue("environment", "sources", "[\"a\"]");
        });

        var removed = service.ResetToDefaults();

        Assert.Equal(
            new[] { "MyTool_config", "core:rocketmode", "telemetry:active" },
            removed.OrderBy(item => item, StringComparer.Ordinal).ToArray());
        Assert.True(service.Configuration.HasSectionKey("environment", "sources"));
        Assert.Equal(new[] { "environment" }, service.Configuration.GetSectionNames().ToArray());
    }

    [Fact]
    public void ResetToDefaults_EnvironmentSection_Throws() {
        var service = BuildService(config => config.SetValue("environment", "sources", "[]"));

        Assert.Throws<ArgumentException>(() => service.ResetToDefaults("environment"));
        Assert.True(service.Configuration.HasSectionKey("environment", "sources"));
    }

    [Fact]
    public void ResetToDefaults_DryRun_ReportsWithoutChanging() {
        var service = BuildService(config => {
            config.SetValue("core", "rocketmode", false);
            config.SetValue("MyTool_config", "answer", 42);
        });

        var removed = service.ResetToDefaults(dryRun: true);

        Assert.Equal(2, removed.Count);
        Assert.True(service.Configuration.HasSectionKey("core", "rocketmode"));
        Assert.True(service.Configuration.HasSection("MyTool_config"));
    }

    [Fact]
    public void ResetToDefaults_UserExtensions_AreKept() {
        var service = BuildService(config => {
            config.SetValue("core", "rocketmode", false);
            config.SetValue("core", "userextensions", "[\"C:\\Extensions\"]");
        });

        var removed = service.ResetToDefaults("core");

        Assert.Equal(new[] { "core:rocketmode" }, removed);
        Assert.True(service.Configuration.HasSectionKey("core", "userextensions"));
    }

    [Fact]
    public void ResetToDefaults_UnknownSection_Throws() {
        var service = BuildService(_ => { });

        Assert.Throws<ArgumentException>(() => service.ResetToDefaults("nosuch"));
    }

    [Fact]
    public void ResetToDefaults_MissingSection_ReturnsEmpty() {
        var service = BuildService(_ => { });

        Assert.Empty(service.ResetToDefaults("routes"));
    }
}
