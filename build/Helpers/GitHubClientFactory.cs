using Microsoft.Extensions.Logging;
using ModularPipelines.Context;
using ModularPipelines.GitHub.Extensions;
using Octokit;
using Octokit.Internal;

namespace Build.Helpers;

/// <summary>
/// Creates the Octokit client the pipeline modules talk to GitHub with.
/// </summary>
/// <remarks>
/// Use this instead of <c>context.GitHub().Client</c>. That client logs every request and
/// response in full, headers and body, and ModularPipelines has no setting to turn it off for
/// GitHub: one release run logged about 45,000 lines of issue JSON. The client created here
/// logs one line per request.
/// </remarks>
public static class GitHubClientFactory
{
    private const string ProductName = "pyRevit-build";

    /// <summary>
    /// Creates a client authenticated with the pipeline's <c>GITHUB_TOKEN</c>.
    /// </summary>
    /// <exception cref="InvalidOperationException">
    /// <c>GITHUB_TOKEN</c> is not set. Modules marked <c>[SkipIfNoGitHubToken]</c> never get here.
    /// </exception>
    public static IGitHubClient Create(IModuleContext context)
    {
        var token = context.GitHub().EnvironmentVariables.Token;
        if (string.IsNullOrWhiteSpace(token))
        {
            throw new InvalidOperationException("GITHUB_TOKEN is not set.");
        }

        return Create(token, context.Logger);
    }

    internal static IGitHubClient Create(string token, ILogger logger)
    {
        var connection = new Connection(
            new ProductHeaderValue(ProductName),
            new HttpClientAdapter(() => new RequestLineLoggingHandler(logger)
            {
                InnerHandler = HttpMessageHandlerFactory.CreateDefault(),
            }));

        return new GitHubClient(connection)
        {
            Credentials = new Credentials(token),
        };
    }
}

/// <summary>
/// Logs the method, URL, status code and duration of each request, and nothing of its headers
/// or body. A request that throws is logged with the exception type and rethrown.
/// </summary>
internal sealed class RequestLineLoggingHandler(ILogger logger) : DelegatingHandler
{
    protected override async Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken)
    {
        var started = System.Diagnostics.Stopwatch.GetTimestamp();
        HttpResponseMessage response;
        try
        {
            response = await base.SendAsync(request, cancellationToken).ConfigureAwait(false);
        }
        catch (Exception exception)
        {
            logger.LogWarning(
                "{Method} {Url} -> {Failure} after {Milliseconds} ms",
                request.Method,
                request.RequestUri,
                exception.GetType().Name,
                ElapsedMilliseconds(started));
            throw;
        }

        logger.LogInformation(
            "{Method} {Url} -> {StatusCode} in {Milliseconds} ms",
            request.Method,
            request.RequestUri,
            (int)response.StatusCode,
            ElapsedMilliseconds(started));

        return response;
    }

    private static long ElapsedMilliseconds(long started)
    {
        return (long)System.Diagnostics.Stopwatch.GetElapsedTime(started).TotalMilliseconds;
    }
}
