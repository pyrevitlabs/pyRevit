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

var modes = PipelineModes.Parse(args);

TestCertificateHelper.EnsureModesAllowed(
    modes,
    (builder.Configuration.GetSection("Build").Get<BuildOptions>() ?? new BuildOptions()).Channel,
    string.Equals(Environment.GetEnvironmentVariable("CI"), "true", StringComparison.OrdinalIgnoreCase),
    OperatingSystem.IsWindows());

builder.Services.AddOptions<BuildOptions>().Bind(builder.Configuration.GetSection("Build"));
builder.Services.AddOptions<SigningOptions>().Bind(builder.Configuration.GetSection("Signing"));
builder.Services.AddOptions<TestSigningOptions>().Bind(builder.Configuration.GetSection("TestSigning"));
builder.Services.Configure<TestSigningOptions>(options => options.Local = modes.SignsWithLocalCertificate);
builder.Services.AddOptions<PublishOptions>().Bind(builder.Configuration.GetSection("Publish"));

builder.Services.Configure<BuildOptions>(options => options.RequireInstallerTooling = modes.Packages);

if (modes.Release)
{
    builder.Services.AddModule<ValidateTagMatchesVersionModule>();
}

if (modes.Ci)
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
    builder.Services.AddModule<TestConfigurationsModule>();
    builder.Services.AddModule<BuildShellModule>();
    builder.Services.AddModule<StageBinAssetsModule>();
    builder.Services.AddModule<BuildAutocompModule>();
    builder.Services.AddModule<VerifyLibGit2Module>();
    builder.Services.AddModule<StageReleaseMetadataModule>();
    builder.Services.AddModule<WriteCiBinManifestModule>();
}

if (modes.Packages)
{
    builder.Services.AddModule<RejectTestSignedBinariesModule>();
    builder.Services.AddModule<RestoreStampedMetadataModule>();
    builder.Services.AddModule<BuildInstallersModule>();
    builder.Services.AddModule<BuildChocoModule>();
}

if (modes.Sign || modes.Publish)
{
    builder.Services.AddModule<SignBinariesModule>();
    builder.Services.AddModule<SignDistInstallersModule>();
    builder.Services.AddModule<SignChocoPackageModule>();
}

if (modes.SignsTestBinaries)
{
    builder.Services.AddModule<SignTestBinariesModule>();
}

if (modes.RemoveCert)
{
    builder.Services.AddModule<RemoveTestCertificateModule>();
}

if (modes.Publish)
{
    builder.Services.AddModule<GenerateReleaseNotesModule>();
    builder.Services.AddModule<PublishGithubReleaseModule>();
    builder.Services.AddModule<PublishChocoModule>();
}

if (modes.Winget)
{
    builder.Services.AddModule<PublishWingetModule>();
}

if (modes.Notify)
{
    builder.Services.AddModule<NotifyIssuesModule>();
}

await builder.Build().RunAsync();
