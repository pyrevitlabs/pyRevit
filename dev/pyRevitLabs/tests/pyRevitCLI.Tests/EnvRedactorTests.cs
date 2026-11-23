using pyRevitCLI;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

[Collection(CliGlobalState.Name)]
[Trait("Level", "Unit")]
[Trait("Environment", "HostFree")]
public class EnvRedactorTests {
    private const string Profile = @"C:\Users\jane.doe";

    [Fact]
    public void UserFolderInPathsIsMaskedAndTheRestOfThePathKept() {
        var redacted = PyRevitEnvRedactor.RedactText(@"Active Config: ""C:\Users\jane.doe\AppData\Roaming\pyRevit\pyRevit_config.ini""", Profile);

        Assert.Equal(@"Active Config: ""C:\Users\***\AppData\Roaming\pyRevit\pyRevit_config.ini""", redacted);
    }

    [Fact]
    public void ProfileFolderWithSpacesIsMaskedCompletely() {
        var redacted = PyRevitEnvRedactor.RedactText(@"C:\Users\Jane Doe\AppData\Roaming", @"C:\Users\Jane Doe");

        Assert.Equal(@"C:\Users\***\AppData\Roaming", redacted);
    }

    [Fact]
    public void ProfileOutsideTheUsersFolderIsMaskedFromTheKnownProfilePath() {
        var redacted = PyRevitEnvRedactor.RedactText(@"D:\Profiles\jdoe\AppData\Roaming", @"D:\Profiles\jdoe");

        Assert.Equal(@"D:\Profiles\***\AppData\Roaming", redacted);
    }

    [Fact]
    public void OtherUsersProfileFoldersAreMaskedWithoutAKnownProfile() {
        var redacted = PyRevitEnvRedactor.RedactText(@"C:\Users\bob\AppData\Roaming\pyRevit-Master", Profile);

        Assert.Equal(@"C:\Users\***\AppData\Roaming\pyRevit-Master", redacted);
    }

    [Fact]
    public void ForwardSlashPathsAreMasked() {
        var redacted = PyRevitEnvRedactor.RedactText("C:/Users/jane.doe/source/repo", Profile);

        Assert.Equal("C:/Users/***/source/repo", redacted);
    }

    [Fact]
    public void UncServerNamesAreMasked() {
        var redacted = PyRevitEnvRedactor.RedactText(@"\\corp-fs01\tools\pyrevit", Profile);

        Assert.Equal(@"\\***\tools\pyrevit", redacted);
    }

    [Theory]
    [InlineData("https://github.com/pyrevitlabs/pyRevit.git", "https://github.com/pyrevitlabs/pyRevit.git")]
    [InlineData("https://raw.githubusercontent.com/pyrevitlabs/pyRevit/develop/extensions/extensions.json", "https://raw.githubusercontent.com/pyrevitlabs/pyRevit/develop/extensions/extensions.json")]
    [InlineData("https://gitlab.com/group/repo.git", "https://gitlab.com/group/repo.git")]
    public void PublicGitHostsKeepTheirUrl(string url, string expected) {
        Assert.Equal(expected, PyRevitEnvRedactor.RedactText(url, Profile));
    }

    [Theory]
    [InlineData("https://git.corp.example.com/team/private-repo.git", "https://***/***.git")]
    [InlineData("https://git.corp.example.com:8443/team/private-repo", "https://***/***")]
    [InlineData("https://intranet.example.com", "https://***")]
    [InlineData("ssh://git@git.corp.example.com/team/private-repo.git", "ssh://***@***/***.git")]
    public void NonPublicHostsAreMaskedKeepingSchemeAndGitSuffix(string url, string expected) {
        Assert.Equal(expected, PyRevitEnvRedactor.RedactText(url, Profile));
    }

    [Theory]
    [InlineData("https://user:s3cret@github.com/org/repo.git", "https://***@github.com/org/repo.git")]
    [InlineData("https://ghp_token@github.com/org/repo.git", "https://***@github.com/org/repo.git")]
    [InlineData("https://user:s3cret@git.corp.example.com/org/repo.git", "https://***@***/***.git")]
    public void EmbeddedCredentialsAreAlwaysMasked(string url, string expected) {
        var redacted = PyRevitEnvRedactor.RedactText(url, Profile);

        Assert.Equal(expected, redacted);
        Assert.DoesNotContain("s3cret", redacted);
        Assert.DoesNotContain("ghp_token", redacted);
    }

    [Theory]
    [InlineData("https://user:sec'ret@git.corp.example.com/team/repo.git", "sec'ret")]
    [InlineData("https://user:pa@ss@git.corp.example.com/team/repo.git", "pa@ss")]
    [InlineData("https://user:pa@github.com@git.corp.example.com/team/repo.git", "pa@github.com")]
    public void PasswordsWithApostrophesOrAtSignsAreMaskedCompletely(string url, string password) {
        var redacted = PyRevitEnvRedactor.RedactText(url, Profile);

        Assert.Equal("https://***@***/***.git", redacted);
        Assert.DoesNotContain(password, redacted);
    }

    [Theory]
    [InlineData("git@git.corp.example.com:team/private-repo.git", "***@***:***.git")]
    [InlineData("git@git.corp.example.com:private-repo", "***@***:***")]
    [InlineData("git@github.com:pyrevitlabs/pyRevit.git", "***@github.com:pyrevitlabs/pyRevit.git")]
    [InlineData("Repo: \"git@git.corp.example.com:team/repo.git\" ", "Repo: \"***@***:***.git\" ")]
    public void ScpStyleGitRemotesAreMasked(string remote, string expected) {
        Assert.Equal(expected, PyRevitEnvRedactor.RedactText(remote, Profile));
    }

    [Theory]
    [InlineData("git.corp.example.com:team/private.git", "***:***.git")]
    [InlineData("git.corp.example.com:private-repo", "***:***")]
    [InlineData("Origin \"git.corp.example.com:team/private.git\" cloned", "Origin \"***:***.git\" cloned")]
    [InlineData("github.com:pyrevitlabs/pyRevit.git", "github.com:pyrevitlabs/pyRevit.git")]
    public void ScpStyleRemotesWithoutAUserNameAreMasked(string remote, string expected) {
        Assert.Equal(expected, PyRevitEnvRedactor.RedactText(remote, Profile));
    }

    [Theory]
    [InlineData(@"C:\Users\***\repo")]
    [InlineData("Version: 7.0.0.26278+2233")]
    [InlineData("Latest Installed .Net Framework: 10.0.14")]
    [InlineData("Engine: DEFAULT (2712)")]
    [InlineData("localhost:8080/path")]
    [InlineData("example.com:8080/path")]
    public void TextThatOnlyLooksLikeAHostAndPathIsLeftAlone(string text) {
        Assert.Equal(text, PyRevitEnvRedactor.RedactText(text, Profile));
    }

    [Fact]
    public void BracketedIpv6HostsAreMaskedWithTheirQuery() {
        var redacted = PyRevitEnvRedactor.RedactText("https://[fd00::abcd]:8443/repo.git?token=secret", Profile);

        Assert.Equal("https://***/***.git?***", redacted);
    }

    [Fact]
    public void QueryValuesWithApostrophesAreMaskedCompletely() {
        var redacted = PyRevitEnvRedactor.RedactText("https://github.com/org/repo.git?token=abc'def", Profile);

        Assert.Equal("https://github.com/org/repo.git?***", redacted);
    }

    [Fact]
    public void OtherUsersProfileFolderWithSpacesAndApostrophesIsMaskedCompletely() {
        var redacted = PyRevitEnvRedactor.RedactText(
            @"""C:\Users\Jane Doe\repo"" ""C:\Users\O'Brien\repo""",
            @"C:\Users\bob");

        Assert.Equal(@"""C:\Users\***\repo"" ""C:\Users\***\repo""", redacted);
    }

    [Theory]
    [InlineData(@"\\corp-fs01", @"\\***")]
    [InlineData(@"""\\corp-fs01""", @"""\\***""")]
    [InlineData(@"\\corp-fs01.example.com\share", @"\\***\share")]
    [InlineData(@"\\?\C:\long\path", @"\\?\C:\long\path")]
    public void ServerOnlyAndQualifiedUncEntriesAreMasked(string path, string expected) {
        Assert.Equal(expected, PyRevitEnvRedactor.RedactText(path, Profile));
    }

    [Theory]
    [InlineData(@"\\fileserver\profiles\jane.doe\AppData\Roaming", @"\\***\profiles\***\AppData\Roaming")]
    [InlineData(@"D:\Redirected\Jane.Doe", @"D:\Redirected\***")]
    public void UserNameSegmentsOutsideTheProfileAreMasked(string path, string expected) {
        Assert.Equal(expected, PyRevitEnvRedactor.RedactText(path, Profile, "jane.doe"));
    }

    [Fact]
    public void DriveRelativePathsWithTheUserNameAreMasked() {
        Assert.Equal(@"C:***\bin", PyRevitEnvRedactor.RedactText(@"C:jane.doe\bin", Profile, "jane.doe"));
    }

    [Theory]
    [InlineData(@"C:\Users\janet\repo", @"C:\Users\***\repo")]
    [InlineData(@"C:\Users\jane.doe2\repo", @"C:\Users\***\repo")]
    [InlineData(@"C:/Users/jane.doe-old/repo", @"C:/Users/***/repo")]
    public void SiblingFoldersSharingTheProfileNameAsPrefixAreMaskedWhole(string path, string expected) {
        Assert.Equal(expected, PyRevitEnvRedactor.RedactText(path, @"C:\Users\jane"));
    }

    [Theory]
    [InlineData(@"D:\Profiles\jdoe o'neil\x")]
    [InlineData(@"D:\Profiles\jdoe two\x")]
    [InlineData(@"D:\Profiles\jdoe'x\x")]
    public void SiblingOfAProfileOutsideUsersWithSpacesOrApostrophesIsMaskedWhole(string path) {
        Assert.Equal(@"D:\Profiles\***\x", PyRevitEnvRedactor.RedactText(path, @"D:\Profiles\jdoe"));
    }

    [Theory]
    [InlineData("https://git.corp.example.com/team'private?token=secret", "https://***/***?***")]
    [InlineData("\"https://git.corp.example.com/team'private.git\" next", "\"https://***/***.git\" next")]
    public void PrivateUrlPathsWithApostrophesAreMaskedWhole(string text, string expected) {
        var redacted = PyRevitEnvRedactor.RedactText(text, Profile);

        Assert.Equal(expected, redacted);
        Assert.DoesNotContain("private", redacted);
    }

    [Theory]
    [InlineData("origin 'https://git.corp.example.com/team/private.git' next", "origin 'https://***/***.git' next")]
    [InlineData("origin 'https://git.corp.example.com/team/private?token=abc' next", "origin 'https://***/***?***' next")]
    [InlineData("origin 'https://github.com/org/repo.git' next", "origin 'https://github.com/org/repo.git' next")]
    [InlineData("'https://git.corp.example.com/team/private.git'", "'https://***/***.git'")]
    [InlineData("origin 'https://git.corp.example.com/team'private?token=secret' next", "origin 'https://***/***?***' next")]
    [InlineData("'https://git.corp.example.com/team'private.git'", "'https://***/***.git'")]
    [InlineData("'https://git.corp.example.com/team'/private?token=secret'", "'https://***/***?***'")]
    [InlineData("origin 'https://git.corp.example.com/team/private.git', next", "origin 'https://***/***.git', next")]
    [InlineData("(origin 'https://git.corp.example.com/team/private.git')", "(origin 'https://***/***.git')")]
    [InlineData("origin 'https://git.corp.example.com/team/private?token=abc'; next", "origin 'https://***/***?***'; next")]
    public void EnclosingSingleQuotesAreKeptAroundMaskedUrls(string text, string expected) {
        Assert.Equal(expected, PyRevitEnvRedactor.RedactText(text, Profile));
    }

    [Theory]
    [InlineData("https://git.corp.example.com/team'/private?token=secret", "https://***/***?***")]
    [InlineData("https://git.corp.example.com/team'private.git", "https://***/***.git")]
    [InlineData("https://git.corp.example.com/team/pri'vate'?token=sec'ret", "https://***/***?***")]
    public void UnquotedUrlsTreatApostrophesAsPartOfThePathAndQuery(string text, string expected) {
        var redacted = PyRevitEnvRedactor.RedactText(text, Profile);

        Assert.Equal(expected, redacted);
        Assert.DoesNotContain("private", redacted);
        Assert.DoesNotContain("secret", redacted);
    }

    [Fact]
    public void JsonValueWithASingleQuotedUrlContainingAnApostropheIsMaskedWithoutLeaking() {
        var json = new JObject { ["origin"] = "origin 'https://git.corp.example.com/team'private?token=secret' next" }.ToString(pyRevitLabs.Json.Formatting.None);

        var redacted = PyRevitEnvRedactor.RedactJson(json, Profile);

        Assert.DoesNotContain("private", redacted);
        Assert.DoesNotContain("secret", redacted);
        Assert.Contains("origin 'https://***/***?***' next", redacted);
    }

    [Fact]
    public void JsonValueWithAnApostropheInTheUrlPathIsMaskedWhole() {
        var json = new JObject { ["origin"] = "https://git.corp.example.com/team'/private?token=secret" }.ToString(pyRevitLabs.Json.Formatting.None);

        var redacted = JObject.Parse(PyRevitEnvRedactor.RedactJson(json, Profile));

        Assert.Equal("https://***/***?***", (string)redacted["origin"]);
    }

    [Fact]
    public void JsonValuesEndingInAQuoteAfterAUrlAreMaskedWithoutLosingTheQuote() {
        var json = new JObject { ["origin"] = "'https://git.corp.example.com/team/private.git'" }.ToString(pyRevitLabs.Json.Formatting.None);

        var redacted = JObject.Parse(PyRevitEnvRedactor.RedactJson(json, Profile));

        Assert.Equal("'https://***/***.git'", (string)redacted["origin"]);
    }

    [Fact]
    public void SiblingOfAProfileOutsideUsersIsMaskedWhole() {
        Assert.Equal(@"D:\Profiles\***\x", PyRevitEnvRedactor.RedactText(@"D:\Profiles\jdoe2\x", @"D:\Profiles\jdoe"));
    }

    [Theory]
    [InlineData("https://github.com/org/repo.git?access_token=secret", "https://github.com/org/repo.git?***", "secret")]
    [InlineData("https://github.com?token=secret", "https://github.com?***", "secret")]
    [InlineData("https://github.com/org/repo#secret", "https://github.com/org/repo#***", "secret")]
    [InlineData("https://git.corp.example.com/team/repo.git?token=secret", "https://***/***.git?***", "secret")]
    public void QueryStringsAndFragmentsOfUrlsAreMasked(string url, string expected, string secret) {
        var redacted = PyRevitEnvRedactor.RedactText(url, Profile);

        Assert.Equal(expected, redacted);
        Assert.DoesNotContain(secret, redacted);
    }

    [Fact]
    public void UserNameIsOnlyMaskedAsAWholePathSegment() {
        const string path = @"C:\tools\jane.doe.tools\jane.doe-cache";

        Assert.Equal(path, PyRevitEnvRedactor.RedactText(path, Profile, "jane.doe"));
    }

    [Fact]
    public void JsonRedactionMasksTheUserNameInPathsOutsideTheProfile() {
        var json = @"{""userEnv"":{""userAppdata"":""\\\\fileserver\\profiles\\jane.doe\\AppData\\Roaming""}}";

        var redacted = JObject.Parse(PyRevitEnvRedactor.RedactJson(json, Profile, "jane.doe"));

        Assert.Equal(@"\\***\profiles\***\AppData\Roaming", (string)redacted["userEnv"]["userAppdata"]);
    }

    [Fact]
    public void UrlInsideAQuotedTextLineIsMaskedWithoutEatingTheQuote() {
        var redacted = PyRevitEnvRedactor.RedactText(@"origin ""https://git.corp.example.com/team/repo.git"" at ""C:\Users\jane.doe\repo""", Profile);

        Assert.Equal(@"origin ""https://***/***.git"" at ""C:\Users\***\repo""", redacted);
    }

    [Fact]
    public void TextWithoutSensitiveValuesIsReturnedUnchanged() {
        const string line = "Admin Access: Yes";

        Assert.Equal(line, PyRevitEnvRedactor.RedactText(line, Profile));
    }

    [Fact]
    public void JsonRedactionMasksAccountsAndNestedStringsAndKeepsTheStructure() {
        var json = new JObject {
            ["clones"] = new JArray(new JObject {
                ["name"] = "master",
                ["clonePath"] = @"C:\Users\jane.doe\pyRevit",
                ["origin"] = "https://user:s3cret@git.corp.example.com/team/pyRevit.git",
            }),
            ["lookupSources"] = new JArray("https://raw.githubusercontent.com/pyrevitlabs/pyRevit/develop/extensions/extensions.json"),
            ["userEnv"] = new JObject {
                ["execUser"] = @"CORP\jane.doe",
                ["activeUser"] = @"CORP\jane.doe",
                ["isAdmin"] = false,
                ["userAppdata"] = @"C:\Users\jane.doe\AppData\Roaming",
                ["userPathEntries"] = new JArray(@"C:\Users\jane.doe\bin", @"C:\Program Files\dotnet"),
            },
        }.ToString(pyRevitLabs.Json.Formatting.None);

        var redacted = JObject.Parse(PyRevitEnvRedactor.RedactJson(json, Profile));

        Assert.Equal(@"C:\Users\***\pyRevit", (string)redacted["clones"][0]["clonePath"]);
        Assert.Equal("master", (string)redacted["clones"][0]["name"]);
        Assert.Equal("https://***@***/***.git", (string)redacted["clones"][0]["origin"]);
        Assert.Equal("https://raw.githubusercontent.com/pyrevitlabs/pyRevit/develop/extensions/extensions.json", (string)redacted["lookupSources"][0]);
        Assert.Equal(PyRevitEnvRedactor.Placeholder, (string)redacted["userEnv"]["execUser"]);
        Assert.Equal(PyRevitEnvRedactor.Placeholder, (string)redacted["userEnv"]["activeUser"]);
        Assert.False((bool)redacted["userEnv"]["isAdmin"]);
        Assert.Equal(@"C:\Users\***\AppData\Roaming", (string)redacted["userEnv"]["userAppdata"]);
        Assert.Equal(@"C:\Users\***\bin", (string)redacted["userEnv"]["userPathEntries"][0]);
        Assert.Equal(@"C:\Program Files\dotnet", (string)redacted["userEnv"]["userPathEntries"][1]);
        Assert.DoesNotContain("jane.doe", redacted.ToString());
        Assert.DoesNotContain("s3cret", redacted.ToString());
    }

    [Fact]
    public void JsonRedactionLeavesDateLikeStringsAsTheyWere() {
        var json = @"{""installDate"":""2026-11-05T07:13:00Z""}";

        var redacted = PyRevitEnvRedactor.RedactJson(json, Profile);

        Assert.Equal(json, redacted);
    }

    [Fact]
    public void RedactedRunFiltersConsoleOutputAndRestoresTheWriter() {
        var original = Console.Out;
        var captured = new StringWriter();
        Console.SetOut(captured);
        try {
            PyRevitEnvRedactor.RunRedacted(() => {
                Console.WriteLine(@"Clone ""C:\Users\jane.doe\pyRevit""");
                Console.WriteLine("origin https://git.corp.example.com/team/repo.git");
                Console.Write(@"no newline C:\Users\jane.doe");
            }, Profile);
            Console.WriteLine();
            Console.WriteLine(@"after C:\Users\jane.doe");
        }
        finally {
            Console.SetOut(original);
        }

        var lines = captured.ToString().Split(new[] { Environment.NewLine }, StringSplitOptions.None);
        Assert.Equal(@"Clone ""C:\Users\***\pyRevit""", lines[0]);
        Assert.Equal("origin https://***/***.git", lines[1]);
        Assert.Equal(@"no newline C:\Users\***", lines[2]);
        Assert.Equal(@"after C:\Users\jane.doe", lines[3]);
    }
}
