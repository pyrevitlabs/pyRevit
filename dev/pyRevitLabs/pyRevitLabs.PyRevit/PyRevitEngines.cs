using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

using pyRevitLabs.Common.Extensions;
using pyRevitLabs.TargetApps.Revit;

namespace pyRevitLabs.PyRevit {
    public static class PyRevitEngines {
        public static PyRevitEngine GetEngineFromManifest(RevitAddonManifest manifest, PyRevitClone clone) {
            foreach (var engine in clone.GetEngines())
                if (manifest.Assembly.IsPathWithin(engine.Path))
                    return engine;
            return null;
        }

        /// <summary>
        /// The engine of <paramref name="clone"/> whose folder contains <paramref name="path"/>, or null.
        /// </summary>
        public static PyRevitEngine FindContaining(PyRevitClone clone, string path) {
            foreach (var engine in clone.GetEngines())
                if (path.IsPathWithin(engine.Path))
                    return engine;
            return null;
        }
    }
}
