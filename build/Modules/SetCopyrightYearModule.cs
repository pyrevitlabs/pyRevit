using Build.Helpers;
using Build.Options;
using Microsoft.Extensions.Options;
using ModularPipelines.Configuration;
using ModularPipelines.Context;
using ModularPipelines.Modules;

namespace Build.Modules;

public sealed class SetCopyrightYearModule(IOptions<BuildOptions> buildOptions) : Module
{
    protected override ModuleConfiguration Configure()
        => ModuleConfiguration.Create().WithStampingGate(buildOptions).Build();
    protected override Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var today = DateTime.Today;
        var year = today.Year;
        if ((new DateTime(year + 1, 1, 1) - today).TotalDays < 30)
        {
            year += 1;
        }

        var copyright = $"2014-{year}";
        var finder = new System.Text.RegularExpressions.Regex(@"2014-\d{4}");
        foreach (var file in PyRevitPaths.CopyrightFiles)
        {
            VersionHelper.ReplacePatternInFile(file, finder, copyright);
        }

        XmlHelper.SetMsiCopyright(PyRevitPaths.PyRevitCommonMsiProps, copyright);
        XmlHelper.SetChocoCopyright(PyRevitPaths.PyRevitChocoNuspec, copyright);
        context.Summary.KeyValue("Build", "Copyright", copyright);
        return Task.CompletedTask;
    }
}
