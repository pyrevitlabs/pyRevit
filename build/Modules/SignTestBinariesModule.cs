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
/// in local mode the developer certificate is created or renewed on demand. Either way the certificate must carry a
/// test subject, so <see cref="RejectTestSignedBinariesModule"/> can recognise what it signed.
/// <para>
/// Local mode never writes a trust store: an untrusted certificate is reported here, naming
/// <c>--trust-cert</c>, instead of blocking a build on the Windows root prompt.
/// </para>
/// </remarks>
[DependsOn<BinCompleteModule>(Optional = true)]
[DependsOn<StageReleaseMetadataModule>(Optional = true)]
public sealed class SignTestBinariesModule(IOptions<TestSigningOptions> testSigningOptions) : Module
{
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var options = testSigningOptions.Value;
        var fingerprint = options.Local
            ? await EnsureTrustedLocalCertificateAsync(cancellationToken)
            : options.Fingerprint;

        if (string.IsNullOrWhiteSpace(fingerprint))
        {
            throw new InvalidOperationException(
                "sign-test needs the throwaway certificate fingerprint in TestSigning__Fingerprint.");
        }

        TestCertificateStore.EnsureFingerprintIsTestCertificate(fingerprint);

        var files = SigningHelper.FindPyRevitBinaries(PyRevitPaths.BinPath).ToArray();
        await SigningHelper.SignFilesWithTestCertificateAsync(context, fingerprint, files, "Binaries", cancellationToken);
    }

    /// <summary>Returns the fingerprint of a trusted developer certificate, creating or renewing it on demand.</summary>
    /// <remarks>
    /// Refuses before creating anything, so a developer who never trusted anything is not left with a private key,
    /// and refuses again on the certificate that will actually sign, because trust is per certificate: a renewed one
    /// is not the one that was trusted, and signing with it yields binaries Windows calls unverified.
    /// </remarks>
    private static async Task<string> EnsureTrustedLocalCertificateAsync(CancellationToken cancellationToken)
    {
        TestCertificateStore.EnsureLocalCertificateIsTrusted();

        var fingerprint = await TestCertificateStore.EnsureLocalCertificateAsync(cancellationToken);

        TestCertificateStore.EnsureFingerprintIsTrusted(fingerprint);

        return fingerprint;
    }
}
