using System;
using System.IO;
using System.Reflection;

// from this link (method 3)
// https://support.microsoft.com/en-us/help/837908/how-to-load-an-assembly-at-runtime-that-is-located-in-a-folder-that-is

namespace pyRevitLabs.TargetApps.Revit {
    public static class PyRevitBindings {
        // activates a resolver that looks into the current binary folder to find missing libraries
        public static void ActivateResolver() {
            AppDomain.CurrentDomain.AssemblyResolve += CurrentDomain_AssemblyResolve;
        }

        private static Assembly CurrentDomain_AssemblyResolve(object sender, ResolveEventArgs args) {
            try {
                // only respond if the request is coming from a pyRevit assembly
                if (args.RequestingAssembly != null && PyRevitClone.IsPyRevitAssembly(args.RequestingAssembly)) {
                    // this handler is called only when the runtime tries to bind to the assembly and fails
                    // retrieve the name and dll name of the missing assembly
                    string missingAssm = args.Name;
                    if (args.Name.IndexOf(",") > -1)
                        missingAssm = args.Name.Substring(0, args.Name.IndexOf(","));
                    string missingAssmDllName = missingAssm + ".dll";

                    // assuming this assembly has been shipped with this module, build the path and test of it exists
                    // in current assembly directory
                    var fullAssmDllPath =
                        Path.Combine(Path.GetDirectoryName(typeof(PyRevit).Assembly.Location), missingAssmDllName);

                    // load it if it exists
                    if (File.Exists(fullAssmDllPath)) {
                        // load the assembly from the specified path. 
                        var foundAssm = Assembly.LoadFrom(fullAssmDllPath);

                        // return the loaded assembly.
                        return foundAssm;
                    }
                }
            }
            catch {
                // just ignore if any exceptions occured due to null references and extracting assembly names
                // if exceptions is balooned up, the refrencing assemnly will have issues
            } 

            return null;
        }
    }
}
