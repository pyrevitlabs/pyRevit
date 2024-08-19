﻿using pyRevitLabs.TargetApps.Revit;

namespace pyRevitLabs.PyRevit
{
    public static class PyRevitEngines {
        public static PyRevitEngine GetEngineFromManifest(RevitAddonManifest manifest, PyRevitClone clone) {
            foreach (var engine in clone.GetEngines())
                if (manifest.Assembly.Contains(engine.Path))
                    return engine;
            return null;
        }
    }
}
