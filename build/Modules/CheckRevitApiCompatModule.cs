using Build.Helpers;
using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.Models;
using ModularPipelines.Modules;
using ModularPipelines.Options;

namespace Build.Modules;

/// <summary>
/// Lints the Python sources for Revit API calls missing in some supported Revit year, using
/// <c>dev/checks/check_revit_api_compat.py</c> against the committed baseline, and checks that the
/// catalog covers every Revit year the projects build for. See <c>docs/revit-api-compat.md</c>.
/// </summary>
/// <remarks>
/// Runs after version and copyright stamping: those modules rewrite <c>pyrevitlib/pyrevit/versionmgr/about.py</c>,
/// and the lint reading it mid-write would report a spurious parse failure.
/// </remarks>
[DependsOn<SetCopyrightYearModule>]
[DependsOn<StampVersionModule>]
public sealed class CheckRevitApiCompatModule : Module
{
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var mismatch = RevitApiCatalogHelper.DescribeYearMismatch(
            RevitApiCatalogHelper.ReadCatalogYears(await File.ReadAllTextAsync(PyRevitPaths.RevitApiCatalog, cancellationToken)),
            RevitApiCatalogHelper.ReadBuildTargetYears(await File.ReadAllTextAsync(PyRevitPaths.DirectoryBuildTargets, cancellationToken)));
        if (mismatch is not null)
        {
            throw new InvalidOperationException(mismatch);
        }

        var result = await context.Shell.Command.ExecuteCommandLineTool(
            new GenericCommandLineToolOptions(ToolResolutionHelper.ResolvePythonExecutable())
            {
                Arguments = [PyRevitPaths.RevitApiCompatScript, "--baseline"],
            },
            new CommandExecutionOptions
            {
                WorkingDirectory = PyRevitPaths.Root,
                ThrowOnNonZeroExitCode = false,
            },
            cancellationToken: cancellationToken);

        if (result.ExitCode != 0)
        {
            throw new InvalidOperationException(
                $"Revit API compatibility lint failed with exit code {result.ExitCode}:"
                + Environment.NewLine + result.StandardOutput + result.StandardError);
        }
    }
}
