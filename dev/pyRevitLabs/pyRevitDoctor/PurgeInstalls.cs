using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using Microsoft.Win32;

namespace pyRevitDoctor {
    public struct RegistryTarget {
        public RegistryHive BaseKey;
        public string SubKeyName;
        public Func<RegistryTarget, RegistryKey, string, Product, bool, bool> TestFunc;
    }

    static class PurgeInstalls {
        static RegistryTarget[] SearchTargets = new RegistryTarget[] {
            new RegistryTarget {
                BaseKey = RegistryHive.LocalMachine,
                SubKeyName = @"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                TestFunc = CheckProductNameOrVersion
            },
            new RegistryTarget {
                BaseKey = RegistryHive.LocalMachine,
                SubKeyName = @"SOFTWARE\Classes\Installer\Products",
                TestFunc = CheckInstallerProducts
            },
            new RegistryTarget {
                BaseKey = RegistryHive.CurrentUser,
                SubKeyName = @"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                TestFunc = CheckProductNameOrVersion
            },
            new RegistryTarget {
                BaseKey = RegistryHive.CurrentUser,
                SubKeyName = @"SOFTWARE\Microsoft\Installer\Products",
                TestFunc = CheckInstallerProducts
            },
        };

        public static void PurgeOldInstalls(bool dryrun) {
            Console.WriteLine("Purging old installs...");
            List<Product> products;
            try {
                products = Program.LoadProducts();
            }
            catch (JsonException ex) {
                Console.Error.WriteLine($"Can not load the embedded product list. Rebuild pyrevit-doctor with a valid pyrevit-products.json: {ex.Message}");
                Environment.ExitCode = 1;
                return;
            }

            // iterate thru the target and remove the key if matches
            foreach (RegistryTarget target in SearchTargets) {
                if (target.TestFunc != null) {
                    RegistryKey key;
                    try {
                        key = RegistryKey.OpenBaseKey(target.BaseKey, RegistryView.Default).OpenSubKey(target.SubKeyName, writable: true);
                    }
                    catch {
                        Console.WriteLine($"Can not open \"({target.BaseKey})\\{target.SubKeyName}\". Run this command as admin");
                        continue;
                    }

                    if (key == null)
                        continue;

                    // for each subkey
                    foreach (string subkeyName in key.GetSubKeyNames())
                        // test if it references any of the pyrevit products
                        foreach (var product in products)
                            // test match using the target function
                            if (target.TestFunc(target, key, subkeyName, product, dryrun))
                                try {
                                    if (!dryrun) {
                                        key.DeleteSubKeyTree(subkeyName);
                                        Console.WriteLine($"Deleted {key.Name}\\{subkeyName}\\ ({product.Name} {product.Version})");
                                    }
                                    else
                                        Console.WriteLine($"Fake Deleted {key.Name}\\{subkeyName}\\ ({product.Name} {product.Version})");
                                }
                                catch (Exception delEx) {
                                    Console.WriteLine($"Error Deleting {key.Name}\\{subkeyName}\\ ({product.Name} {product.Version}) | {delEx.Message}");
                                }
                    key.Close();
                }
            }
        }

        static bool CheckProductNameOrVersion(RegistryTarget searchTarget, RegistryKey searchTargetKey, string subKeyName, Product product, bool dryrun) {
            return subKeyName == product.Key || subKeyName == $"{product.Name} {product.Version}";
        }

        static bool CheckInstallerProducts(RegistryTarget searchTarget, RegistryKey searchTargetKey, string subKeyName, Product product, bool dryrun) {
            var label = $"{searchTargetKey.Name}\\{subKeyName} ({product.Name} {product.Version})";
            try {
                string productName;
                string productIcon;
                using (var targetKey = searchTargetKey.OpenSubKey(subKeyName)) {
                    if (targetKey == null)
                        return false;
                    productName = (string)targetKey.GetValue("ProductName");
                    productIcon = (string)targetKey.GetValue("ProductIcon");
                }
                if (productName != product.Name || productIcon == null || !productIcon.Contains(product.Key))
                    return false;

                using var baseKey = RegistryKey.OpenBaseKey(searchTarget.BaseKey, RegistryView.Default);
                using var featuresKey = baseKey.OpenSubKey(searchTarget.SubKeyName.Replace(@"\Products", @"\Features"), writable: true);
                using var upgradeInfoKey = baseKey.OpenSubKey(searchTarget.SubKeyName.Replace(@"\Products", @"\UpgradeCodes"), writable: true);
                if (featuresKey == null || upgradeInfoKey == null) {
                    Console.WriteLine($"Skipped {label} | the Features or UpgradeCodes registry key is missing, nothing was deleted");
                    return false;
                }

                if (featuresKey.GetSubKeyNames().Contains(subKeyName)) {
                    if (!dryrun)
                        featuresKey.DeleteSubKey(subKeyName);
                    Console.WriteLine($"{(dryrun ? "Fake Deleted" : "Deleted")} {featuresKey.Name}\\{subKeyName}\\ ({product.Name} {product.Version})");
                }

                foreach (var upgradeInfoSubKeyName in upgradeInfoKey.GetSubKeyNames()) {
                    using var subUpgradeInfoKey = upgradeInfoKey.OpenSubKey(upgradeInfoSubKeyName, writable: true);
                    if (subUpgradeInfoKey != null && subUpgradeInfoKey.GetValueNames().Contains(subKeyName)) {
                        if (!dryrun)
                            subUpgradeInfoKey.DeleteValue(subKeyName);
                        Console.WriteLine($"{(dryrun ? "Fake Deleted" : "Deleted")} {subUpgradeInfoKey.Name}\\{subKeyName} ({product.Name} {product.Version})");
                    }
                }

                return true;
            }
            catch (Exception ex) {
                Console.WriteLine($"Error purging {label}, its Products key was kept | {ex.Message}");
                return false;
            }
        }
    }
}
