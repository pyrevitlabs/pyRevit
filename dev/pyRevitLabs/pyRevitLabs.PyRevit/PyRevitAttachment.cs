using System;
using System.Collections.Generic;
using System.IO;
using System.Security.AccessControl;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

using pyRevitLabs.Common;
using pyRevitLabs.TargetApps.Revit;

namespace pyRevitLabs.PyRevit {
    public enum PyRevitAttachmentType {
        AllUsers,
        CurrentUser
    }

    public class PyRevitAttachment {
        private PyRevitClone _clone = null;

        public PyRevitAttachment(RevitAddonManifest manifest,
                                 RevitProduct product,
                                 PyRevitAttachmentType attachmentType) {
            Manifest = manifest;
            Product = product;
            AttachmentType = attachmentType;
        }

        public override string ToString() {
            if (_clone != null) {
                var engine = Engine;

                return string.Format(
                    "{0} | Product: \"{1}\" | Engine: {2} | Path: \"{3}\" | Manifest: \"{4}\"",
                    _clone.Name,
                    Product.ProductName,
                    engine != null ? engine.Version : 0,
                    _clone.ClonePath,
                    Manifest.FilePath
                    );
            }
            else {
                return string.Format(
                    "Unknown | Product: \"{0}\" | Manifest: \"{1}\"",
                    Product.ProductName,
                    Manifest.FilePath
                    );
            }
        }

        public RevitAddonManifest Manifest { get; private set; }
        public RevitProduct Product { get; private set; }
        public PyRevitAttachmentType AttachmentType { get; private set; }

        public PyRevitClone Clone {
            get {
                if (_clone != null)
                    return _clone;
                else {
                    try {
                        _clone = PyRevitClone.GetCloneFromManifest(Manifest);
                        return _clone;
                    }
                    catch {
                        return null;
                    }
                }
            }
        }

        public PyRevitEngine Engine {
            get {
                if (_clone != null)
                    return PyRevitEngines.GetEngineFromManifest(Manifest, _clone);
                else
                    return null;
            }
        }
        public bool AllUsers => AttachmentType == PyRevitAttachmentType.AllUsers;

        public void SetClone(PyRevitClone clone) {
            _clone = clone;
        }

        public bool IsReadOnly() {
            // determine if attachment can be modified by user
            var us = new UserSecurity();
            return ! us.HasAccess(new FileInfo(Manifest.FilePath), FileSystemRights.Write);
        }
    }
}
