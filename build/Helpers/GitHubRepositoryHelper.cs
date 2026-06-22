using Build.Options;
using Microsoft.Extensions.Options;

namespace Build.Helpers;

public static class GitHubRepositoryHelper
{
    public static (string Owner, string Name) Resolve(
        IOptions<BuildOptions>? buildOptions = null,
        IOptions<PublishOptions>? publishOptions = null,
        string? gitHubOwner = null,
        string? gitHubRepositoryName = null)
    {
        var fromEnv = Environment.GetEnvironmentVariable("GITHUB_REPOSITORY");
        if (!string.IsNullOrWhiteSpace(fromEnv))
        {
            return SplitRepository(fromEnv);
        }

        var configured = publishOptions?.Value.Repository ?? buildOptions?.Value.MainRepository;
        if (!string.IsNullOrWhiteSpace(configured))
        {
            return SplitRepository(configured);
        }

        if (!string.IsNullOrWhiteSpace(gitHubOwner) && !string.IsNullOrWhiteSpace(gitHubRepositoryName))
        {
            return (
                gitHubOwner,
                NormalizeRepositoryName(gitHubRepositoryName));
        }

        return ("pyrevitlabs", "pyRevit");
    }

    public static string NormalizeRepositoryName(string name)
    {
        if (name.EndsWith(".git", StringComparison.OrdinalIgnoreCase))
        {
            return name[..^4];
        }

        return name;
    }

    private static (string Owner, string Name) SplitRepository(string value)
    {
        var slash = value.IndexOf('/');
        if (slash <= 0 || slash >= value.Length - 1)
        {
            throw new InvalidOperationException("Invalid repository format: " + value);
        }

        return (
            value[..slash],
            NormalizeRepositoryName(value[(slash + 1)..]));
    }
}
