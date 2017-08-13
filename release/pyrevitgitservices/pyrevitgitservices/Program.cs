using System;
using System.Linq;
using System.Collections.Generic;
using System.Reflection;
using LibGit2Sharp;
using Mono.Options;

namespace pyrevitgitservices
{
    class Program
    {
        private static string commiterName = "eirannejad";
        private static string commiterEmail = "eirannejad@gmail.com";
        private static Identity commiterId = new Identity(commiterName, commiterEmail);

        static void Main(string[] args)
        {
            var suite = new CommandSet("pyrevitgitservices")
            {
                "usage: pyrevitgitservices COMMAND PARAM [,PARAM] [OPTIONS]+",
                { "v|version", "prints version", v => Console.WriteLine(Assembly.GetExecutingAssembly().GetName().Version)},
                new Command ("clone", "clones the pyrevit git repo")
                {
                    Run = cargs => { Clone(cargs.ToList()); }
                },

                 new Command ("update", "updates the pyrevit repo to the most recent version")
                {
                    Run = cargs => { Update(cargs.ToList()); }
                },

                new Command ("setversion", "rebases the pyrevit repo to a specific commit")
                {
                    Run = cargs => { ChangeVersion(cargs.ToList()); }
                }
            };

            suite.Run(args);
        }

        static void Clone(List<string> cloneArgs)
        {
            if (cloneArgs.Count == 1)
            {
                var destPath = cloneArgs[0];
                var cops = new CloneOptions();
                cops.Checkout = true;
                cops.BranchName = "master";
                Console.WriteLine(String.Format("Cloning pyRevit into: {0}", destPath));
                Repository.Clone("https://github.com/eirannejad/pyRevit.git", destPath, cops);

                var repo = new Repository(destPath);
                if (repo != null)
                    Console.WriteLine(String.Format("Successfully cloned pyRevit into: {0}", destPath));
                else
                    Console.WriteLine(String.Format("Failed to verify successful clone of pyRevit to: {0}", destPath));
            }
            else
            {
                Console.WriteLine("Provide destination path to clone the repo into.");
            }
        }

        static void Update(List<string> updateArgs)
        {
            if (updateArgs.Count == 1)
            {
                var repoPath = updateArgs[0];

                var repo = new Repository(repoPath);
                var options = new PullOptions();
                options.FetchOptions = new FetchOptions();

                // before updating, let's first
                // forced checkout to overwrite possible local changes
                // Re: https://github.com/eirannejad/pyRevit/issues/229
                var checkoutOptions = new CheckoutOptions();
                checkoutOptions.CheckoutModifiers = CheckoutModifiers.Force;
                Commands.Checkout(repo, repo.Head, checkoutOptions);

                // now let's pull from the tracked remote
                Console.WriteLine(String.Format("Updating repo at: {0}", repoPath));
                var res = Commands.Pull(repo, new Signature("pyRevitCoreUpdater", commiterEmail, new DateTimeOffset(DateTime.Now)), options);

                // process the results and let user know
                if (res.Status == MergeStatus.FastForward)
                    Console.WriteLine("Successfully updated repo to HEAD");
                else if (res.Status == MergeStatus.UpToDate)
                    Console.WriteLine("Repo is already up to date.");
                else if (res.Status == MergeStatus.Conflicts)
                    Console.WriteLine("There are conflicts to be resolved. Use the git tool to resolve conflicts.");
                else
                    Console.WriteLine("Failed updating repo to HEAD");
            }
            else
            {
                Console.WriteLine("Provide repo path to update.");
            }
        }

        static void ChangeVersion(List<string> rebaseArgs)
        {
            if (rebaseArgs.Count == 2)
            {
                var repoPath = rebaseArgs[0];
                var commitHash = rebaseArgs[1];

                var repo = new Repository(repoPath);

                // trying to find commit in current branch
                Commit desCommit = null;
                foreach (Commit cmt in repo.Commits)
                {
                    if (cmt.Id.ToString().StartsWith(commitHash))
                    {
                        desCommit = cmt;
                        break;
                    }
                }

                if (desCommit != null)
                {
                    Console.WriteLine(String.Format("Target commit found: {0}", desCommit.Id.ToString()));
                    Console.WriteLine("Attempting rebase...");
                    var tempBranch = repo.CreateBranch("rebasetemp", desCommit);
                    repo.Rebase.Start(repo.Head, repo.Head, tempBranch, commiterId, new RebaseOptions());
                    repo.Branches.Remove(tempBranch);
                    Console.WriteLine(String.Format("Rebase successful. Repo is now at commit: {0}", repo.Head.Tip.Id.ToString()));
                }
                else
                {
                    Console.WriteLine("Could not find target commit.");
                }

            }
            else
            {
                Console.WriteLine("Provide repo path and target commit hash.");
            }
        }
    }
}
