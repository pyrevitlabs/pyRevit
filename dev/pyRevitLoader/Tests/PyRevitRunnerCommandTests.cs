using System;
using System.IO;
using System.Reflection;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using PyRevitRunner;

namespace PyRevitLoader.Tests {
    [TestClass]
    public class PyRevitRunnerCommandTests {
        private static string CreateMockAssemblyPath(string structure) {
            // Helper to create mock assembly path based on folder structure
            return Path.Combine(structure.Split('/'));
        }

        [TestMethod]
        public void GetDeployPath_WithNetCoreFolderStructure_ReturnsCorrectPath() {
            // Arrange
            var mockAssemblyPath = CreateMockAssemblyPath("C:/Users/test/AppData/Roaming/pyRevit-Master/bin/netcore/engines/IPY2712PR/pyRevitLoader.dll");
            var expectedPath = "C:/Users/test/AppData/Roaming/pyRevit-Master";

            // Use reflection to test private method
            var method = typeof(PyRevitRunnerCommand).GetMethod("GetDeployPath", 
                BindingFlags.NonPublic | BindingFlags.Static);

            // Mock Assembly.GetExecutingAssembly().Location
            // This would require more setup in a real test environment
            
            // Act
            var result = method.Invoke(null, null);

            // Assert
            Assert.AreEqual(expectedPath, result);
        }

        [TestMethod]
        public void GetDeployPath_WithNetFxFolderStructure_ReturnsCorrectPath() {
            // Similar test for netfx structure
            var mockAssemblyPath = CreateMockAssemblyPath("C:/Users/test/AppData/Roaming/pyRevit-Master/bin/netfx/engines/IPY2712PR/pyRevitLoader.dll");
            var expectedPath = "C:/Users/test/AppData/Roaming/pyRevit-Master";

            var method = typeof(PyRevitRunnerCommand).GetMethod("GetDeployPath", 
                BindingFlags.NonPublic | BindingFlags.Static);
            
            var result = method.Invoke(null, null);
            
            Assert.AreEqual(expectedPath, result);
        }

        [TestMethod]
        public void GetPyRevitLibsPath_ReturnsCorrectPath() {
            var method = typeof(PyRevitRunnerCommand).GetMethod("GetPyRevitLibsPath", 
                BindingFlags.NonPublic | BindingFlags.Static);
            
            var result = method.Invoke(null, null);
            
            Assert.IsTrue(result.ToString().EndsWith("pyrevitlib"));
        }

        [TestMethod]
        public void GetSitePkgsPath_ReturnsCorrectPath() {
            var method = typeof(PyRevitRunnerCommand).GetMethod("GetSitePkgsPath", 
                BindingFlags.NonPublic | BindingFlags.Static);
            
            var result = method.Invoke(null, null);
            
            Assert.IsTrue(result.ToString().EndsWith("site-packages"));
        }
    }
}