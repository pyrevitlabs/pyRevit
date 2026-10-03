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
/// separate <c>ci local</c> run. Run <c>ci</c> to rebuild unsigned binaries.
/// </remarks>
[DependsOn<WriteCiBinManifestModule>(Optional = true)]
public sealed class RejectTestSignedBinariesModule : Module
{
    protected override Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var offenders = TestCertificateHelper.FindTestSignedFiles(SigningHelper.FindPyRevitBinaries(PyRevitPaths.BinPath));
        if (offenders.Count > 0)
        {
            throw new InvalidOperationException(
                $"{offenders.Count} binaries in bin/ are signed with a test certificate (first: {offenders[0]}). " +
                "Rebuild with 'ci' before pack, sign or publish.");
        }

        return Task.CompletedTask;
    }
}
