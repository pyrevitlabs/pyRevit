using System.Xml.Linq;

namespace Build.Helpers;

public static class XmlHelper
{
    public static void SetMsiCopyright(string propsFile, string copyright)
    {
        UpdateElement(propsFile, "http://schemas.microsoft.com/developer/msbuild/2003", "Copyright", copyright);
    }

    public static void SetMsiVersion(string propsFile, string version)
    {
        UpdateElement(propsFile, "http://schemas.microsoft.com/developer/msbuild/2003", "Version", version);
    }

    public static void SetMsiProductCodes(string propsFile, string productCode, string upgradeCode)
    {
        UpdateElement(propsFile, "http://schemas.microsoft.com/developer/msbuild/2003", "ProductIdCode", productCode);
        UpdateElement(propsFile, "http://schemas.microsoft.com/developer/msbuild/2003", "ProductUpgradeCode", upgradeCode);
    }

    public static void SetChocoCopyright(string nuspecFile, string copyright)
    {
        UpdateElement(nuspecFile, "http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd", "copyright", copyright);
    }

    public static void SetChocoVersion(string nuspecFile, string installVersion, string releaseNotesUrl)
    {
        UpdateElement(nuspecFile, "http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd", "version", installVersion);
        UpdateElement(nuspecFile, "http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd", "releaseNotes", releaseNotesUrl);
    }

    private static void UpdateElement(string filePath, string namespaceUri, string localName, string value)
    {
        var document = XDocument.Load(filePath);
        var element = document
            .Descendants(XName.Get(localName, namespaceUri))
            .FirstOrDefault();

        if (element is null)
        {
            throw new InvalidOperationException($"Element '{localName}' not found in {filePath}");
        }

        element.Value = value;
        document.Save(filePath);
    }
}
