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
        /// <summary>
        /// Attach the given clone to one Revit product year.
        /// </summary>
        /// <exception cref="PyRevitException">
        /// The year is below <see cref="RevitProductData.MinimumSupportedProductYear"/>,
        /// the year is a known install whose executable is missing, or the engine cannot
        /// be used as a runtime. An attachment is only a manifest file, so writing one
        /// for an unsupported year would leave that Revit pointing at a loader it
        /// cannot load, with nothing on disk to show why. The executable check runs
        /// before the existing attachment is removed, so a year that cannot be attached
        /// never leaves the Revit it was already attached to with no attachment at all.
        /// </exception>
        // @handled @logs
        public static void Attach(int revitYear,
                                  PyRevitClone clone,
                                  PyRevitEngineVersion engineVer,
                                  bool allUsers = false,
                                  bool force = false) {
            if (!IsAttachableProductYear(revitYear))
                throw new PyRevitException(
                    $"Can not attach to Revit {revitYear}: this pyRevit line supports Revit "
                    + $"{RevitProductData.MinimumSupportedProductYear} or newer. Use a pyRevit release "
                    + $"that supports Revit {revitYear} to run pyRevit there.");

            // A year can carry more than one entry: the registry scan also matches
            // localized installs such as "Revit 2025 - German", and the set it returns
            // does not merge them, so two 2025 products can come back.
            var knownProduct = SelectProductForAttach(
                revitYear,
                RevitProduct.ListInstalledProducts());
            if (knownProduct != null && !CommonUtils.VerifyFile(knownProduct.ExecutiveLocation))
                throw new PyRevitException(
                    $"Can not attach to Revit {revitYear}: no executable found at "
                    + $"\"{knownProduct.ExecutiveLocation}\". The existing attachment was left as it is.");

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

        /// <summary>
        /// Whether this pyRevit line can run on a Revit product year at all.
        /// </summary>
        /// <remarks>
        /// The single source of truth for the year rule. It depends on nothing but the
        /// year, so a caller holding only a year - an explicit attach, a manifest found
        /// on disk - can apply the same rule the bulk paths apply.
        /// </remarks>
        public static bool IsAttachableProductYear(int revitYear) {
            return RevitProductData.IsSupportedProductYear(revitYear);
        }

        /// <summary>
        /// Whether this pyRevit line can be attached to an installed product.
        /// </summary>
        /// <remarks>
        /// The product-level form of <see cref="IsAttachableProductYear"/>, adding the
        /// check that the product's executable is actually on disk. Every path that
        /// writes or rewrites a manifest decides through this, so a bulk reattachment
        /// can never apply a looser rule than a direct attach. Callers log their own
        /// message, because the right wording differs: a first attach says the product
        /// is not a target, while a reattachment also has to say that the manifest
        /// already there is being kept.
        /// </remarks>
        public static bool IsAttachable(RevitProduct product) {
            return IsAttachableProductYear(product.ProductYear)
                   && CommonUtils.VerifyFile(product.ExecutiveLocation);
        }

        /// <summary>
        /// Pick the installed product an attach to a year should be validated against.
        /// </summary>
        /// <remarks>
        /// A single product year can yield more than one entry: the registry scan also
        /// matches localized installs such as "Revit 2025 - German", and the set it
        /// returns does not merge them, so the same year can come back twice. Choosing
        /// the first match would let a stale entry veto a year that has a perfectly good
        /// install, and in a bulk attach that aborts every year after it. An attachable
        /// entry therefore wins, and the fallback to any entry exists so a year whose
        /// only entry is stale still reports why it cannot be attached. Null when the
        /// year is not installed at all, which is not an error: attaching ahead of an
        /// install has to keep working.
        /// </remarks>
        public static RevitProduct SelectProductForAttach(int revitYear, IEnumerable<RevitProduct> products) {
            var yearProducts = products.Where(prod => prod.ProductYear == revitYear).ToList();
            return yearProducts.FirstOrDefault(IsAttachable) ?? yearProducts.FirstOrDefault();
        }

        /// <summary>
        /// Installed Revit products this pyRevit line can actually be attached to.
        /// </summary>
        /// <remarks>
        /// A product qualifies only when this line supports its product year and its
        /// executable is on disk. Both checks matter because an attachment is just a
        /// manifest file: written for a below-minimum year it points a host that
        /// cannot load the loader named in it, and written for a stale registry entry
        /// it points a Revit that is not installed. Side-by-side installs are a normal
        /// setup, so excluded products are named in the log rather than dropped
        /// silently, but a caller must never treat "installed" as "attachable".
        /// </remarks>
        public static List<RevitProduct> GetAttachableProducts() {
            return GetAttachableProducts(RevitProduct.ListInstalledProducts());
        }

        /// <summary>
        /// Filter a set of installed products down to the ones this line can be attached to.
        /// </summary>
        /// <remarks>
        /// Takes the products as an argument so the filter can be exercised against a
        /// known set instead of only against whatever happens to be installed. The
        /// registry-backed overload delegates here.
        /// </remarks>
        public static List<RevitProduct> GetAttachableProducts(IEnumerable<RevitProduct> products) {
            var attachable = new List<RevitProduct>();
            foreach (var product in products) {
                if (!IsAttachable(product)) {
                    if (!IsAttachableProductYear(product.ProductYear))
                        logger.Warn("Not attaching to Revit {0}: this pyRevit line supports Revit {1} or newer. " +
                                    "Use a pyRevit release that supports Revit {0} to run pyRevit there.",
                                    product.ProductYear, RevitProductData.MinimumSupportedProductYear);
                    else
                        logger.Warn("Not attaching to Revit {0}: no executable found at \"{1}\".",
                                    product.ProductYear, product.ExecutiveLocation);
                    continue;
                }
                attachable.Add(product);
            }
            return attachable;
        }

        /// <summary>
        /// Attach a clone to every installed Revit this pyRevit line can run on.
        /// </summary>
        /// <remarks>
        /// Products this line cannot run on are skipped with the reason logged, rather
        /// than aborting the ones it can.
        /// </remarks>
        // @handled @logs
        public static void AttachToAll(PyRevitClone clone, PyRevitEngineVersion engineVer, bool allUsers = false) {
            foreach (var revit in GetAttachableProducts())
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
