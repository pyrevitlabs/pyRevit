using System.Globalization;
using System.Text.Json;
using Build.Options;
using ModularPipelines.Context;
using ModularPipelines.Models;
using ModularPipelines.Options;

namespace Build.Helpers;

public static class SigningHelper
{
    /// <summary>NuGet id of the Microsoft Trusted Signing CLI, <c>sign code</c>.</summary>
    internal const string SignToolPackageId = "sign";

    internal const string SignToolVersionIndexUrl =
        "https://api.nuget.org/v3-flatcontainer/sign/index.json";

    private static readonly TimeSpan SignToolLookupTimeout = TimeSpan.FromSeconds(30);

    /// <summary>
    /// Makes sure the <c>sign code</c> CLI is available, installing it when it is not.
    /// </summary>
    /// <remarks>
    /// Two unrelated packages share the NuGet id <c>sign</c>: the Microsoft Trusted Signing CLI, which is a .NET
    /// tool and only ships on the <c>0.x</c> prerelease line, and an assembly-signing library that owns the stable
    /// <c>1.x</c> line. <c>dotnet tool install --prerelease sign</c> resolves the highest version across both, picks
    /// the library, and fails with <c>Error: Package sign is not a .NET tool.</c> — so the version is resolved
    /// explicitly and passed to <c>--version</c>. See <see cref="SelectSignToolVersion"/>.
    /// </remarks>
    public static async Task EnsureSignToolInstalledAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        if (FindSignExecutable() is not null)
        {
            return;
        }

        var arguments = new List<string> { "tool", "install", "--global", SignToolPackageId };
        var version = await ResolveSignToolVersionAsync(cancellationToken);
        if (version is not null)
        {
            arguments.AddRange(["--version", version]);
        }

        await context.Shell.Command.ExecuteCommandLineTool(
            new GenericCommandLineToolOptions("dotnet") { Arguments = [.. arguments] },
            cancellationToken: cancellationToken);

        if (FindSignExecutable() is null)
        {
            throw new InvalidOperationException(
                $"The Microsoft sign CLI was not installed"
                + (version is null ? "." : $" at {version}.")
                + $" Install it manually with 'dotnet tool install --global {SignToolPackageId} --version <version>' "
                + "and rerun; only the 0.x versions of that package are .NET tools.");
        }
    }

    /// <summary>
    /// Picks the newest published version of <see cref="SignToolPackageId"/> that is a .NET tool.
    /// </summary>
    /// <remarks>
    /// The stable <c>1.x</c> line is a different package that happens to share the id, so only <c>0.x</c> versions
    /// are eligible. Returns <see langword="null"/> when the feed lists none, which leaves the caller to report a
    /// real installation failure instead of silently picking the wrong package.
    /// </remarks>
    internal static string? SelectSignToolVersion(IEnumerable<string> publishedVersions)
    {
        var toolVersions = publishedVersions
            .Where(version => version.StartsWith("0.", StringComparison.Ordinal))
            .ToArray();

        return toolVersions.Length == 0
            ? null
            : toolVersions.OrderBy(VersionOrderKey, StringComparer.Ordinal).Last();
    }

    /// <summary>Pads each numeric part so plain string ordering matches version ordering, build label last.</summary>
    private static string VersionOrderKey(string version)
    {
        var separator = version.IndexOf('-');
        var numeric = separator < 0 ? version : version[..separator];
        var parsed = Version.TryParse(numeric, out var value) ? value : new Version(0, 0);

        // '~' sorts after every character a prerelease label can start with, so a stable release orders after the
        // prereleases of the same version.
        return string.Format(
            CultureInfo.InvariantCulture,
            "{0:D5}.{1:D5}.{2:D5}.{3:D5}.{4}",
            parsed.Major,
            parsed.Minor,
            Math.Max(parsed.Build, 0),
            Math.Max(parsed.Revision, 0),
            separator < 0 ? "~" : version[separator..]);
    }

    private static async Task<string?> ResolveSignToolVersionAsync(CancellationToken cancellationToken)
    {
        try
        {
            using var client = new HttpClient { Timeout = SignToolLookupTimeout };
            using var response = await client.GetAsync(SignToolVersionIndexUrl, cancellationToken);
            if (!response.IsSuccessStatusCode)
            {
                return null;
            }

            await using var stream = await response.Content.ReadAsStreamAsync(cancellationToken);
            using var document = await JsonDocument.ParseAsync(stream, cancellationToken: cancellationToken);
            if (!document.RootElement.TryGetProperty("versions", out var versions))
            {
                return null;
            }

            return SelectSignToolVersion(
                versions.EnumerateArray().Select(version => version.GetString()).OfType<string>());
        }
        catch (Exception error) when (IsVersionLookupFailure(error, cancellationToken))
        {
            return null;
        }
    }

    private static bool IsVersionLookupFailure(Exception error, CancellationToken cancellationToken) =>
        !cancellationToken.IsCancellationRequested
        && (error is HttpRequestException or JsonException or OperationCanceledException);

    /// <summary>
    /// Returns the path of the installed <c>sign</c> CLI, or <see langword="null"/> when it is not installed.
    /// </summary>
    /// <remarks>
    /// Checks the global tool directory and <c>PATH</c>, so a runner that placed the tool somewhere else — a
    /// container image, a manually provisioned agent — is used instead of being reinstalled over.
    /// </remarks>
    public static string? FindSignExecutable()
    {
        if (File.Exists(GetSignExecutablePath()))
        {
            return GetSignExecutablePath();
        }

        var path = Environment.GetEnvironmentVariable("PATH") ?? string.Empty;
        var extensions = OperatingSystem.IsWindows()
            ? (Environment.GetEnvironmentVariable("PATHEXT") ?? ".EXE;.CMD;.BAT")
                .Split(';', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            : [string.Empty];

        foreach (var directory in path.Split(Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
        {
            foreach (var extension in extensions)
            {
                var candidate = Path.Combine(directory, SignToolPackageId + extension.ToLowerInvariant());
                if (File.Exists(candidate))
                {
                    return candidate;
                }
            }
        }

        return null;
    }

    public static string GetSignExecutablePath()
    {
        var userProfile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        return Path.Combine(userProfile, ".dotnet", "tools", OperatingSystem.IsWindows() ? "sign.exe" : "sign");
    }

    public static string BuildSigningSummary(IEnumerable<string> files)
    {
        var counts = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        foreach (var file in files)
        {
            var extension = Path.GetExtension(file);
            if (string.IsNullOrEmpty(extension))
            {
                extension = "(no extension)";
            }

            counts.TryGetValue(extension, out var count);
            counts[extension] = count + 1;
        }

        var total = counts.Values.Sum();
        var breakdown = string.Join(
            ", ",
            counts
                .OrderBy(kvp => kvp.Key, StringComparer.OrdinalIgnoreCase)
                .Select(kvp => string.Format("{0} {1}", kvp.Value, kvp.Key)));

        return string.Format("{0} file(s): {1}", total, breakdown);
    }

    public static Task<CommandResult> SignFilesAsync(
        IModuleContext context,
        SigningOptions signingOptions,
        BuildOptions buildOptions,
        IEnumerable<string> files,
        string summaryLabel,
        CancellationToken cancellationToken)
        => RunSignToolAsync(
            context,
            BuildProductionInvocation(signingOptions, buildOptions, summaryLabel),
            files,
            cancellationToken);

    /// <summary>
    /// Builds the production <c>sign code trusted-signing</c> invocation, including the Azure Trusted Signing
    /// credentials passed through the environment rather than the command line.
    /// </summary>
    /// <remarks>Extracted so the exact production argument list is pinned by a test; it is the highest-risk path.</remarks>
    internal static SignInvocation BuildProductionInvocation(
        SigningOptions signingOptions,
        BuildOptions buildOptions,
        string summaryLabel)
        => new(
            "trusted-signing",
            [
                "--trusted-signing-account", signingOptions.SigningAccountName,
                "--trusted-signing-certificate-profile", signingOptions.CertificateProfileName,
                "--trusted-signing-endpoint", signingOptions.Endpoint,
                "--timestamp-url", buildOptions.TimestampUrl,
                "--timestamp-digest", "SHA256",
            ],
            "Signing",
            summaryLabel)
        {
            EnvironmentVariables = new Dictionary<string, string?>
            {
                ["AZURE_TENANT_ID"] = signingOptions.TenantId,
                ["AZURE_CLIENT_ID"] = signingOptions.ClientId,
                ["AZURE_CLIENT_SECRET"] = signingOptions.ClientSecret,
            },
        };

    /// <summary>
    /// Signs <paramref name="files"/> in place with a test certificate from the Windows certificate store.
    /// Never touches <see cref="SigningOptions"/>, so production credentials cannot reach this path.
    /// </summary>
    /// <param name="fingerprint">SHA-256 fingerprint; the sign tool rejects a SHA-1 thumbprint.</param>
    /// <remarks>Re-signing an already signed file replaces its signature, so repeated <c>ci local</c> runs succeed.</remarks>
    public static Task<CommandResult> SignFilesWithTestCertificateAsync(
        IModuleContext context,
        string fingerprint,
        IEnumerable<string> files,
        string summaryLabel,
        CancellationToken cancellationToken)
    {
        var invocation = new SignInvocation(
            "certificate-store",
            ["--certificate-fingerprint", fingerprint],
            "Test signing",
            summaryLabel);

        return RunSignToolAsync(context, invocation, files, cancellationToken);
    }

    /// <summary>
    /// Runs <c>sign code &lt;provider&gt;</c> over <paramref name="files"/>. Production and test signing both go
    /// through here, so they always share the file list handling, file digest and summary reporting.
    /// </summary>
    internal static async Task<CommandResult> RunSignToolAsync(
        IModuleContext context,
        SignInvocation invocation,
        IEnumerable<string> files,
        CancellationToken cancellationToken)
    {
        var fileList = files.ToArray();
        if (fileList.Length == 0)
        {
            throw new InvalidOperationException("No files were provided for signing.");
        }

        context.Summary.KeyValue(invocation.SummarySection, invocation.SummaryLabel, BuildSigningSummary(fileList));

        await EnsureSignToolInstalledAsync(context, cancellationToken);

        return await context.Shell.Command.ExecuteCommandLineTool(
            new GenericCommandLineToolOptions(
                FindSignExecutable() ?? GetSignExecutablePath())
            {
                Arguments = BuildSignArguments(invocation, fileList),
            },
            new CommandExecutionOptions
            {
                EnvironmentVariables = invocation.EnvironmentVariables.ToDictionary(),
            },
            cancellationToken: cancellationToken);
    }

    internal static List<string> BuildSignArguments(SignInvocation invocation, IEnumerable<string> files)
    {
        var arguments = new List<string> { "code", invocation.Provider };
        arguments.AddRange(files);
        arguments.AddRange(["--file-digest", "SHA256"]);
        arguments.AddRange(invocation.ProviderArguments);
        return arguments;
    }

    public static IEnumerable<string> FindPyRevitBinaries(string rootFolder)
    {
        if (!Directory.Exists(rootFolder))
        {
            yield break;
        }

        foreach (var file in Directory.EnumerateFiles(rootFolder, "*.*", SearchOption.AllDirectories))
        {
            var name = Path.GetFileName(file);
            if (!name.StartsWith("pyrevit", StringComparison.OrdinalIgnoreCase)
                && !name.StartsWith("pyRevit", StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }

            var extension = Path.GetExtension(file);
            if (extension.Equals(".exe", StringComparison.OrdinalIgnoreCase)
                || extension.Equals(".dll", StringComparison.OrdinalIgnoreCase))
            {
                yield return file;
            }
        }
    }
}
