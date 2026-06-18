using Build.Options;
using Microsoft.Extensions.Options;
using ModularPipelines.Configuration;
using ModularPipelines.Models;

namespace Build.Helpers;

public static class SkipDecisions
{
    public static ModuleConfigurationBuilder WithMainRepositoryGate(
        this ModuleConfigurationBuilder builder,
        IOptions<BuildOptions> buildOptions)
    {
        return builder.WithSkipWhen(_ => CreateUnlessMainRepository(buildOptions));
    }

    public static ModuleConfigurationBuilder WithStampingGate(
        this ModuleConfigurationBuilder builder,
        IOptions<BuildOptions> buildOptions)
    {
        return builder.WithSkipWhen(_ =>
        {
            if (string.Equals(buildOptions.Value.Channel, "none", StringComparison.OrdinalIgnoreCase))
            {
                return SkipDecision.Skip("Build channel is none; skipping version stamping.");
            }

            return CreateUnlessMainRepository(buildOptions);
        });
    }

    public static ModuleConfigurationBuilder WithSigningGate(
        this ModuleConfigurationBuilder builder,
        IOptions<SigningOptions> signingOptions)
    {
        return builder.WithSkipWhen(_ => CreateUnlessSigningConfigured(signingOptions));
    }

    public static SkipDecision CreateUnlessMainRepository(IOptions<BuildOptions> buildOptions)
    {
        var repository = Environment.GetEnvironmentVariable("GITHUB_REPOSITORY");
        if (string.IsNullOrWhiteSpace(repository))
        {
            return SkipDecision.DoNotSkip;
        }

        var mainRepository = buildOptions.Value.MainRepository;
        if (!string.Equals(repository, mainRepository, StringComparison.OrdinalIgnoreCase))
        {
            return SkipDecision.Skip("Not running on main repository (" + repository + ").");
        }

        return SkipDecision.DoNotSkip;
    }

    public static SkipDecision CreateUnlessSigningConfigured(IOptions<SigningOptions> signingOptions)
    {
        if (!signingOptions.Value.IsConfigured)
        {
            return SkipDecision.Skip("Signing secrets are not configured.");
        }

        return SkipDecision.DoNotSkip;
    }
}
