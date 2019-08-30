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
        public static string GetScriptFileExt(PyRevitScriptTypes scriptType) {
            switch (scriptType) {
                case PyRevitScriptTypes.Python: return PyRevitConsts.BundleScriptPythonPostfix;
                case PyRevitScriptTypes.CSharp: return PyRevitConsts.BundleScriptCSharpPostfix;
                case PyRevitScriptTypes.VisualBasic: return PyRevitConsts.BundleScriptVisualBasicPostfix;
                case PyRevitScriptTypes.Ruby: return PyRevitConsts.BundleScriptRubyPostfix;
                case PyRevitScriptTypes.Dynamo: return PyRevitConsts.BundleScriptDynamoBIMPostfix;
                case PyRevitScriptTypes.Grasshopper: return PyRevitConsts.BundleScriptGrasshopperPostfix;
                case PyRevitScriptTypes.RevitFamily: return PyRevitConsts.BundleScriptRevitFamilyPostfix;
                default: return null;
            }
        }
    }
}
