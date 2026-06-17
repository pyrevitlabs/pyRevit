using Build.Helpers;
using ModularPipelines.Context;
using ModularPipelines.Modules;

namespace Build.Modules;

public sealed class ValidateTagMatchesVersionModule : Module
{
    protected override Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var refName = Environment.GetEnvironmentVariable("GITHUB_REF_NAME");
        if (string.IsNullOrWhiteSpace(refName) || !refName.StartsWith('v'))
        {
            return Task.CompletedTask;
        }

        var tagVersion = refName[1..];
        var fileVersion = VersionHelper.ReadBuildVersion();
        if (!string.Equals(tagVersion, fileVersion, StringComparison.Ordinal))
        {
            throw new InvalidOperationException(
                $"Tag version ({tagVersion}) does not match pyrevitlib/pyrevit/version ({fileVersion})");
        }

        return Task.CompletedTask;
    }
}
