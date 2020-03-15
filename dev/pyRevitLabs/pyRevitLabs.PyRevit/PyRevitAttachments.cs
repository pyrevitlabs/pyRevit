using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Text.RegularExpressions;
using System.Security.Principal;
using System.Text;
using System.Linq;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;

using MadMilkman.Ini;
using pyRevitLabs.Json.Linq;
using pyRevitLabs.NLog;
using pyRevitLabs.TargetApps.Revit;

namespace pyRevitLabs.PyRevit {
    public static class PyRevitAttachments {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();
        
        // managing attachments ======================================================================================
        // attach primary or given clone to revit version
        // @handled @logs
        public static void Attach(int revitYear,
                                  PyRevitClone clone,
                                  int engineVer,
                                  bool allUsers = false,
                                  bool force = false) {
            // make the addin manifest file
            var engine = clone.GetEngine(engineVer);

            if (engine.Runtime) {
                logger.Debug(string.Format("Attaching Clone \"{0}\" @ \"{1}\" to Revit {2}", clone.Name, clone.ClonePath, revitYear));

                // remove existing attachments first
                // this is critical as there might be invalid attachments to expired clones
                Detach(revitYear, currentAndAllUsers: true);

                // now recreate attachment
                RevitAddons.CreateManifestFile(
                    revitYear,
                    PyRevitConsts.AddinFileName,
                    PyRevitConsts.AddinName,
                    engine.AssemblyPath,
                    PyRevitConsts.AddinId,
                    PyRevitConsts.AddinClassName,
                    PyRevitConsts.VendorId,
                    allusers: allUsers
                    );
            }
            else
                throw new PyRevitException(string.Format("Engine {0} can not be used as runtime.", engineVer));
        }

        // attach clone to all installed revit versions
        // @handled @logs
        public static void AttachToAll(PyRevitClone clone, int engineVer = 000, bool allUsers = false) {
            foreach (var revit in RevitProduct.ListInstalledProducts())
                Attach(revit.ProductYear, clone, engineVer: engineVer, allUsers: allUsers);
        }

        // detach from revit version
        // @handled @logs
        public static void Detach(int revitYear, bool currentAndAllUsers = false) {
            logger.Debug("Detaching from Revit {0}", revitYear);
            RevitAddons.RemoveManifestFile(revitYear, PyRevitConsts.AddinName, currentAndAllUsers: currentAndAllUsers);
        }

        // detach pyrevit attachment
        // @handled @logs
        public static void Detach(PyRevitAttachment attachment) {
            logger.Debug("Detaching from Revit {0}", attachment.Product.ProductYear);
            Detach(attachment.Product.ProductYear);
        }

        // detach from all attached revits
        // @handled @logs
        public static void DetachAll() {
            foreach (var attachment in GetAttachments()) {
                Detach(attachment);
            }
        }

        // get all attached revit versions
        // @handled @logs
        public static List<PyRevitAttachment> GetAttachments() {
            var attachments = new List<PyRevitAttachment>();

            foreach (var revit in RevitProduct.ListInstalledProducts()) {
                logger.Debug("Checking attachment to Revit \"{0}\"", revit.Version);
                var userManifest = RevitAddons.GetAttachedManifest(PyRevitConsts.AddinName, revit.ProductYear, allUsers: false);
                var allUsersManifest = RevitAddons.GetAttachedManifest(PyRevitConsts.AddinName, revit.ProductYear, allUsers: true);

                PyRevitAttachment attachment = null;
                if (allUsersManifest != null) {
                    logger.Debug("pyRevit (All Users) is attached to Revit \"{0}\"", revit.Version);
                    attachment = new PyRevitAttachment(allUsersManifest, revit, PyRevitAttachmentType.AllUsers);

                }
                else if (userManifest != null) {
                    logger.Debug("pyRevit (Current User) is attached to Revit \"{0}\"", revit.Version);
                    attachment = new PyRevitAttachment(userManifest, revit, PyRevitAttachmentType.CurrentUser);
                }

                // verify attachment has found
                if (attachment != null) {
                    // try to find clone in registered clones
                    foreach (var clone in PyRevitClones.GetRegisteredClones()) {
                        if (attachment.Clone != null && attachment.Clone.ClonePath.Contains(clone.ClonePath)) {
                            attachment.SetClone(clone);
                            break;
                        }
                    }

                    attachments.Add(attachment);
                }
                else
                    logger.Debug("No attachment found for Revit \"{0}\"", revit.Version);
            }

            return attachments;
        }

        // get all attachments for a revit version
        // @handled @logs
        public static List<PyRevitAttachment> GetAllAttached(int revitYear) =>
            GetAttachments().Where(x => x.Product.ProductYear == revitYear).ToList<PyRevitAttachment>();

        // get attachment for a revit version
        // @handled @logs
        public static PyRevitAttachment GetAttached(int revitYear, bool allUsers = false) {
            foreach (PyRevitAttachment attachment in GetAllAttached(revitYear))
                if (attachment.AllUsers == allUsers)
                    return attachment;
            return null;
        }

    }
}
