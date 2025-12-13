using pyRevitExtensionParser;
using pyRevitExtensionParserTest.TestHelpers;
using System.IO;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class LocalizationTests : TempFileTestBase
    {
        [Test]
        public void TestLocalizedButtonBundle()
        {
            // Create test extension on-the-fly instead of using repo files
            var extensionPath = TestExtensionFactory.CreateComprehensiveTestExtension(TestTempDir);
            
            // Parse extensions
            var extensions = ParseInstalledExtensions(new[] { extensionPath });
            
            TestContext.Out.WriteLine("=== Testing LocalizedButton Localized Bundle ===");
            
            foreach (var extension in extensions)
            {
                if (extension == null) continue;
                
                var localizedButton = FindComponentRecursively(extension, "LocalizedButton");
                if (localizedButton != null)
                {
                    TestContext.Out.WriteLine($"Button: {localizedButton.DisplayName}");
                    TestContext.Out.WriteLine($"Name: {localizedButton.Name}");
                    TestContext.Out.WriteLine($"Title: {localizedButton.Title}");
                    TestContext.Out.WriteLine($"Tooltip: {localizedButton.Tooltip}");
                    TestContext.Out.WriteLine($"Author: {localizedButton.Author}");
                    TestContext.Out.WriteLine($"Bundle File: {localizedButton.BundleFile}");
                    
                    // Verify the component was found and has a bundle
                    Assert.IsNotNull(localizedButton.BundleFile);
                    Assert.IsTrue(File.Exists(localizedButton.BundleFile));
                    Assert.AreEqual(CommandComponentType.PushButton, localizedButton.Type);
                    
                    // Verify localized content (should default to en_us)
                    Assert.AreEqual("TEST TITLE 1 EN", localizedButton.Title);
                    Assert.AreEqual("TEST TOOLTIP EN", localizedButton.Tooltip);
                    Assert.AreEqual("Roman Golev", localizedButton.Author);
                    
                    // Test localization features
                    Assert.IsNotNull(localizedButton.LocalizedTitles);
                    Assert.IsNotNull(localizedButton.LocalizedTooltips);
                    Assert.IsTrue(localizedButton.HasLocalizedContent);
                    
                    // Test different locale access
                    Assert.AreEqual("TEST TITLE 1 FR", localizedButton.GetLocalizedTitle("fr_fr"));
                    Assert.AreEqual("TEST TITLE 1 DE", localizedButton.GetLocalizedTitle("de_de"));
                    Assert.AreEqual("TEST TOOLTIP FR", localizedButton.GetLocalizedTooltip("fr_fr"));
                    Assert.AreEqual("TEST TOOLTIP DE", localizedButton.GetLocalizedTooltip("de_de"));
                    
                    // Test fallback to en_us for non-existent locale
                    Assert.AreEqual("TEST TITLE 1 EN", localizedButton.GetLocalizedTitle("es_es"));
                    Assert.AreEqual("TEST TOOLTIP EN", localizedButton.GetLocalizedTooltip("es_es"));
                    
                    // Test available locales
                    var availableLocales = localizedButton.AvailableLocales.ToList();
                    Assert.Contains("en_us", availableLocales);
                    Assert.Contains("fr_fr", availableLocales);
                    Assert.Contains("de_de", availableLocales);
                    
                    TestContext.Out.WriteLine($"Available locales: {string.Join(", ", availableLocales)}");
                    
                    // Test completed successfully
                    return;
                }
            }
            
            Assert.Fail("LocalizedButton not found");
        }
        
        [Test]
        public void TestBundleLocalizationFallback()
        {
            // Test with a temporary bundle to verify locale fallback behavior
            // Use TestExtensionBuilder to reduce boilerplate
            var extensionPath = TestExtensionBuilder.CreateMinimalExtension(
                TestTempDir, "TestLocalization", "TestTab", "TestPanel", "TestButton", "print('test')");
            
            var buttonDir = Path.Combine(extensionPath, "TestTab.tab", "TestPanel.panel", "TestButton.pushbutton");
            
            var bundleContent = @"title:
  fr_fr: French Title
  de_de: German Title
  es_es: Spanish Title
tooltip:
  fr_fr: French Tooltip
  de_de: German Tooltip
author: Test Author";
            
            TestExtensionBuilder.WriteBundleYaml(buttonDir, bundleContent);
            
            // Parse the extension
            var extensions = ParseInstalledExtensions(new[] { extensionPath });
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
        
        [Test]
        public void TestAdvancedLocalizationFeatures()
        {
            // Test with a comprehensive multilingual bundle using TestExtensionBuilder
            var extensionPath = TestExtensionBuilder.CreateMinimalExtension(
                TestTempDir, "TestAdvancedLocalization", "TestTab", "TestPanel", "TestMultilingualButton", "print('multilingual test')");
            
            var buttonDir = Path.Combine(extensionPath, "TestTab.tab", "TestPanel.panel", "TestMultilingualButton.pushbutton");
            
            var bundleContent = @"title:
  en_us: English Title
  fr_fr: Titre Francais
  de_de: Deutscher Titel
  es_es: Titulo Espanol
  it_it: Titolo Italiano
tooltips:
  en_us: English tooltip description
  fr_fr: Description de info-bulle francaise
  de_de: Deutsche Tooltip-Beschreibung
  es_es: Descripcion del tooltip en espanol
author: Multilingual Test Author";
            
            TestExtensionBuilder.WriteBundleYaml(buttonDir, bundleContent);
            
            // Parse the extension
            var extensions = ParseInstalledExtensions(new[] { extensionPath });
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
                ["fr_fr"] = "Titre Francais", 
                ["de_de"] = "Deutscher Titel",
                ["es_es"] = "Titulo Espanol",
                ["it_it"] = "Titolo Italiano"
            };
            
            var expectedTooltips = new Dictionary<string, string>
            {
                ["en_us"] = "English tooltip description",
                ["fr_fr"] = "Description de info-bulle francaise",
                ["de_de"] = "Deutsche Tooltip-Beschreibung", 
                ["es_es"] = "Descripcion del tooltip en espanol"
            };
            
            foreach (var kvp in expectedTitles)
            {
                var actualTitle = testButton.GetLocalizedTitle(kvp.Key);
                Assert.AreEqual(kvp.Value, actualTitle, $"Title mismatch for locale {kvp.Key}");
                TestContext.Out.WriteLine($"[OK] {kvp.Key} title: {actualTitle}");
            }
            
            foreach (var kvp in expectedTooltips)
            {
                var actualTooltip = testButton.GetLocalizedTooltip(kvp.Key);
                Assert.AreEqual(kvp.Value, actualTooltip, $"Tooltip mismatch for locale {kvp.Key}");
                TestContext.Out.WriteLine($"[OK] {kvp.Key} tooltip: {actualTooltip}");
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
        
        [Test]
        public void TestConfigurableDefaultLocale()
        {
            // Test with a bundle that doesn't have en_us using TestExtensionBuilder
            var extensionPath = TestExtensionBuilder.CreateMinimalExtension(
                TestTempDir, "TestDefaultLocale", "TestTab", "TestPanel", "TestLocaleButton", "print('locale test')");
            
            var buttonDir = Path.Combine(extensionPath, "TestTab.tab", "TestPanel.panel", "TestLocaleButton.pushbutton");
            
            var bundleContent = @"title:
  fr_fr: Titre Francais Only
  de_de: Nur Deutscher Titel
tooltip:
  fr_fr: Info-bulle francaise
  de_de: Deutsche Tooltip
author: Locale Test Author";
            
            TestExtensionBuilder.WriteBundleYaml(buttonDir, bundleContent);
            
            // Test with default locale (en_us) - should fallback to first available
            var originalDefaultLocale = ExtensionParser.DefaultLocale;
            
            try
            {
                ExtensionParser.DefaultLocale = "en_us";
                
                var extensions = ParseInstalledExtensions(new[] { extensionPath });
                var extension = extensions.FirstOrDefault();
                var testButton = FindComponentRecursively(extension, "TestLocaleButton");
                
                Assert.IsNotNull(testButton);
                
                // Should get first available since en_us is not available
                var titleWithEnUs = testButton.GetLocalizedTitle();
                Assert.IsTrue(titleWithEnUs == "Titre Francais Only" || titleWithEnUs == "Nur Deutscher Titel");
                
                TestContext.Out.WriteLine($"Default locale (en_us) fallback title: {titleWithEnUs}");
                
                // Change default locale to fr_fr
                ExtensionParser.DefaultLocale = "fr_fr";
                
                // Re-parse to test with new default locale
                extensions = ParseInstalledExtensions(new[] { extensionPath });
                extension = extensions.FirstOrDefault();
                testButton = FindComponentRecursively(extension, "TestLocaleButton");
                
                Assert.IsNotNull(testButton);
                
                // Should now default to French
                Assert.AreEqual("Titre Francais Only", testButton.Title);
                Assert.AreEqual("Info-bulle francaise", testButton.Tooltip);
                Assert.AreEqual("Titre Francais Only", testButton.GetLocalizedTitle());
                Assert.AreEqual("Info-bulle francaise", testButton.GetLocalizedTooltip());
                
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