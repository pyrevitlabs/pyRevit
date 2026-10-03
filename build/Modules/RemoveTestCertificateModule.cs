using Build.Helpers;
using ModularPipelines.Context;
using ModularPipelines.Modules;

namespace Build.Modules;

public sealed class RemoveTestCertificateModule : Module
{
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        await TestCertificateHelper.RemoveLocalCertificateAsync(cancellationToken);
        context.Summary.KeyValue("Test signing", "Certificate", "removed");
    }
}
