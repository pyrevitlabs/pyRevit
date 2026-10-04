using Build.Options;
using ModularPipelines.Context;
using ModularPipelines.Models;
using ModularPipelines.Options;

namespace Build.Helpers;

public static class SigningHelper
{
    public static async Task EnsureSignToolInstalledAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        if (File.Exists(GetSignExecutablePath()))
        {
            return;
        }

        await context.Shell.Command.ExecuteCommandLineTool(
            new GenericCommandLineToolOptions("dotnet")
            {
                Arguments = ["tool", "install", "--global", "sign", "--prerelease"],
            },
            cancellationToken: cancellationToken);
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
    {
        var invocation = new SignInvocation(
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

        return RunSignToolAsync(context, invocation, files, cancellationToken);
    }

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
            new GenericCommandLineToolOptions(GetSignExecutablePath())
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
