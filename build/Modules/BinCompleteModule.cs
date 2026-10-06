using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.Modules;

namespace Build.Modules;

/// <summary>
/// Marks the point in a <c>ci</c> run where every module that writes pyRevit binaries into <c>bin/</c> has finished.
/// </summary>
/// <remarks>
/// Modules that sign or scan <c>bin/</c> depend on this (optionally, so they also run without <c>ci</c>) instead of
/// naming the writers themselves. Invariant: a new module that writes into <c>bin/</c> must be added here, or
/// signing and the test-signature scan can run while it is still writing.
/// </remarks>
[DependsOn<WriteCiBinManifestModule>]
[DependsOn<BuildShellModule>]
[DependsOn<TestConfigurationsModule>]
[DependsOn<VerifyLibGit2Module>]
public sealed class BinCompleteModule : Module
{
    protected override Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken) =>
        Task.CompletedTask;
}
