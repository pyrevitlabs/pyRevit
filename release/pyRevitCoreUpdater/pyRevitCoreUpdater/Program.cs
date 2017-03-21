using System;
using LibGit2Sharp;

namespace pyRevitCoreUpdater
{
    class Program
    {
        static void Main(string[] args)
        {
            var repo = new Repository(args[0]);
            PullOptions options = new PullOptions();
            options.FetchOptions = new FetchOptions();
            var res = Commands.Pull(repo, new Signature("pyRevitCoreUpdater", "eirannejad@gmail.com", new DateTimeOffset(DateTime.Now)), options);
            Console.WriteLine(String.Format("Result: {0}", res.Status.ToString()));
        }
    }
}
