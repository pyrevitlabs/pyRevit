using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace pyRevitLabs.PyRevit {
    public enum PyRevitScriptTypes {
        Unknown,
        Python,
        CSharp,
        VisualBasic,
        Ruby,
        Dynamo,
        Grasshopper,
        RevitFamily
    }

    public class PyRevitScript {
        private static string[] GetScriptFileExt(PyRevitScriptTypes scriptType) {
            switch (scriptType) {
                case PyRevitScriptTypes.Python: return new string[] { PyRevitConsts.BundleScriptPythonPostfix };
                case PyRevitScriptTypes.CSharp: return new string[] { PyRevitConsts.BundleScriptCSharpPostfix };
                case PyRevitScriptTypes.VisualBasic: return new string[] { PyRevitConsts.BundleScriptVisualBasicPostfix };
                case PyRevitScriptTypes.Ruby: return new string[] { PyRevitConsts.BundleScriptRubyPostfix };
                case PyRevitScriptTypes.Dynamo: return new string[] { PyRevitConsts.BundleScriptDynamoBIMPostfix };
                case PyRevitScriptTypes.Grasshopper: return new string[] { PyRevitConsts.BundleScriptGrasshopperPostfix, PyRevitConsts.BundleScriptGrasshopperXPostfix };
                case PyRevitScriptTypes.RevitFamily: return new string[] { PyRevitConsts.BundleScriptRevitFamilyPostfix };
                default: return null;
            }
        }

        public static bool IsType(string scriptPath, PyRevitScriptTypes scriptType) {
            scriptPath = scriptPath.ToLower();
            foreach (string scriptEx in GetScriptFileExt(scriptType))
                if (scriptPath.EndsWith(scriptEx))
                    return true;
            return false;
        }
    }
}
