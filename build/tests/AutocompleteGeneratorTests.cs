using System.Diagnostics;
using System.Text.RegularExpressions;
using Build.Helpers;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Build.Tests;

[TestClass]
public sealed class AutocompleteGeneratorTests
{
    private const string AutocompSourceRepoPath = "dev/pyRevitLabs/pyRevitCLIAutoComplete/pyrevit-autocomplete.go";

    private static string ReadIndexedFile(string repoRelativePath)
    {
        var startInfo = new ProcessStartInfo("git", $"show :{repoRelativePath}")
        {
            WorkingDirectory = PyRevitPaths.Root,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
        };

        using var process = Process.Start(startInfo)!;
        var output = process.StandardOutput.ReadToEnd();
        var error = process.StandardError.ReadToEnd();
        process.WaitForExit();

        Assert.AreEqual(0, process.ExitCode, $"git show :{repoRelativePath} failed: {error}");
        return output;
    }

    private static string WithoutWhitespace(string text)
    {
        return Regex.Replace(text, @"\s+", string.Empty);
    }

    [TestMethod]
    public void Generate_shippedUsagePatterns_matchesCommittedSource()
    {
        var committed = ReadIndexedFile(AutocompSourceRepoPath);
        var generatedPath = Path.GetTempFileName();
        try
        {
            AutocompleteGenerator.Generate(PyRevitPaths.UsagePatterns, generatedPath);

            Assert.AreEqual(
                WithoutWhitespace(committed),
                WithoutWhitespace(File.ReadAllText(generatedPath)),
                $"{AutocompSourceRepoPath} is out of date with UsagePatterns.txt or the generator. "
                    + "Run the ci pipeline and commit the regenerated file.");
        }
        finally
        {
            File.Delete(generatedPath);
        }
    }

    private static IReadOnlyList<string> FlagsOf(string command, params string[] usageLines)
    {
        var commands = AutocompleteGenerator.CollectCommandFlags(usageLines);
        Assert.IsTrue(commands.ContainsKey(command), $"Command '{command}' was not generated.");
        return commands[command];
    }

    [TestMethod]
    public void CollectCommandFlags_hyphenatedFlag_keepsFullName()
    {
        var flags = FlagsOf("clone", "pyrevit clone <clone_name> [--skip-bin] [--persist-credentials]");

        CollectionAssert.AreEquivalent(new[] { "persist-credentials", "skip-bin" }, flags.ToArray());
    }

    [TestMethod]
    public void CollectCommandFlags_adjacentFlags_keepsEveryFlag()
    {
        var flags = FlagsOf(
            "clone",
            "pyrevit clone <clone_name> [--dest=<dest_path>] [--branch=<branch_name>] [--source=<repo_url>] [--log=<log_file>]");

        CollectionAssert.AreEquivalent(new[] { "branch", "dest", "log", "source" }, flags.ToArray());
    }

    [TestMethod]
    public void CollectCommandFlags_flagsInsideParentheses_areKept()
    {
        var flags = FlagsOf(
            "clones update",
            "pyrevit clones update (--all | <clone_name>) [(--username=<username> --password=<password> | --token=<auth_token>)]");

        CollectionAssert.AreEquivalent(new[] { "all", "password", "token", "username" }, flags.ToArray());
    }

    [TestMethod]
    public void CollectCommandFlags_flagThatPrefixesAnother_leavesNoResidue()
    {
        var commands = AutocompleteGenerator.CollectCommandFlags(
            new[] { "pyrevit attached [--all] [--allusers] [--attached]" });

        CollectionAssert.AreEquivalent(new[] { "all", "allusers", "attached" }, commands["attached"].ToArray());
        CollectionAssert.AreEquivalent(new[] { string.Empty, "attached" }, commands.Keys.ToArray());
    }

    [TestMethod]
    public void CollectCommandFlags_subcommandAlternatives_eachGetTheFlags()
    {
        var commands = AutocompleteGenerator.CollectCommandFlags(new[]
        {
            "pyrevit extend (ui | lib) <extension_name> <repo_url> [--dest=<dest_path>] [(--username=<username> --password=<password> | --token=<auth_token>)] [--persist-credentials]",
        });

        var expected = new[] { "dest", "password", "persist-credentials", "token", "username" };
        CollectionAssert.AreEquivalent(expected, commands["extend ui"].ToArray());
        CollectionAssert.AreEquivalent(expected, commands["extend lib"].ToArray());
    }

    [TestMethod]
    public void CollectCommandFlags_rootCommand_offersGlobalFlags()
    {
        var flags = FlagsOf(string.Empty, "pyrevit help");

        CollectionAssert.AreEquivalent(new[] { "debug", "verbose" }, flags.ToArray());
    }

    [TestMethod]
    public void KeepLineEndingsWhenUnchanged_onlyLineEndingsDiffer_restoresPreviousBytes()
    {
        var path = Path.GetTempFileName();
        try
        {
            const string previous = "package main\r\n\r\nfunc main() {}\r\n";
            File.WriteAllText(path, "package main\n\nfunc main() {}\n");

            AutocompleteGenerator.KeepLineEndingsWhenUnchanged(path, previous);

            Assert.AreEqual(previous, File.ReadAllText(path));
        }
        finally
        {
            File.Delete(path);
        }
    }

    [TestMethod]
    public void KeepLineEndingsWhenUnchanged_contentChanged_keepsGeneratedFile()
    {
        var path = Path.GetTempFileName();
        try
        {
            const string generated = "package main\n\nfunc main() { run() }\n";
            File.WriteAllText(path, generated);

            AutocompleteGenerator.KeepLineEndingsWhenUnchanged(path, "package main\r\n\r\nfunc main() {}\r\n");

            Assert.AreEqual(generated, File.ReadAllText(path));
        }
        finally
        {
            File.Delete(path);
        }
    }

    [TestMethod]
    public void KeepLineEndingsWhenUnchanged_noPreviousFile_keepsGeneratedFile()
    {
        var path = Path.GetTempFileName();
        try
        {
            const string generated = "package main\n";
            File.WriteAllText(path, generated);

            AutocompleteGenerator.KeepLineEndingsWhenUnchanged(path, null);

            Assert.AreEqual(generated, File.ReadAllText(path));
        }
        finally
        {
            File.Delete(path);
        }
    }

    [TestMethod]
    public void CollectCommandFlags_shippedUsagePatterns_completeExtendFlags()
    {
        var usageLines = File.ReadAllLines(PyRevitPaths.UsagePatterns).Skip(1);

        var commands = AutocompleteGenerator.CollectCommandFlags(usageLines);

        foreach (var command in new[] { "extend ui", "extend lib" })
        {
            CollectionAssert.IsSubsetOf(
                new[] { "branch", "dest", "log", "password", "persist-credentials", "token", "username" },
                commands[command].ToArray(),
                command);
        }

        CollectionAssert.Contains(commands["clone"].ToArray(), "skip-bin");
    }
}
