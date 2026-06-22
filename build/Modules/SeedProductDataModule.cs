using Build.Helpers;
using ModularPipelines.Context;
using ModularPipelines.Modules;

namespace Build.Modules;

public sealed class SeedProductDataModule : Module
{
    protected override Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        ProductDataHelper.SeedProductsFromTemplate(
            PyRevitPaths.ProductsTemplateFile,
            PyRevitPaths.ProductsDataFile);
        return Task.CompletedTask;
    }
}
