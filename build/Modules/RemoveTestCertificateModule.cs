using Build.Helpers;
using ModularPipelines.Context;
using ModularPipelines.Modules;

namespace Build.Modules;

/// <summary>Removes the developer test-signing certificate from every store it was trusted in.</summary>
public sealed class RemoveTestCertificateModule : Module
{
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        await TestCertificateHelper.RemoveLocalCertificateAsync(cancellationToken);
        context.Summary.KeyValue("Test signing", "Certificate", "removed");
    }
}
