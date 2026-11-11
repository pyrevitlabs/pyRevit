using System;
using System.Collections.Generic;
using System.Linq;
using System.Security;
using System.Text.Json;
using Microsoft.Win32;

namespace pyRevitDoctor {
    /// <summary>
    /// <c>purge-installs</c>: removes registry records of pyRevit and pyRevit CLI installers.
    /// </summary>
    /// <remarks>
    /// Matching lives in <see cref="UninstallEntryMatcher"/>. Entries whose install is still present are
    /// reported as <c>Skipped (install present)</c> unless <see cref="PurgeOptions.Force"/> is set.
    /// </remarks>
    public static class PurgeInstalls {
        sealed record RegistryTarget(RegistryHive BaseKey, string SubKeyName, bool IsUninstallList);

        static readonly RegistryTarget[] SearchTargets = {
            new(RegistryHive.LocalMachine, @"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", IsUninstallList: true),
            new(RegistryHive.LocalMachine, @"SOFTWARE\Classes\Installer\Products", IsUninstallList: false),
            new(RegistryHive.CurrentUser, @"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", IsUninstallList: true),
            new(RegistryHive.CurrentUser, @"SOFTWARE\Microsoft\Installer\Products", IsUninstallList: false),
        };

        public static void Run(PurgeSession session) {
            session.Output.WriteLine("Purging old installs...");
            List<Product> products;
            try {
                products = Program.LoadProducts();
            }
            catch (JsonException ex) {
                Console.Error.WriteLine($"Can not load the embedded product list. Rebuild pyrevit-doctor with a valid pyrevit-products.json: {ex.Message}");
                Environment.ExitCode = 1;
                return;
            }

            foreach (var target in SearchTargets) {
                RegistryKey key;
                try {
                    key = OpenTargetKey(session, target);
                }
                catch {
                    session.Output.WriteLine($"Can not open \"({target.BaseKey})\\{target.SubKeyName}\". Run this command as admin");
                    continue;
                }

                if (key == null)
                    continue;

                using (key)
                    foreach (var subKeyName in key.GetSubKeyNames())
                        if (target.IsUninstallList)
                            PurgeUninstallEntry(session, key, subKeyName, products);
                        else
                            PurgeInstallerProduct(session, target, key, subKeyName, products);
            }
        }

        static RegistryKey OpenTargetKey(PurgeSession session, RegistryTarget target) {
            try {
                return OpenSubKey(target, writable: !session.Options.DryRun);
            }
            catch (Exception ex) when (ex is UnauthorizedAccessException or SecurityException) {
                return OpenSubKey(target, writable: false);
            }
        }

        static RegistryKey OpenSubKey(RegistryTarget target, bool writable) =>
            RegistryKey.OpenBaseKey(target.BaseKey, RegistryView.Default).OpenSubKey(target.SubKeyName, writable);

        static void PurgeUninstallEntry(PurgeSession session, RegistryKey uninstallKey, string subKeyName, List<Product> products) {
            var entry = ReadUninstallEntry(uninstallKey, subKeyName);
            var verdict = UninstallEntryMatcher.Classify(entry, products, session.Exists, session.Options.Force);
            var item = $@"{uninstallKey.Name}\{subKeyName}\ ({entry.DisplayName})";
            switch (verdict) {
                case UninstallVerdict.SkipInstallPresent:
                    session.ReportSkipped("install present", item);
                    break;
                case UninstallVerdict.Purge:
                    DeleteSubKeyTree(session, uninstallKey, subKeyName, item);
                    break;
            }
        }

        static UninstallEntry ReadUninstallEntry(RegistryKey uninstallKey, string subKeyName) {
            using var entryKey = uninstallKey.OpenSubKey(subKeyName);
            return new UninstallEntry {
                SubKeyName = subKeyName,
                DisplayName = entryKey?.GetValue("DisplayName") as string,
                UninstallString = entryKey?.GetValue("UninstallString") as string,
                InstallLocation = entryKey?.GetValue("InstallLocation") as string,
            };
        }

        static void PurgeInstallerProduct(PurgeSession session, RegistryTarget target, RegistryKey productsKey, string subKeyName, List<Product> products) {
            using var productKey = productsKey.OpenSubKey(subKeyName);
            var productName = productKey?.GetValue("ProductName") as string;
            var productIcon = productKey?.GetValue("ProductIcon") as string;
            var product = products.FirstOrDefault(candidate => productName == candidate.Name && productIcon != null && productIcon.Contains(candidate.Key));
            if (product == null)
                return;

            var item = $@"{productsKey.Name}\{subKeyName}\ ({product.Name} {product.Version})";
            try {
                DeleteFeatureReference(session, target, subKeyName, product);
                DeleteUpgradeCodeReferences(session, target, subKeyName, product);
            }
            catch (Exception ex) when (ex is UnauthorizedAccessException or SecurityException) {
                session.ReportFailed(item, ex);
                return;
            }
            DeleteSubKeyTree(session, productsKey, subKeyName, item);
        }

        static void DeleteFeatureReference(PurgeSession session, RegistryTarget target, string subKeyName, Product product) {
            using var featuresKey = RegistryKey.OpenBaseKey(target.BaseKey, RegistryView.Default)
                .OpenSubKey(target.SubKeyName.Replace(@"\Products", @"\Features"), writable: !session.Options.DryRun);
            if (featuresKey == null || !featuresKey.GetSubKeyNames().Contains(subKeyName))
                return;
            var item = $@"{featuresKey.Name}\{subKeyName}\ ({product.Name} {product.Version})";
            try {
                if (!session.Options.DryRun)
                    featuresKey.DeleteSubKey(subKeyName);
                session.ReportDeleted(item);
            }
            catch (Exception ex) {
                session.ReportFailed(item, ex);
            }
        }

        static void DeleteUpgradeCodeReferences(PurgeSession session, RegistryTarget target, string subKeyName, Product product) {
            using var upgradeCodesKey = RegistryKey.OpenBaseKey(target.BaseKey, RegistryView.Default)
                .OpenSubKey(target.SubKeyName.Replace(@"\Products", @"\UpgradeCodes"), writable: !session.Options.DryRun);
            if (upgradeCodesKey == null)
                return;
            foreach (var upgradeCodeName in upgradeCodesKey.GetSubKeyNames()) {
                using var upgradeCodeKey = upgradeCodesKey.OpenSubKey(upgradeCodeName, writable: !session.Options.DryRun);
                if (upgradeCodeKey == null || !upgradeCodeKey.GetValueNames().Contains(subKeyName))
                    continue;
                var item = $@"{upgradeCodeKey.Name}\{subKeyName} ({product.Name} {product.Version})";
                try {
                    if (!session.Options.DryRun)
                        upgradeCodeKey.DeleteValue(subKeyName);
                    session.ReportDeleted(item);
                }
                catch (Exception ex) {
                    session.ReportFailed(item, ex);
                }
            }
        }

        static void DeleteSubKeyTree(PurgeSession session, RegistryKey parentKey, string subKeyName, string item) {
            try {
                if (!session.Options.DryRun)
                    parentKey.DeleteSubKeyTree(subKeyName);
                session.ReportDeleted(item);
            }
            catch (Exception ex) {
                session.ReportFailed(item, ex);
            }
        }
    }
}
