using System;
using System.Linq;
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
                    
                    // for each subkey
                    foreach (string subkeyName in key.GetSubKeyNames())
                        // test if it references any of the pyrevit products
                        foreach (var product in Program.LoadProducts())
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
            var targetKey = searchTargetKey.OpenSubKey(subKeyName);
            try {
                // if product code is listed in iconpath, assume a match
                var productName = (string)targetKey.GetValue("ProductName");
                var productIcon = (string)targetKey.GetValue("ProductIcon");
                targetKey.Close();
                if (productName == product.Name && productIcon.Contains(product.Key)) {
                    
                    // cleanup reference under Features
                    var featuresKey = RegistryKey.OpenBaseKey(searchTarget.BaseKey, RegistryView.Default).OpenSubKey(searchTarget.SubKeyName.Replace(@"\Products", @"\Features"), writable: true);
                    if (featuresKey.GetSubKeyNames().Contains(subKeyName))
                        try {
                            if (!dryrun) {
                                featuresKey.DeleteSubKey(subKeyName);
                                Console.WriteLine($"Deleted {featuresKey.Name}\\{subKeyName}\\ ({product.Name} {product.Version})");
                            }
                            else
                                Console.WriteLine($"Fake Deleted {featuresKey.Name}\\{subKeyName}\\ ({product.Name} {product.Version})");
                        }
                        catch (Exception delEx) {
                            Console.WriteLine($"Error Deleting {featuresKey.Name}\\{subKeyName}\\ ({product.Name} {product.Version}) | {delEx.Message}");
                        }
                    featuresKey.Close();
                    
                    // cleanup reference under UpgradeCodes
                    var upgradeInfoKey = RegistryKey.OpenBaseKey(searchTarget.BaseKey, RegistryView.Default).OpenSubKey(searchTarget.SubKeyName.Replace(@"\Products", @"\UpgradeCodes"), writable: true);
                    foreach(var upgradeInfoSubKeyName in upgradeInfoKey.GetSubKeyNames()) {
                        var subUpgradeInfoKey = upgradeInfoKey.OpenSubKey(upgradeInfoSubKeyName, writable: true);
                        if (subUpgradeInfoKey.GetValueNames().Contains(subKeyName))
                            try {
                                if (!dryrun) {
                                    subUpgradeInfoKey.DeleteValue(subKeyName);
                                    Console.WriteLine($"Deleted {subUpgradeInfoKey.Name}\\{subKeyName} ({product.Name} {product.Version})");
                                }
                                else
                                    Console.WriteLine($"Fake Deleted {subUpgradeInfoKey.Name}\\{subKeyName} ({product.Name} {product.Version})");
                            }
                            catch (Exception delEx) {
                                Console.WriteLine($"Error Deleting {subUpgradeInfoKey.Name}\\{subKeyName} ({product.Name} {product.Version}) | {delEx.Message}");
                            }
                    }
                    upgradeInfoKey.Close();
                    
                    // return true so the root key gets deleted also
                    return true;
                }
            }
            catch { }
            
            // close opened key and return
            if (targetKey != null)
                targetKey.Close();
            return false;
        }
    }
}
