using Microsoft.VisualStudio.TestTools.UnitTesting;
using System;
using System.IO;

using pyRevitLabs.TargetApps.Revit;

namespace pyRevitLabs.UnitTests.RevitAddons {
    [TestClass()]
    public class RevitAddonsTests {
        [TestMethod()]
        public void GetRevitAddonsFolder_UserLevel_AllVersions_Test() {
            // Test that user-level path is unchanged for all versions
            var path2025 = pyRevitLabs.TargetApps.Revit.RevitAddons.GetRevitAddonsFolder(2025, allUsers: false);
            var path2027 = pyRevitLabs.TargetApps.Revit.RevitAddons.GetRevitAddonsFolder(2027, allUsers: false);
            var path2030 = pyRevitLabs.TargetApps.Revit.RevitAddons.GetRevitAddonsFolder(2030, allUsers: false);

            // All should use AppData
            var expectedBasePath = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
            
            Assert.IsTrue(path2025.StartsWith(expectedBasePath, StringComparison.OrdinalIgnoreCase), 
                $"User-level path for 2025 should start with {expectedBasePath}");
            Assert.IsTrue(path2027.StartsWith(expectedBasePath, StringComparison.OrdinalIgnoreCase), 
                $"User-level path for 2027 should start with {expectedBasePath}");
            Assert.IsTrue(path2030.StartsWith(expectedBasePath, StringComparison.OrdinalIgnoreCase), 
                $"User-level path for 2030 should start with {expectedBasePath}");

            // Verify path structure
            Assert.IsTrue(path2025.Contains(@"Autodesk\Revit\Addins\2025") || 
                          path2025.Contains("Autodesk/Revit/Addins/2025"),
                $"Path 2025 should contain correct structure: {path2025}");
            Assert.IsTrue(path2027.Contains(@"Autodesk\Revit\Addins\2027") || 
                          path2027.Contains("Autodesk/Revit/Addins/2027"),
                $"Path 2027 should contain correct structure: {path2027}");
        }

        [TestMethod()]
        public void GetRevitAddonsFolder_AllUsers_Pre2027_Test() {
            // Test that all-users path uses ProgramData for Revit ≤2026
            var path2024 = pyRevitLabs.TargetApps.Revit.RevitAddons.GetRevitAddonsFolder(2024, allUsers: true);
            var path2025 = pyRevitLabs.TargetApps.Revit.RevitAddons.GetRevitAddonsFolder(2025, allUsers: true);
            var path2026 = pyRevitLabs.TargetApps.Revit.RevitAddons.GetRevitAddonsFolder(2026, allUsers: true);

            // All should use CommonApplicationData (ProgramData)
            var expectedBasePath = Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData);
            
            Assert.IsTrue(path2024.StartsWith(expectedBasePath), 
                $"All-users path for 2024 should start with {expectedBasePath}");
            Assert.IsTrue(path2025.StartsWith(expectedBasePath), 
                $"All-users path for 2025 should start with {expectedBasePath}");
            Assert.IsTrue(path2026.StartsWith(expectedBasePath), 
                $"All-users path for 2026 should start with {expectedBasePath}");

            // Verify path structure
            Assert.IsTrue(path2026.Contains(@"Autodesk\Revit\Addins\2026") || 
                          path2026.Contains("Autodesk/Revit/Addins/2026"),
                $"Path 2026 should contain correct structure: {path2026}");
        }

        [TestMethod()]
        public void GetRevitAddonsFolder_AllUsers_Post2027_Test() {
            var path2027 = pyRevitLabs.TargetApps.Revit.RevitAddons.GetRevitAddonsFolder(2027, allUsers: true);
            var path2028 = pyRevitLabs.TargetApps.Revit.RevitAddons.GetRevitAddonsFolder(2028, allUsers: true);
            var path2030 = pyRevitLabs.TargetApps.Revit.RevitAddons.GetRevitAddonsFolder(2030, allUsers: true);

            // Verify path structure - should use shared Revit\Addins\<year> under Program Files
            var programFiles = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);

            Assert.IsTrue(path2027.StartsWith(programFiles, StringComparison.OrdinalIgnoreCase),
                $"All-users path for 2027 should be under Program Files: {path2027}");
            Assert.IsTrue(path2027.Contains(@"Autodesk\Revit\Addins\2027") ||
                          path2027.Contains("Autodesk/Revit/Addins/2027"),
                $"Path 2027 should use shared Revit\\Addins structure: {path2027}");
            Assert.IsTrue(path2028.StartsWith(programFiles, StringComparison.OrdinalIgnoreCase),
                $"All-users path for 2028 should be under Program Files: {path2028}");
            Assert.IsTrue(path2028.Contains(@"Autodesk\Revit\Addins\2028") ||
                          path2028.Contains("Autodesk/Revit/Addins/2028"),
                $"Path 2028 should use shared Revit\\Addins structure: {path2028}");
            Assert.IsTrue(path2030.StartsWith(programFiles, StringComparison.OrdinalIgnoreCase),
                $"All-users path for 2030 should be under Program Files: {path2030}");
            Assert.IsTrue(path2030.Contains(@"Autodesk\Revit\Addins\2030") ||
                          path2030.Contains("Autodesk/Revit/Addins/2030"),
                $"Path 2030 should use shared Revit\\Addins structure: {path2030}");
        }

        [TestMethod()]
        public void GetRevitAddonsFolder_AllUsers_2027Boundary_Test() {
            var path2026 = pyRevitLabs.TargetApps.Revit.RevitAddons.GetRevitAddonsFolder(2026, allUsers: true);
            var path2027 = pyRevitLabs.TargetApps.Revit.RevitAddons.GetRevitAddonsFolder(2027, allUsers: true);

            var programData = Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData);
            var programFiles = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);

            // 2026 should use the legacy ProgramData structure
            Assert.IsTrue(path2026.StartsWith(programData, StringComparison.OrdinalIgnoreCase),
                $"2026 should use ProgramData: {path2026}");

            // 2027 should use Program Files shared structure
            Assert.IsTrue(path2027.StartsWith(programFiles, StringComparison.OrdinalIgnoreCase),
                $"2027 should use Program Files: {path2027}");
            Assert.IsTrue(path2027.EndsWith(@"Addins\2027") || path2027.EndsWith("Addins/2027"),
                $"2027 should end with Addins\\2027: {path2027}");
        }

        [TestMethod()]
        public void GetRevitAddonsFilePath_Consistency_Test() {
            // Test that GetRevitAddonsFilePath uses GetRevitAddonsFolder correctly
            // This is an integration test to ensure the methods work together
            
            // For user-level
            var userFilePath2027 = pyRevitLabs.TargetApps.Revit.RevitAddons.GetRevitAddonsFilePath(2027, "TestAddin", allusers: false);
            var userFolder2027 = pyRevitLabs.TargetApps.Revit.RevitAddons.GetRevitAddonsFolder(2027, allUsers: false);
            Assert.IsTrue(userFilePath2027.StartsWith(userFolder2027, StringComparison.OrdinalIgnoreCase),
                $"User file path should be within user folder: {userFilePath2027} vs {userFolder2027}");

            // Verify file path ends with .addin extension
            Assert.IsTrue(userFilePath2027.EndsWith("TestAddin.addin", StringComparison.OrdinalIgnoreCase),
                $"File path should end with TestAddin.addin: {userFilePath2027}");
        }

        [TestMethod()]
        public void GetRevitAddonsFilePath_ExplicitAllUsers_Test() {
            // With allusers: false, path must contain user AppData (no elevation override)
            var userPath = pyRevitLabs.TargetApps.Revit.RevitAddons.GetRevitAddonsFilePath(2027, "TestAddin", allusers: false);
            Assert.IsTrue(userPath.IndexOf("AppData", StringComparison.OrdinalIgnoreCase) >= 0 ||
                         userPath.IndexOf("Roaming", StringComparison.OrdinalIgnoreCase) >= 0,
                "allusers: false should return path under user AppData/Roaming: " + userPath);

            // With allusers: true, Revit 2026 and earlier use CommonApplicationData
            var allUsersPath2026 = pyRevitLabs.TargetApps.Revit.RevitAddons.GetRevitAddonsFilePath(2026, "TestAddin", allusers: true);
            var commonData = Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData);
            Assert.IsTrue(allUsersPath2026.StartsWith(commonData, StringComparison.OrdinalIgnoreCase),
                "allusers: true for 2026 should be under CommonApplicationData: " + allUsersPath2026);

            // With allusers: true, Revit 2027+ uses %ProgramFiles%\Autodesk\Revit\Addins\<year>
            var allUsersPath2027 = pyRevitLabs.TargetApps.Revit.RevitAddons.GetRevitAddonsFilePath(2027, "TestAddin", allusers: true);
            Assert.IsTrue(allUsersPath2027.EndsWith("TestAddin.addin", StringComparison.OrdinalIgnoreCase),
                "Path should end with TestAddin.addin: " + allUsersPath2027);
            Assert.IsTrue(allUsersPath2027.Contains("Addins") && allUsersPath2027.Contains("2027"),
                "Path should contain Addins and year 2027: " + allUsersPath2027);
        }
    }
}
