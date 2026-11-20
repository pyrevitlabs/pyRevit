using System.Net;
using Build.Helpers;
using Microsoft.Extensions.Logging;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Build.Tests;

[TestClass]
public sealed class GitHubClientFactoryTests
{
    [TestMethod]
    public async Task Request_is_logged_as_one_line_without_headers_or_body()
    {
        var logger = new RecordingLogger();
        using var invoker = new HttpMessageInvoker(new RequestLineLoggingHandler(logger)
        {
            InnerHandler = new CannedResponseHandler(HttpStatusCode.NotFound, "{\"secret_body\":true}"),
        });
        using var request = new HttpRequestMessage(HttpMethod.Get, "https://api.github.com/repos/o/r/issues/1");
        request.Headers.Add("Authorization", "token secret_header");

        using var response = await invoker.SendAsync(request, CancellationToken.None);

        Assert.HasCount(1, logger.Lines);
        StringAssert.StartsWith(logger.Lines[0], "GET https://api.github.com/repos/o/r/issues/1 -> 404 in ");
        Assert.IsFalse(logger.Lines[0].Contains("secret", StringComparison.Ordinal));
    }

    [TestMethod]
    public async Task Response_reaches_the_caller_unread()
    {
        using var invoker = new HttpMessageInvoker(new RequestLineLoggingHandler(new RecordingLogger())
        {
            InnerHandler = new CannedResponseHandler(HttpStatusCode.OK, "payload"),
        });
        using var request = new HttpRequestMessage(HttpMethod.Get, "https://api.github.com/rate_limit");

        using var response = await invoker.SendAsync(request, CancellationToken.None);

        Assert.AreEqual(HttpStatusCode.OK, response.StatusCode);
        Assert.AreEqual("payload", await response.Content.ReadAsStringAsync());
    }

    [TestMethod]
    public void Client_carries_the_token_and_targets_github()
    {
        var client = GitHubClientFactory.Create("the-token", new RecordingLogger());

        Assert.AreEqual("the-token", client.Connection.Credentials.Password);
        Assert.AreEqual(new Uri("https://api.github.com/"), client.Connection.BaseAddress);
    }

    private sealed class CannedResponseHandler(HttpStatusCode statusCode, string body) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken)
        {
            return Task.FromResult(new HttpResponseMessage(statusCode)
            {
                Content = new StringContent(body),
            });
        }
    }

    private sealed class RecordingLogger : ILogger
    {
        public List<string> Lines { get; } = [];

        public IDisposable? BeginScope<TState>(TState state)
            where TState : notnull
        {
            return null;
        }

        public bool IsEnabled(LogLevel logLevel)
        {
            return true;
        }

        public void Log<TState>(
            LogLevel logLevel,
            EventId eventId,
            TState state,
            Exception? exception,
            Func<TState, Exception?, string> formatter)
        {
            Lines.Add(formatter(state, exception));
        }
    }
}
