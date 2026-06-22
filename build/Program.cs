using Build.Helpers;
using Build.Modules;
using Build.Options;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using ModularPipelines;
using ModularPipelines.Extensions;

PyRevitPaths.Initialize();

var builder = Pipeline.CreateBuilder(args);

builder.Configuration.AddJsonFile("appsettings.json", optional: false, reloadOnChange: false);
builder.Configuration.AddEnvironmentVariables();
builder.Configuration.AddJsonFile(
    $"appsettings.{builder.Configuration["DOTNET_ENVIRONMENT"] ?? "Development"}.json",
    optional: true,
    reloadOnChange: false);
builder.Configuration.AddCommandLine(args);

var argsSet = new HashSet<string>(args, StringComparer.OrdinalIgnoreCase);
var runCi = argsSet.Count == 0 || argsSet.Contains("ci");
var runPack = argsSet.Contains("pack");
var runSign = argsSet.Contains("sign");
var runPublish = argsSet.Contains("publish");
var runNotify = argsSet.Contains("notify");
var runRelease = argsSet.Contains("release");
var runWinget = argsSet.Contains("winget");

builder.Services.AddOptions<BuildOptions>().Bind(builder.Configuration.GetSection("Build"));
builder.Services.AddOptions<SigningOptions>().Bind(builder.Configuration.GetSection("Signing"));
builder.Services.AddOptions<PublishOptions>().Bind(builder.Configuration.GetSection("Publish"));

var requireInstallerTooling = runPack || runSign || runPublish;
builder.Services.Configure<BuildOptions>(options => options.RequireInstallerTooling = requireInstallerTooling);

if (runRelease)
{
    builder.Services.AddModule<ValidateTagMatchesVersionModule>();
}

if (runCi)
{
    builder.Services.AddModule<CheckEnvironmentModule>();
    builder.Services.AddModule<ResolveVersioningModule>();
    builder.Services.AddModule<SetCopyrightYearModule>();
    builder.Services.AddModule<StampVersionModule>();
    builder.Services.AddModule<SeedProductDataModule>();
    builder.Services.AddModule<SetProductDataModule>();
    builder.Services.AddModule<BuildLabsModule>();
    builder.Services.AddModule<CheckDeployLocksModule>();
    builder.Services.AddModule<BuildIronPythonDepsModule>();
    builder.Services.AddModule<BuildLoadersModule>();
    builder.Services.AddModule<BuildRuntimeModule>();
    builder.Services.AddModule<BuildRunnersModule>();
    builder.Services.AddModule<StageBinAssetsModule>();
    builder.Services.AddModule<BuildAutocompModule>();
    builder.Services.AddModule<VerifyLibGit2Module>();
    builder.Services.AddModule<StageReleaseMetadataModule>();
    builder.Services.AddModule<WriteCiBinManifestModule>();
}

if (runPack || runSign || runPublish)
{
    builder.Services.AddModule<RestoreStampedMetadataModule>();
    builder.Services.AddModule<BuildInstallersModule>();
    builder.Services.AddModule<BuildChocoModule>();
}

if (runSign || runPublish)
{
    builder.Services.AddModule<SignBinariesModule>();
    builder.Services.AddModule<SignDistInstallersModule>();
    builder.Services.AddModule<SignChocoPackageModule>();
}

if (runPublish)
{
    builder.Services.AddModule<GenerateReleaseNotesModule>();
    builder.Services.AddModule<PublishGithubReleaseModule>();
    builder.Services.AddModule<PublishChocoModule>();
}

if (runWinget)
{
    builder.Services.AddModule<PublishWingetModule>();
}

if (runNotify)
{
    builder.Services.AddModule<NotifyIssuesModule>();
}

await builder.Build().RunAsync();
