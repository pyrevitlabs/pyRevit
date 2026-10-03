using Build.Helpers;
using Build.Options;
using Microsoft.Extensions.Options;
using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.Modules;

namespace Build.Modules;

/// <summary>
/// Signs the pyRevit binaries in <c>bin/</c> with a throwaway or per-developer certificate so Revit loads them
/// without the unsigned add-in dialog.
/// </summary>
/// <remarks>
/// Never reads <see cref="SigningOptions"/>. In CI the fingerprint comes from <c>TestSigning__Fingerprint</c>;
/// in local mode the developer certificate is created, trusted and renewed on demand.
/// </remarks>
[DependsOn<WriteCiBinManifestModule>(Optional = true)]
[DependsOn<StageReleaseMetadataModule>(Optional = true)]
[DependsOn<BuildShellModule>(Optional = true)]
[DependsOn<TestConfigurationsModule>(Optional = true)]
public sealed class SignTestBinariesModule(IOptions<TestSigningOptions> testSigningOptions) : Module
{
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var options = testSigningOptions.Value;
        var fingerprint = options.Local
            ? await TestCertificateHelper.EnsureLocalCertificateAsync(cancellationToken)
            : options.Fingerprint;

        if (string.IsNullOrWhiteSpace(fingerprint))
        {
            throw new InvalidOperationException(
                "sign-test needs the throwaway certificate fingerprint in TestSigning__Fingerprint.");
        }

        var files = SigningHelper.FindPyRevitBinaries(PyRevitPaths.BinPath).ToArray();
        await TestCertificateHelper.SignFilesAsync(context, fingerprint, files, "Binaries", cancellationToken);
    }
}
