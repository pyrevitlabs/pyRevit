using System.Net;
using Build.Helpers;
using Microsoft.Extensions.Logging;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Build.Tests;

[TestClass]
[TestCategory("HostFree")]
[TestCategory("Unit")]
public sealed class GitHubClientFactoryTests
{
    [TestMethod]
    public async Task Request_is_logged_as_one_line_without_headers_or_body()
    {
        var logger = new RecordingLogger();
        using var invoker = new HttpMessageInvoker(new RequestLineLoggingHandler(logger)
        {
            InnerHandler = new CannedResponseHandler(HttpStatusCode.NotFound, new StringContent("{\"secret_body\":true}")),
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
        var content = new ReadCountingContent("payload");
        using var invoker = new HttpMessageInvoker(new RequestLineLoggingHandler(new RecordingLogger())
        {
            InnerHandler = new CannedResponseHandler(HttpStatusCode.OK, content),
        });
        using var request = new HttpRequestMessage(HttpMethod.Get, "https://api.github.com/rate_limit");

        using var response = await invoker.SendAsync(request, CancellationToken.None);

        Assert.AreEqual(HttpStatusCode.OK, response.StatusCode);
        Assert.AreEqual(0, content.Reads);
        Assert.AreEqual("payload", await response.Content.ReadAsStringAsync());
    }

    [TestMethod]
    public async Task Failed_request_is_logged_and_rethrown()
    {
        var logger = new RecordingLogger();
        using var invoker = new HttpMessageInvoker(new RequestLineLoggingHandler(logger)
        {
            InnerHandler = new ThrowingHandler(),
        });
        using var request = new HttpRequestMessage(HttpMethod.Post, "https://uploads.github.com/assets");

        await Assert.ThrowsExactlyAsync<HttpRequestException>(
            () => invoker.SendAsync(request, CancellationToken.None));

        Assert.HasCount(1, logger.Lines);
        StringAssert.StartsWith(logger.Lines[0], "POST https://uploads.github.com/assets -> HttpRequestException after ");
    }

    [TestMethod]
    public void Client_carries_the_token_and_targets_github()
    {
        var client = GitHubClientFactory.Create("the-token", new RecordingLogger());

        Assert.AreEqual("the-token", client.Connection.Credentials.Password);
        Assert.AreEqual(new Uri("https://api.github.com/"), client.Connection.BaseAddress);
    }

    private sealed class CannedResponseHandler(HttpStatusCode statusCode, HttpContent content) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken)
        {
            return Task.FromResult(new HttpResponseMessage(statusCode)
            {
                Content = content,
            });
        }
    }

    private sealed class ThrowingHandler : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken)
        {
            throw new HttpRequestException("connection refused");
        }
    }

    private sealed class ReadCountingContent(string body) : HttpContent
    {
        private readonly byte[] bytes = System.Text.Encoding.UTF8.GetBytes(body);

        public int Reads { get; private set; }

        protected override Task SerializeToStreamAsync(Stream stream, TransportContext? context)
        {
            Reads++;
            return stream.WriteAsync(bytes, 0, bytes.Length);
        }

        protected override bool TryComputeLength(out long length)
        {
            length = bytes.Length;
            return true;
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
