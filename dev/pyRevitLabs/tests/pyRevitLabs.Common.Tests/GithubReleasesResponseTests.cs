using System.Net;

using NUnit.Framework;

using pyRevitLabs.Common;

namespace pyRevitLabs.Common.Tests {
    /// <summary>
    /// Parsing a GitHub releases response returns the release list only for a successful JSON list,
    /// and turns error objects, failed statuses and non-JSON bodies into <c>pyRevitGithubApiException</c>.
    /// </summary>
    [TestFixture]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [Category("HostFree")]
    [Category("Unit")]
    [Category("Regression")]
    public class GithubReleasesResponseTests {
        private const string RateLimitJson = @"{
            ""message"": ""API rate limit exceeded for 203.0.113.7."",
            ""documentation_url"": ""https://docs.github.com/rest/overview/resources-in-the-rest-api#rate-limiting""
        }";

        /// <summary>A successful JSON list is returned as releases in response order.</summary>
        [Test]
        public void ParseReleases_ReleaseList_ReturnsReleases() {
            var releases = GithubAPI.ParseReleases<GithubReleaseInfo>(
                @"[ { ""tag_name"": ""v7.1.0"" }, { ""tag_name"": ""v7.0.1"" } ]", HttpStatusCode.OK);
            Assert.That(releases.Count, Is.EqualTo(2));
            Assert.That(releases[0].Tag, Is.EqualTo("v7.1.0"));
        }

        /// <summary>A rate-limit error object raises with the HTTP status and GitHub's own message.</summary>
        [Test]
        public void ParseReleases_RateLimitErrorObject_ThrowsWithGithubMessage() {
            var ex = Assert.Throws<pyRevitGithubApiException>(() =>
                GithubAPI.ParseReleases<GithubReleaseInfo>(RateLimitJson, HttpStatusCode.Forbidden));
            Assert.That(ex.Message, Is.EqualTo("GitHub API request failed (HTTP 403): API rate limit exceeded for 203.0.113.7."));
        }

        /// <summary>An error object raises even when the status code reports success.</summary>
        [Test]
        public void ParseReleases_ErrorObjectWithOkStatus_Throws() {
            Assert.Throws<pyRevitGithubApiException>(() =>
                GithubAPI.ParseReleases<GithubReleaseInfo>(RateLimitJson, HttpStatusCode.OK));
        }

        /// <summary>A non-JSON body raises with the HTTP status name in place of a message.</summary>
        [Test]
        public void ParseReleases_NonJsonBody_ThrowsWithStatus() {
            var ex = Assert.Throws<pyRevitGithubApiException>(() =>
                GithubAPI.ParseReleases<GithubReleaseInfo>("<html>Bad gateway</html>", HttpStatusCode.BadGateway));
            Assert.That(ex.Message, Is.EqualTo("GitHub API request failed (HTTP 502): BadGateway"));
        }

        /// <summary>A failed status raises even when the body is a valid JSON list.</summary>
        [Test]
        public void ParseReleases_ErrorStatusWithListBody_Throws() {
            Assert.Throws<pyRevitGithubApiException>(() =>
                GithubAPI.ParseReleases<GithubReleaseInfo>("[]", HttpStatusCode.InternalServerError));
        }
    }
}
