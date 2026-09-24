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

        // session cache for GetAttachedCached(). GetAttachments() re-reads the
        // addin manifests and the clones registry from disk on every
        // enumeration, but within a running Revit session those inputs only
        // change through Attach/Detach or clone registry edits, which
        // invalidate this cache. The IronPython loader and the C# runtime share
        // it because both reference this single assembly; on reload it is
        // cleared via ClearAttachmentCache().
        private static readonly Dictionary<int, PyRevitAttachment> _attachmentCache =
            new Dictionary<int, PyRevitAttachment>();
        private static readonly object _attachmentCacheLock = new object();

        // managing attachments ======================================================================================
        // attach primary or given clone to revit version
        // @handled @logs
        public static void Attach(int revitYear,
                                  PyRevitClone clone,
                                  PyRevitEngineVersion engineVer,
                                  bool allUsers = false,
                                  bool force = false) {
            // make the addin manifest file
            var engine = clone.GetEngine(revitYear, engineVer);

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
                throw new PyRevitException($"Engine {engineVer} can not be used as runtime.");

            ClearAttachmentCache();
        }

        // attach clone to all installed revit versions
        // @handled @logs
        public static void AttachToAll(PyRevitClone clone, PyRevitEngineVersion engineVer, bool allUsers = false) {
            foreach (var revit in RevitProduct.ListInstalledProducts())
                Attach(revit.ProductYear, clone, engineVer: engineVer, allUsers: allUsers);
        }

        // detach from revit version
        // @handled @logs
        public static void Detach(int revitYear, bool currentAndAllUsers = false) {
            logger.Debug("Detaching from Revit {0}", revitYear);
            RevitAddons.RemoveManifestFile(revitYear, PyRevitConsts.AddinName, currentAndAllUsers: currentAndAllUsers);
            ClearAttachmentCache();
        }

        // detach pyrevit attachment
        // @handled @logs
        public static void Detach(PyRevitAttachment attachment, bool currentAndAllUsers = false) {
            logger.Debug("Detaching from Revit {0}", attachment.Product.ProductYear);
            Detach(attachment.Product.ProductYear, currentAndAllUsers);
        }

        // detach from all attached revits
        // @handled @logs
        public static void DetachAll(bool currentAndAllUsers = false) {
            foreach (var attachment in GetAttachments()) {
                Detach(attachment, currentAndAllUsers);
            }
        }

        private static PyRevitAttachment FindAttachment(RevitProduct revit) {
            logger.Debug("Checking attachment to Revit \"{0}\"", revit.Version);

            var allUsersManifest = RevitAddons.GetAttachedManifest(PyRevitConsts.AddinName, revit.ProductYear, allUsers: true);
            if (allUsersManifest != null) {
                logger.Debug("pyRevit (All Users) is attached to Revit \"{0}\"", revit.Version);
                return new PyRevitAttachment(allUsersManifest, revit, PyRevitAttachmentType.AllUsers);
            }

            var userManifest = RevitAddons.GetAttachedManifest(PyRevitConsts.AddinName, revit.ProductYear, allUsers: false);
            if (userManifest != null) {
                logger.Debug("pyRevit (Current User) is attached to Revit \"{0}\"", revit.Version);
                return new PyRevitAttachment(userManifest, revit, PyRevitAttachmentType.CurrentUser);
            }

            logger.Debug("No attachment found for Revit \"{0}\"", revit.Version);
            return null;
        }

        private static void ResolveRegisteredClone(PyRevitAttachment attachment, IEnumerable<PyRevitClone> registeredClones) {
            foreach (var clone in registeredClones) {
                if (attachment.Clone != null && attachment.Clone.ClonePath.Contains(clone.ClonePath)) {
                    attachment.SetClone(clone);
                    return;
                }
            }
        }

        /// <summary>
        /// Enumerate the pyRevit attachment of every installed Revit.
        /// </summary>
        /// <remarks>
        /// Reads the addin manifests of every installed Revit year and the clones
        /// registry from disk on every enumeration. Use <see cref="GetAllAttached(int)"/>
        /// when only one year is of interest.
        /// </remarks>
        public static IEnumerable<PyRevitAttachment> GetAttachments() {
            var registeredClones = PyRevitClones.GetRegisteredClones();

            foreach (var revit in RevitProduct.ListInstalledProducts()) {
                var attachment = FindAttachment(revit);
                if (attachment is null)
                    continue;
                ResolveRegisteredClone(attachment, registeredClones);
                yield return attachment;
            }
        }

        /// <summary>
        /// Get the pyRevit attachments of one Revit year.
        /// </summary>
        /// <remarks>
        /// Reads only that year's addin manifests, and reads the clones registry
        /// only once an attachment is found, so a year with no pyRevit attached
        /// costs no clone validation.
        /// </remarks>
        public static List<PyRevitAttachment> GetAllAttached(int revitYear) {
            var attachments = new List<PyRevitAttachment>();
            foreach (var revit in RevitProduct.ListInstalledProducts()) {
                if (revit.ProductYear != revitYear)
                    continue;
                var attachment = FindAttachment(revit);
                if (attachment != null)
                    attachments.Add(attachment);
            }

            if (attachments.Count > 0) {
                var registeredClones = PyRevitClones.GetRegisteredClones();
                foreach (var attachment in attachments)
                    ResolveRegisteredClone(attachment, registeredClones);
            }

            return attachments.OrderBy(x => x.AllUsers).ToList();
        }

        // get attachment for a revit version
        // @handled @logs
        public static PyRevitAttachment GetAttached(int revitYear) {
            return GetAllAttached(revitYear)?.FirstOrDefault();
        }

        // get attachment for a revit version, cached for the running session.
        // invalidated by Attach/Detach, clone registry changes, and reload.
        // @handled @logs
        public static PyRevitAttachment GetAttachedCached(int revitYear) {
            lock (_attachmentCacheLock) {
                // a missing manifest is cached as null so the disk scan is not
                // repeated for an unattached session
                if (_attachmentCache.TryGetValue(revitYear, out var cached))
                    return cached;
                var attachment = GetAttached(revitYear);
                _attachmentCache[revitYear] = attachment;
                return attachment;
            }
        }

        // drop cached attachments so the next lookup re-reads from disk
        // @handled @logs
        public static void ClearAttachmentCache() {
            lock (_attachmentCacheLock) {
                _attachmentCache.Clear();
            }
        }

    }
}
