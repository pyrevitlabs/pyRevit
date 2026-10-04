using Build.Helpers;
using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.Modules;

namespace Build.Modules;

/// <summary>
/// Fails pack, sign and publish runs when <c>bin/</c> holds binaries signed with a test certificate, so a
/// developer or CI test signature can never reach an installer.
/// </summary>
/// <remarks>
/// Inspects the actual Authenticode signer of each binary, so it also catches a <c>bin/</c> signed by an earlier,
/// separate <c>ci local</c> run or downloaded from a <c>sign-test</c> job.
/// <para>
/// Every module that packages or signs <c>bin/</c> depends on this one directly, so the guard does not rely on
/// registration order. The optional dependency on <see cref="WriteCiBinManifestModule"/> is load-bearing: in a
/// <c>ci pack</c> run it forces the scan to happen after the build has produced <c>bin/</c>, not before.
/// </para>
/// </remarks>
[DependsOn<WriteCiBinManifestModule>(Optional = true)]
public sealed class RejectTestSignedBinariesModule : Module
{
    protected override Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        TestSignatureDetector.EnsureNoTestSignedBinaries(PyRevitPaths.BinPath);
        return Task.CompletedTask;
    }
}
