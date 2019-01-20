using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

using pyRevitLabs.TargetApps.Revit;

namespace pyRevitLabs.TargetApps.Revit {
    public class PyRevitAttachment {
        public PyRevitAttachment(RevitAddonManifest manifest, RevitProduct product, PyRevitAttachmentType attachmentType) {
            Manifest = manifest;
            Product = product;
            AttachmentType = attachmentType;
        }

        public RevitAddonManifest Manifest { get; private set; }
        public RevitProduct Product { get; private set; }
        public PyRevitAttachmentType AttachmentType { get; private set; }

        public PyRevitClone Clone => GetCloneFromManifest(Manifest);
        public PyRevitEngine Engine => GetEngineFromManifest(Manifest, Clone);
        public bool AllUsers => AttachmentType == PyRevitAttachmentType.AllUsers;

        public static PyRevitClone GetCloneFromManifest(RevitAddonManifest manifest) {
            foreach (var clone in PyRevit.GetRegisteredClones())
                if (manifest.Assembly.Contains(clone.ClonePath))
                    return clone;
            return null;
        }

        public static PyRevitEngine GetEngineFromManifest(RevitAddonManifest manifest, PyRevitClone clone) {
            foreach (var engine in clone.GetEngines())
                if (manifest.Assembly.Contains(engine.Path))
                    return engine;
            return null;
        }

    }
}
