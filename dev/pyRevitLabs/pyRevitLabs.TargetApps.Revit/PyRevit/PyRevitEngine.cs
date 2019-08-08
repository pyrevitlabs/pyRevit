using System.IO;
using System.Linq;
using System.Collections.Generic;

using pyRevitLabs.Common.Extensions;

namespace pyRevitLabs.TargetApps.Revit {
    public class PyRevitEngine {
        // create engine from engine info
        public PyRevitEngine(int engineVer, bool runtime,
                             string enginePath, string assemblyName = PyRevit.LegacyEngineDllName,
                             string kernelName = "", string engineDescription = "",
                             IEnumerable<string> compatibleProducts = null) {
            Version = engineVer;
            Runtime = runtime;
            Path = enginePath;
            AssemblyName = assemblyName;
            KernelName = kernelName;
            Description = engineDescription;
            CompatibleProducts = compatibleProducts != null ? compatibleProducts.ToList() : new List<string>();
        }

        public override string ToString() {
            return string.Format(
                "Kernel: {0} | Version: {1} | Runtime: {2} | Path: \"{3}\" | Desc: \"{4}\" | Compatible: \"{5}\"",
                KernelName, Version, Runtime, AssemblyPath, Description, CompatibleProducts.ConvertToCommaSeparatedString());
        }

        public int Version { get; private set; }
        public bool Runtime { get; private set; }
        public string Path { get; private set; }
        public string AssemblyName { get; private set; }
        public string KernelName { get; private set; }

        public string AssemblyPath {
            get {
                return System.IO.Path.Combine(Path, AssemblyName).NormalizeAsPath();
            }
        }

        public string Description { get; private set; }
        public List<string> CompatibleProducts { get; private set; }

        public bool IsCompatibleWith(string productName) {
            return CompatibleProducts.Contains(productName);
        }
    }
}
