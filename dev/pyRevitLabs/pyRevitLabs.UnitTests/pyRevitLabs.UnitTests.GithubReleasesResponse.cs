using System.Net;

using Microsoft.VisualStudio.TestTools.UnitTesting;

using pyRevitLabs.Common;
using pyRevitLabs.PyRevit;

namespace pyRevitLabs.UnitTests {
    [TestClass]
    [TestCategory("HostFree")]
    [TestCategory("Unit")]
    public class GithubReleasesResponseTests {
        private const string RateLimitJson = @"{
            ""message"": ""API rate limit exceeded for 203.0.113.7."",
            ""documentation_url"": ""https://docs.github.com/rest/overview/resources-in-the-rest-api#rate-limiting""
        }";

        [TestMethod]
        public void ParseReleases_ReleaseList_ReturnsReleases_Issue4105() {
            var releases = GithubAPI.ParseReleases<PyRevitRelease>(
                @"[ { ""tag_name"": ""v7.1.0"" }, { ""tag_name"": ""v7.0.1"" } ]", HttpStatusCode.OK);
            Assert.AreEqual(2, releases.Count);
            Assert.AreEqual("v7.1.0", releases[0].Tag);
        }

        [TestMethod]
        public void ParseReleases_RateLimitErrorObject_ThrowsWithGithubMessage_Issue4105() {
            var ex = Assert.ThrowsException<pyRevitGithubApiException>(() =>
                GithubAPI.ParseReleases<PyRevitRelease>(RateLimitJson, HttpStatusCode.Forbidden));
            Assert.AreEqual("GitHub API request failed (HTTP 403): API rate limit exceeded for 203.0.113.7.", ex.Message);
        }

        [TestMethod]
        public void ParseReleases_ErrorObjectWithOkStatus_Throws_Issue4105() {
            Assert.ThrowsException<pyRevitGithubApiException>(() =>
                GithubAPI.ParseReleases<PyRevitRelease>(RateLimitJson, HttpStatusCode.OK));
        }

        [TestMethod]
        public void ParseReleases_NonJsonBody_ThrowsWithStatus_Issue4105() {
            var ex = Assert.ThrowsException<pyRevitGithubApiException>(() =>
                GithubAPI.ParseReleases<PyRevitRelease>("<html>Bad gateway</html>", HttpStatusCode.BadGateway));
            Assert.AreEqual("GitHub API request failed (HTTP 502): BadGateway", ex.Message);
        }

        [TestMethod]
        public void ParseReleases_ErrorStatusWithListBody_Throws_Issue4105() {
            Assert.ThrowsException<pyRevitGithubApiException>(() =>
                GithubAPI.ParseReleases<PyRevitRelease>("[]", HttpStatusCode.InternalServerError));
        }
    }
}
