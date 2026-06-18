using Build.Helpers;
using Build.Models;
using Build.Options;
using Microsoft.Extensions.Options;
using ModularPipelines.Attributes;
using ModularPipelines.Configuration;
using ModularPipelines.Context;
using ModularPipelines.Modules;

namespace Build.Modules;

[DependsOn<StampVersionModule>]
public sealed class SetProductDataModule(IOptions<BuildOptions> buildOptions) : Module
{
    protected override ModuleConfiguration Configure()
        => ModuleConfiguration.Create().WithStampingGate(buildOptions).Build();
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var versionResult = await context.GetModule<StampVersionModule>();
        var versionInfo = versionResult.ValueOrDefault
            ?? throw new InvalidOperationException("StampVersionModule did not produce a version.");

        var msiProductCode = Guid.NewGuid().ToString();
        XmlHelper.SetMsiProductCodes(
            PyRevitPaths.PyRevitCliMsiProps,
            msiProductCode,
            PyRevitPaths.PyRevitCliUpgradeCode);

        var products = ProductDataHelper.LoadProducts(PyRevitPaths.ProductsTemplateFile);
        ProductDataHelper.InsertProduct(
            products,
            new ProductRecord("pyRevit", versionInfo.BuildVersion, versionInfo.BuildVersion, PyRevitPaths.PyRevitInnoProductCode),
            cli: false);
        ProductDataHelper.InsertProduct(
            products,
            new ProductRecord("pyRevit CLI", versionInfo.BuildVersion, versionInfo.BuildVersion, PyRevitPaths.PyRevitCliInnoProductCode),
            cli: true);
        ProductDataHelper.InsertProduct(
            products,
            new ProductRecord("pyRevit CLI MSI", versionInfo.BuildVersion, versionInfo.BuildVersion, msiProductCode),
            cli: true,
            msi: true);

        ProductDataHelper.SaveProducts(PyRevitPaths.ProductsDataFile, products);
    }
}
