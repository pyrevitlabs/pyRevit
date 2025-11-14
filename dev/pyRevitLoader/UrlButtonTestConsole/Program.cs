using System;
using System.Linq;
using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;

// Simple console app to test URL button parsing
var devToolsPath = @"C:\dev\romangolev\pyRevit\extensions\pyRevitDevTools.extension";

Console.WriteLine("Testing URL Button Parsing...\n");

var extensions = ParseInstalledExtensions(new[] { devToolsPath });
var devToolsExt = extensions.FirstOrDefault();

if (devToolsExt == null)
{
    Console.WriteLine("ERROR: Could not parse extension");
    return 1;
}

Console.WriteLine($"Extension: {devToolsExt.Name}");

// Find URL button
ParsedComponent FindComponent(ParsedComponent root, string name)
{
    if (root.Name != null && root.Name.Equals(name, StringComparison.OrdinalIgnoreCase))
        return root;
    
    if (root.Children != null)
    {
        foreach (var child in root.Children)
        {
            var found = FindComponent(child, name);
            if (found != null)
                return found;
        }
    }
    return null;
}

ParsedComponent FindInExtension(ParsedExtension ext, string name)
{
    if (ext.Children != null)
    {
        foreach (var child in ext.Children)
        {
            var found = FindComponent(child, name);
            if (found != null)
                return found;
        }
    }
    return null;
}

var apidocsButton = FindInExtension(devToolsExt, "apidocs");

if (apidocsButton == null)
{
    Console.WriteLine("ERROR: Could not find apidocs button");
    return 1;
}

Console.WriteLine($"\nFound URL Button: {apidocsButton.DisplayName}");
Console.WriteLine($"Type: {apidocsButton.Type}");
Console.WriteLine($"Hyperlink: {apidocsButton.Hyperlink}");
Console.WriteLine($"Tooltip: {apidocsButton.Tooltip}");
Console.WriteLine($"Context: {apidocsButton.Context}");

// Verify
bool success = true;
if (apidocsButton.Type != CommandComponentType.UrlButton)
{
    Console.WriteLine("\n❌ FAILED: Button type should be UrlButton");
    success = false;
}

if (string.IsNullOrEmpty(apidocsButton.Hyperlink))
{
    Console.WriteLine("\n❌ FAILED: Hyperlink should not be empty");
    success = false;
}

if (!apidocsButton.Hyperlink.StartsWith("http"))
{
    Console.WriteLine("\n❌ FAILED: Hyperlink should be a valid URL");
    success = false;
}

if (success)
{
    Console.WriteLine("\n✅ SUCCESS: URL button parsing works correctly!");
    return 0;
}
else
{
    return 1;
}
