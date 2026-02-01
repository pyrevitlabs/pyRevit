using pyRevitExtensionParser;
using System;
using System.IO;

namespace pyRevitExtensionParserTest
{
    class Program
    {
        static void Main(string[] args)
        {
            Console.WriteLine("Testing current SearchButton parsing...");
            
            var bundlePath = @"c:\dev\romangolev\pyRevit\extensions\pyRevitCore.extension\pyRevit.tab\pyRevit.panel\tools.stack\Search.pushbutton\bundle.yaml";
            
            if (!File.Exists(bundlePath))
            {
                Console.WriteLine($"Bundle file not found: {bundlePath}");
                return;
            }
            
            Console.WriteLine($"Parsing bundle: {bundlePath}");
            
            // Test the BundleParser directly
            var result = BundleParser.BundleYamlParser.Parse(bundlePath);
            
            Console.WriteLine("\n=== BundleParser Results ===");
            foreach (var title in result.Titles)
            {
                Console.WriteLine($"[{title.Key}]: '{title.Value}' (Length: {title.Value.Length})");
                
                // Check for any quotes in the value
                if (title.Value.Contains("\"") || title.Value.Contains("'"))
                {
                    Console.WriteLine($"  ❌ ISSUE: Still contains quotes!");
                }
                else
                {
                    Console.WriteLine($"  ✅ Clean (no quotes)");
                }
            }
            
            Console.WriteLine("\n=== Specific Test Cases ===");
            Console.WriteLine($"en_us: '{result.Titles.GetValueOrDefault("en_us", "NOT_FOUND")}'");
            Console.WriteLine($"es_es: '{result.Titles.GetValueOrDefault("es_es", "NOT_FOUND")}'");
            Console.WriteLine($"fa: '{result.Titles.GetValueOrDefault("fa", "NOT_FOUND")}'");
            
            Console.WriteLine("\nTest completed. Press any key to exit...");
            Console.ReadKey();
        }
    }
}