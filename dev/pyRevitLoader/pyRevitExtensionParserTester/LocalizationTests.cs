using pyRevitExtensionParser;
using System.IO;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class LocalizationTests
    {
        [Test]
        public void TestPanelOneButton1LocalizedBundle()
        {
            var testBundlePath = Path.Combine(TestContext.CurrentContext.TestDirectory, "..", "..", "..", "..", "..", "..", "extensions", "pyRevitDevTools.extension");
            
            // Parse extensions
            var extensions = ParseInstalledExtensions(new[] { testBundlePath });
            
            TestContext.Out.WriteLine("=== Testing PanelOneButton1 Localized Bundle ===");
            
            foreach (var extension in extensions)
            {
                if (extension == null) continue;
                
                var panelOneButton1 = FindComponentRecursively(extension, "PanelOneButton1");
                if (panelOneButton1 != null)
                {
                    TestContext.Out.WriteLine($"Button: {panelOneButton1.DisplayName}");
                    TestContext.Out.WriteLine($"Name: {panelOneButton1.Name}");
                    TestContext.Out.WriteLine($"Title: {panelOneButton1.Title}");
                    TestContext.Out.WriteLine($"Tooltip: {panelOneButton1.Tooltip}");
                    TestContext.Out.WriteLine($"Author: {panelOneButton1.Author}");
                    TestContext.Out.WriteLine($"Bundle File: {panelOneButton1.BundleFile}");
                    
                    // Verify the component was found and has a bundle
                    Assert.IsNotNull(panelOneButton1.BundleFile);
                    Assert.IsTrue(File.Exists(panelOneButton1.BundleFile));
                    Assert.AreEqual(CommandComponentType.PushButton, panelOneButton1.Type);
                    
                    // Verify localized content (should default to en_us)
                    Assert.AreEqual("TEST TITLE 1 EN", panelOneButton1.Title);
                    Assert.AreEqual("TEST TOOLTIP EN", panelOneButton1.Tooltip);
                    Assert.AreEqual("Roman Golev", panelOneButton1.Author);
                    
                    // Test localization features
                    Assert.IsNotNull(panelOneButton1.LocalizedTitles);
                    Assert.IsNotNull(panelOneButton1.LocalizedTooltips);
                    Assert.IsTrue(panelOneButton1.HasLocalizedContent);
                    
                    // Test different locale access
                    Assert.AreEqual("TEST TITLE 1 FR", panelOneButton1.GetLocalizedTitle("fr_fr"));
                    Assert.AreEqual("TEST TITLE 1 DE", panelOneButton1.GetLocalizedTitle("de_de"));
                    Assert.AreEqual("TEST TOOLTIP FR", panelOneButton1.GetLocalizedTooltip("fr_fr"));
                    Assert.AreEqual("TEST TOOLTIP DE", panelOneButton1.GetLocalizedTooltip("de_de"));
                    
                    // Test fallback to en_us for non-existent locale
                    Assert.AreEqual("TEST TITLE 1 EN", panelOneButton1.GetLocalizedTitle("es_es"));
                    Assert.AreEqual("TEST TOOLTIP EN", panelOneButton1.GetLocalizedTooltip("es_es"));
                    
                    // Test available locales
                    var availableLocales = panelOneButton1.AvailableLocales.ToList();
                    Assert.Contains("en_us", availableLocales);
                    Assert.Contains("fr_fr", availableLocales);
                    Assert.Contains("de_de", availableLocales);
                    
                    TestContext.Out.WriteLine($"Available locales: {string.Join(", ", availableLocales)}");
                    
                    // Test completed successfully
                    return;
                }
            }
            
            Assert.Fail("PanelOneButton1 not found");
        }
        
        [Test]
        public void TestBundleLocalizationFallback()
        {
            // Test with a temporary bundle to verify locale fallback behavior
            var tempDir = Path.Combine(Path.GetTempPath(), "TestLocalization.extension");
            var tabDir = Path.Combine(tempDir, "TestTab.tab");
            var panelDir = Path.Combine(tabDir, "TestPanel.panel");
            var buttonDir = Path.Combine(panelDir, "TestButton.pushbutton");
            
            try
            {
                Directory.CreateDirectory(buttonDir);
                
                var scriptPath = Path.Combine(buttonDir, "script.py");
                File.WriteAllText(scriptPath, "print('test')");
                
                var bundlePath = Path.Combine(buttonDir, "bundle.yaml");
                var bundleContent = @"title:
  fr_fr: French Title
  de_de: German Title
  es_es: Spanish Title
tooltip:
  fr_fr: French Tooltip
  de_de: German Tooltip
author: Test Author";
                
                File.WriteAllText(bundlePath, bundleContent);
                
                // Parse the extension
                var extensions = ParseInstalledExtensions(new[] { tempDir });
                var extension = extensions.FirstOrDefault();
                
                Assert.IsNotNull(extension, "Extension should be parsed");
                
                var testButton = FindComponentRecursively(extension, "TestButton");
                Assert.IsNotNull(testButton, "TestButton should be found");
                
                // Since there's no en_us, should fallback to first available
                Assert.IsNotNull(testButton.Title, "Title should not be null");
                Assert.IsNotNull(testButton.Tooltip, "Tooltip should not be null");
                Assert.That(testButton.Author, Is.EqualTo("Test Author"));
                
                TestContext.Out.WriteLine($"Fallback Title: {testButton.Title}");
                TestContext.Out.WriteLine($"Fallback Tooltip: {testButton.Tooltip}");
                
                // Should get one of the available locales (first one in order)
                Assert.IsTrue(testButton.Title == "French Title" || 
                             testButton.Title == "German Title" || 
                             testButton.Title == "Spanish Title");
            }
            finally
            {
                if (Directory.Exists(tempDir))
                    Directory.Delete(tempDir, true);
            }
        }
        
        [Test]
        public void TestAdvancedLocalizationFeatures()
        {
            // Test with a comprehensive multilingual bundle
            var tempDir = Path.Combine(Path.GetTempPath(), "TestAdvancedLocalization.extension");
            var tabDir = Path.Combine(tempDir, "TestTab.tab");
            var panelDir = Path.Combine(tabDir, "TestPanel.panel");
            var buttonDir = Path.Combine(panelDir, "TestMultilingualButton.pushbutton");
            
            try
            {
                Directory.CreateDirectory(buttonDir);
                
                var scriptPath = Path.Combine(buttonDir, "script.py");
                File.WriteAllText(scriptPath, "print('multilingual test')");
                
                var bundlePath = Path.Combine(buttonDir, "bundle.yaml");
                var bundleContent = @"title:
  en_us: English Title
  fr_fr: Titre Fran�ais
  de_de: Deutscher Titel
  es_es: T�tulo Espa�ol
  it_it: Titolo Italiano
tooltips:
  en_us: English tooltip description
  fr_fr: Description de l'info-bulle fran�aise
  de_de: Deutsche Tooltip-Beschreibung
  es_es: Descripci�n del tooltip en espa�ol
author: Multilingual Test Author";
                
                File.WriteAllText(bundlePath, bundleContent);
                
                // Parse the extension
                var extensions = ParseInstalledExtensions(new[] { tempDir });
                var extension = extensions.FirstOrDefault();
                
                Assert.IsNotNull(extension, "Extension should be parsed");
                
                var testButton = FindComponentRecursively(extension, "TestMultilingualButton");
                Assert.IsNotNull(testButton, "TestMultilingualButton should be found");
                
                TestContext.Out.WriteLine("=== Testing Advanced Localization Features ===");
                
                // Test all localization features
                Assert.IsTrue(testButton.HasLocalizedContent);
                Assert.AreEqual(5, testButton.LocalizedTitles.Count);
                Assert.AreEqual(4, testButton.LocalizedTooltips.Count);
                
                // Test each locale
                var expectedTitles = new Dictionary<string, string>
                {
                    ["en_us"] = "English Title",
                    ["fr_fr"] = "Titre Fran�ais", 
                    ["de_de"] = "Deutscher Titel",
                    ["es_es"] = "T�tulo Espa�ol",
                    ["it_it"] = "Titolo Italiano"
                };
                
                var expectedTooltips = new Dictionary<string, string>
                {
                    ["en_us"] = "English tooltip description",
                    ["fr_fr"] = "Description de l'info-bulle fran�aise",
                    ["de_de"] = "Deutsche Tooltip-Beschreibung", 
                    ["es_es"] = "Descripci�n del tooltip en espa�ol"
                };
                
                foreach (var kvp in expectedTitles)
                {
                    var actualTitle = testButton.GetLocalizedTitle(kvp.Key);
                    Assert.AreEqual(kvp.Value, actualTitle, $"Title mismatch for locale {kvp.Key}");
                    TestContext.Out.WriteLine($"? {kvp.Key} title: {actualTitle}");
                }
                
                foreach (var kvp in expectedTooltips)
                {
                    var actualTooltip = testButton.GetLocalizedTooltip(kvp.Key);
                    Assert.AreEqual(kvp.Value, actualTooltip, $"Tooltip mismatch for locale {kvp.Key}");
                    TestContext.Out.WriteLine($"? {kvp.Key} tooltip: {actualTooltip}");
                }
                
                // Test fallback for it_it (has title but no tooltip)
                Assert.AreEqual("Titolo Italiano", testButton.GetLocalizedTitle("it_it"));
                Assert.AreEqual("English tooltip description", testButton.GetLocalizedTooltip("it_it")); // Should fallback to en_us
                
                // Test fallback for unknown locale
                Assert.AreEqual("English Title", testButton.GetLocalizedTitle("zh_cn")); // Should fallback to en_us
                Assert.AreEqual("English tooltip description", testButton.GetLocalizedTooltip("zh_cn")); // Should fallback to en_us
                
                // Test available locales
                var availableLocales = testButton.AvailableLocales.ToList();
                Assert.Contains("en_us", availableLocales);
                Assert.Contains("fr_fr", availableLocales);
                Assert.Contains("de_de", availableLocales);
                Assert.Contains("es_es", availableLocales);
                Assert.Contains("it_it", availableLocales);
                
                TestContext.Out.WriteLine($"Available locales: {string.Join(", ", availableLocales)}");
                TestContext.Out.WriteLine("Advanced localization test completed successfully!");
            }
            finally
            {
                if (Directory.Exists(tempDir))
                    Directory.Delete(tempDir, true);
            }
        }
        
        [Test]
        public void TestConfigurableDefaultLocale()
        {
            // Test with a bundle that doesn't have en_us
            var tempDir = Path.Combine(Path.GetTempPath(), "TestDefaultLocale.extension");
            var tabDir = Path.Combine(tempDir, "TestTab.tab");
            var panelDir = Path.Combine(tabDir, "TestPanel.panel");
            var buttonDir = Path.Combine(panelDir, "TestLocaleButton.pushbutton");
            
            try
            {
                Directory.CreateDirectory(buttonDir);
                
                var scriptPath = Path.Combine(buttonDir, "script.py");
                File.WriteAllText(scriptPath, "print('locale test')");
                
                var bundlePath = Path.Combine(buttonDir, "bundle.yaml");
                var bundleContent = @"title:
  fr_fr: Titre Fran�ais Only
  de_de: Nur Deutscher Titel
tooltip:
  fr_fr: Info-bulle fran�aise
  de_de: Deutsche Tooltip
author: Locale Test Author";
                
                File.WriteAllText(bundlePath, bundleContent);
                
                // Test with default locale (en_us) - should fallback to first available
                var originalDefaultLocale = ExtensionParser.DefaultLocale;
                
                try
                {
                    ExtensionParser.DefaultLocale = "en_us";
                    
                    var extensions = ParseInstalledExtensions(new[] { tempDir });
                    var extension = extensions.FirstOrDefault();
                    var testButton = FindComponentRecursively(extension, "TestLocaleButton");
                    
                    Assert.IsNotNull(testButton);
                    
                    // Should get first available since en_us is not available
                    var titleWithEnUs = testButton.GetLocalizedTitle();
                    Assert.IsTrue(titleWithEnUs == "Titre Fran�ais Only" || titleWithEnUs == "Nur Deutscher Titel");
                    
                    TestContext.Out.WriteLine($"Default locale (en_us) fallback title: {titleWithEnUs}");
                    
                    // Change default locale to fr_fr
                    ExtensionParser.DefaultLocale = "fr_fr";
                    
                    // Re-parse to test with new default locale
                    extensions = ParseInstalledExtensions(new[] { tempDir });
                    extension = extensions.FirstOrDefault();
                    testButton = FindComponentRecursively(extension, "TestLocaleButton");
                    
                    Assert.IsNotNull(testButton);
                    
                    // Should now default to French
                    Assert.AreEqual("Titre Fran�ais Only", testButton.Title);
                    Assert.AreEqual("Info-bulle fran�aise", testButton.Tooltip);
                    Assert.AreEqual("Titre Fran�ais Only", testButton.GetLocalizedTitle());
                    Assert.AreEqual("Info-bulle fran�aise", testButton.GetLocalizedTooltip());
                    
                    TestContext.Out.WriteLine($"French default locale title: {testButton.Title}");
                    TestContext.Out.WriteLine($"French default locale tooltip: {testButton.Tooltip}");
                    
                    // Test explicit locale still works
                    Assert.AreEqual("Nur Deutscher Titel", testButton.GetLocalizedTitle("de_de"));
                    Assert.AreEqual("Deutsche Tooltip", testButton.GetLocalizedTooltip("de_de"));
                }
                finally
                {
                    // Restore original default locale
                    ExtensionParser.DefaultLocale = originalDefaultLocale;
                }
            }
            finally
            {
                if (Directory.Exists(tempDir))
                    Directory.Delete(tempDir, true);
            }
        }
        
        // Helper method to find components recursively
        private ParsedComponent? FindComponentRecursively(ParsedComponent? parent, string componentName)
        {
            if (parent == null || string.IsNullOrEmpty(componentName))
                return null;
                
            if (parent.Name == componentName)
                return parent;

            if (parent.Children != null)
            {
                foreach (var child in parent.Children)
                {
                    var found = FindComponentRecursively(child, componentName);
                    if (found != null)
                        return found;
                }
            }

            return null;
        }
    }
}