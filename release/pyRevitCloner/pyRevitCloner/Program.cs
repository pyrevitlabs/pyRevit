using System;
using LibGit2Sharp;

namespace pyRevitCloner
{
    class Programs
    {
        static void Main(string[] args)
        {
            var cops = new CloneOptions();
            cops.Checkout = true;
            cops.BranchName = "master";
            Repository.Clone(args[0], args[1], cops);
        }
    }
}
