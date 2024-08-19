﻿using System.IO;
using System.Security.AccessControl;

using pyRevitLabs.Common;
using pyRevitLabs.TargetApps.Revit;

namespace pyRevitLabs.PyRevit
{
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
                    "{0} | Product: \"{1}\" | Engine: {2} | Path: \"{3}\" {4}",
                    _clone.Name,
                    Product.Name,
                    engine != null ? $"{engine.Id} ({engine.Version})" : "?",
                    _clone.ClonePath,
                    AllUsers ? "| AllUsers" : ""
                    );
            }
            else {
                return string.Format(
                    "Unknown | Product: \"{0}\" | Manifest: \"{1}\"",
                    Product.Name,
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
