using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text.RegularExpressions;

using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;
using pyRevitLabs.NLog;

namespace pyRevitLabs.Common {
    public class pyRevitMissingGithubTokenException : PyRevitException {
        public pyRevitMissingGithubTokenException()
            : base("Missing GitHub authorization token. Set GITHUBTOKEN for private-repo Actions artifact fallback "
                   + "(actions:read scope). Public pyrevitlabs/pyRevit clones use Release assets and do not need a token.") { }
    }

    public class pyRevitBinArtifactNotFoundException : PyRevitException {
        public pyRevitBinArtifactNotFoundException(string message) : base(message) { }
    }

    public class GithubArtifactInfo {
        public long Id { get; set; }
        public string Name { get; set; }
        public long WorkflowRunId { get; set; }
    }

    public static class GithubRepoHelper {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        private static readonly Regex GithubHttpsRepoPattern =
            new Regex(@"https?://github\.com/(?<owner>[^/]+)/(?<repo>[^/\.]+)", RegexOptions.IgnoreCase);

        private static readonly Regex GithubSshRepoPattern =
            new Regex(@"git@github\.com:(?<owner>[^/]+)/(?<repo>[^/\.]+)", RegexOptions.IgnoreCase);

        public static string ParseRepoId(string repoUrl) {
            if (string.IsNullOrWhiteSpace(repoUrl))
                return PyRevitLabsConsts.OriginalRepoId;

            var normalized = repoUrl.Trim().TrimEnd('/');
            if (normalized.EndsWith(".git", StringComparison.OrdinalIgnoreCase))
                normalized = normalized.Substring(0, normalized.Length - 4);

            var match = GithubHttpsRepoPattern.Match(normalized);
            if (!match.Success)
                match = GithubSshRepoPattern.Match(normalized);

            if (match.Success)
                return string.Format("{0}/{1}", match.Groups["owner"].Value, match.Groups["repo"].Value);

            logger.Warn(
                "Could not parse GitHub repo URL \"{0}\"; using default {1}.",
                repoUrl,
                PyRevitLabsConsts.OriginalRepoId);
            return PyRevitLabsConsts.OriginalRepoId;
        }
    }

    public static class GithubActionsAPI {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        public const string UnsignedBinArtifactPrefix = "unsigned-bin-";
        public const string CiWorkflowFileName = "ci.yml";

        private static string RequireAuthToken() {
            var token = GithubAPI.AuthToken;
            if (string.IsNullOrWhiteSpace(token))
                throw new pyRevitMissingGithubTokenException();
            return token;
        }

        private static HttpRequestMessage BuildRequest(HttpMethod method, string url, bool requireAuth = false) {
            var request = new HttpRequestMessage(method, url);
            request.Headers.UserAgent.ParseAdd("pyrevit-cli");
            var token = GithubAPI.AuthToken;
            if (!string.IsNullOrWhiteSpace(token))
                request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
            else if (requireAuth)
                request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", RequireAuthToken());
            request.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/vnd.github+json"));
            return request;
        }

        private static JObject GetJson(string url, bool requireAuth = false) {
            logger.Debug("GitHub API GET \"{0}\"", url);
            if (!CommonUtils.CheckInternetConnection())
                throw new pyRevitNoInternetConnectionException();

            using (var request = BuildRequest(HttpMethod.Get, url, requireAuth))
            using (var response = CommonUtils.SendHttpRequest(request)) {
                var body = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();
                if (!response.IsSuccessStatusCode)
                    throw new PyRevitException(string.Format(
                        "GitHub API request failed ({0}): {1}", (int)response.StatusCode, body));
                return JObject.Parse(body);
            }
        }

        public static string GetCommitShaForBranch(string repoId, string branchName) {
            var url = string.Format(
                "https://api.github.com/repos/{0}/commits/{1}",
                repoId,
                Uri.EscapeDataString(branchName));
            var payload = GetJson(url);
            return payload["sha"]?.Value<string>();
        }

        public static GithubArtifactInfo FindArtifactByName(string repoId, string artifactName) {
            var url = string.Format(
                "https://api.github.com/repos/{0}/actions/artifacts?name={1}&per_page=5",
                repoId,
                Uri.EscapeDataString(artifactName));
            var payload = GetJson(url, requireAuth: true);
            var artifacts = payload["artifacts"] as JArray;
            if (artifacts == null || artifacts.Count == 0)
                return null;

            var match = artifacts
                .Select(ParseArtifact)
                .FirstOrDefault(item => item != null && item.Name == artifactName);
            return match;
        }

        private static GithubArtifactInfo ParseArtifact(JToken token) {
            if (token == null)
                return null;

            return new GithubArtifactInfo {
                Id = token["id"]?.Value<long>() ?? 0,
                Name = token["name"]?.Value<string>(),
            };
        }

        public static GithubArtifactInfo FindLatestBranchArtifact(string repoId, string branchName) {
            if (!BinArtifactSupport.IsSupportedCiBinBranch(branchName))
                return null;

            var url = string.Format(
                "https://api.github.com/repos/{0}/actions/workflows/{1}/runs?branch={2}&status=completed&per_page=20",
                repoId,
                CiWorkflowFileName,
                Uri.EscapeDataString(branchName));
            var payload = GetJson(url, requireAuth: true);
            var runs = payload["workflow_runs"] as JArray;
            if (runs == null)
                return null;

            foreach (var runToken in runs) {
                var conclusion = runToken["conclusion"]?.Value<string>();
                if (!string.Equals(conclusion, "success", StringComparison.OrdinalIgnoreCase))
                    continue;

                var runId = runToken["id"]?.Value<long>() ?? 0;
                var headSha = runToken["head_sha"]?.Value<string>();
                if (runId <= 0 || string.IsNullOrWhiteSpace(headSha))
                    continue;

                var artifactName = UnsignedBinArtifactPrefix + headSha;
                var artifact = FindArtifactForRun(repoId, runId, artifactName);
                if (artifact != null) {
                    artifact.WorkflowRunId = runId;
                    return artifact;
                }
            }

            return null;
        }

        private static GithubArtifactInfo FindArtifactForRun(string repoId, long runId, string artifactName) {
            var url = string.Format(
                "https://api.github.com/repos/{0}/actions/runs/{1}/artifacts?per_page=5",
                repoId,
                runId);
            var payload = GetJson(url, requireAuth: true);
            var artifacts = payload["artifacts"] as JArray;
            if (artifacts == null || artifacts.Count == 0)
                return null;

            return artifacts
                .Select(ParseArtifact)
                .FirstOrDefault(item => item != null && item.Name == artifactName);
        }

        public static string DownloadArtifactZip(string repoId, long artifactId, string destPath) {
            var url = string.Format(
                "https://api.github.com/repos/{0}/actions/artifacts/{1}/zip",
                repoId,
                artifactId);
            logger.Debug("Downloading artifact \"{0}\" to \"{1}\"", artifactId, destPath);

            if (!CommonUtils.CheckInternetConnection())
                throw new pyRevitNoInternetConnectionException();

            using (var request = BuildRequest(HttpMethod.Get, url, requireAuth: true))
            using (var response = CommonUtils.SendHttpRequest(request)) {
                if (!response.IsSuccessStatusCode) {
                    var body = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();
                    throw new PyRevitException(string.Format(
                        "GitHub artifact download failed ({0}): {1}", (int)response.StatusCode, body));
                }

                CommonUtils.CopyHttpContentToFile(response.Content, destPath);
            }

            return destPath;
        }
    }
}
