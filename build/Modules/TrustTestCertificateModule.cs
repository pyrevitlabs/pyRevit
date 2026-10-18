using Build.Helpers;
using ModularPipelines.Context;
using ModularPipelines.Modules;

namespace Build.Modules;

/// <summary>
/// Creates the developer test-signing certificate and trusts it for the current user, so <c>ci local</c> can sign
/// with it afterwards.
/// </summary>
/// <remarks>
/// This is the only step that writes a trust store, and adding a self-signed certificate to <c>Root</c> raises the
/// modal Windows Security Warning. Keeping it in its own mode means the prompt is expected, announced up front, and
/// never happens in the middle of a build. Runs once per certificate: a certificate that is already trusted is left
/// alone. Refused when <c>CI</c> is set, because nobody is there to answer the prompt.
/// </remarks>
public sealed class TrustTestCertificateModule : Module
{
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var fingerprint = await TestCertificateStore.TrustLocalCertificateAsync(cancellationToken);
        context.Summary.KeyValue("Test signing", "Certificate", $"trusted ({fingerprint})");
    }
}
