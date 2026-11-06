using pyRevitCLI;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

[Collection(CliGlobalState.Name)]
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
