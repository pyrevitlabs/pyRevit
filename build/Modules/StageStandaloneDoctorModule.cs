using Build.Helpers;
using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.Modules;

namespace Build.Modules;

/// <summary>
/// Stages <c>pyrevit-doctor.exe</c> in <c>dist/</c>, where the release publish uploads it as an asset of its own
/// and the WIP workflow includes it in the installer artifact.
/// </summary>
/// <remarks>
/// The copy is taken from <c>bin/</c> rather than built again, so the download is the same binary the installers
/// ship. The optional dependency on <see cref="SignBinariesModule"/> is load-bearing: in a signing run it makes
/// the copy happen after <c>bin/</c> is signed, so the download carries the Authenticode signature.
/// </remarks>
[DependsOn<RejectTestSignedBinariesModule>]
[DependsOn<SignBinariesModule>(Optional = true)]
public sealed class StageStandaloneDoctorModule : Module
{
    protected override Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var staged = StandaloneDoctorHelper.StageForRelease(PyRevitPaths.BinPath, PyRevitPaths.DistPath);
        context.Summary.KeyValue("Packaging", "Standalone doctor", staged);
        return Task.CompletedTask;
    }
}
