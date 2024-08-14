using System.IO;
using System.Linq;
using System.Collections.Generic;

using pyRevitLabs.Common.Extensions;

namespace pyRevitLabs.PyRevit {
    public class PyRevitEngineVersion {
        static public PyRevitEngineVersion Default => new PyRevitEngineVersion(0);
        
        public int Version { get; private set; }
        bool IsDefault => Version == 0;
        
        public PyRevitEngineVersion(int version) => Version = version;

        public static implicit operator int(PyRevitEngineVersion v) => v.Version;
        public static explicit operator PyRevitEngineVersion(int v) => new PyRevitEngineVersion(v);
        public static bool operator ==(PyRevitEngineVersion v1, PyRevitEngineVersion v2) => v1.Version == v2.Version;
        public static bool operator !=(PyRevitEngineVersion v1, PyRevitEngineVersion v2) => v1.Version != v2.Version;
        public static bool operator >(PyRevitEngineVersion v1, PyRevitEngineVersion v2) => v1.Version > v2.Version;
        public static bool operator <(PyRevitEngineVersion v1, PyRevitEngineVersion v2) => v1.Version < v2.Version;
        public static bool operator >=(PyRevitEngineVersion v1, PyRevitEngineVersion v2) => v1.Version >= v2.Version;
        public static bool operator <=(PyRevitEngineVersion v1, PyRevitEngineVersion v2) => v1.Version <= v2.Version;
        public static bool operator ==(PyRevitEngineVersion v1, int v2) => v1.Version == v2;
        public static bool operator !=(PyRevitEngineVersion v1, int v2) => v1.Version != v2;
        public static bool operator >(PyRevitEngineVersion v1, int v2) => v1.Version > v2;
        public static bool operator <(PyRevitEngineVersion v1, int v2) => v1.Version < v2;
        public static bool operator >=(PyRevitEngineVersion v1, int v2) => v1.Version >= v2;
        public static bool operator <=(PyRevitEngineVersion v1, int v2) => v1.Version <= v2;
        public override bool Equals(object obj) => Version.Equals(obj);
        public override int GetHashCode() => Version.GetHashCode();
        public override string ToString() => Version.ToString();
    }

    public class PyRevitEngine {
        // create engine from engine info
        public PyRevitEngine(string id,
                             PyRevitEngineVersion engineVer,
                             bool runtime,
                             string enginePath,
                             string assemblyName = PyRevitConsts.LegacyEngineDllName,
                             string kernelName = "",
                             string engineDescription = "",
                             bool isDefault = false) {
            Id = id;
            Version = engineVer;
            Runtime = runtime;
            Path = enginePath;
            AssemblyName = assemblyName;
            KernelName = kernelName;
            Description = engineDescription;
            IsDefault = isDefault;
        }

        public override string ToString() {
            return string.Format(
                "{0} | Kernel: {1} | Version: {2} | Runtime: {3} | Path: \"{4}\" | Desc: \"{5}\"",
                Id, KernelName, Version, Runtime, AssemblyPath, Description);
        }

        public string Id { get; private set; }
        public PyRevitEngineVersion Version { get; private set; }
        public bool Runtime { get; private set; }
        public string Path { get; private set; }
        public string AssemblyName { get; private set; }
        public string KernelName { get; private set; }
        public bool IsDefault { get; private set; }

        public string AssemblyPath {
            get {
                return System.IO.Path.Combine(Path, AssemblyName).NormalizeAsPath();
            }
        }

        public string Description { get; private set; }
    }
}
