using System.Collections.Generic;
using System.Linq;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.SessionManager
{
    public class ExtensionManagerService
    {
        public IEnumerable<ParsedExtension> GetInstalledExtensions()
        {
            var installedExtensions = ExtensionParser.ParseInstalledExtensions();

            foreach (var parsedExtension in installedExtensions)
            {
                // Populate tooltip, UniqueId, etc., if needed (e.g., add validation or enrichment)
                FlattenAndEnrich(parsedExtension.Children);
                yield return parsedExtension;
            }
        }

        private void FlattenAndEnrich(IEnumerable<ParsedComponent> components)
        {
            foreach (var component in components)
            {
                if (!string.IsNullOrEmpty(component.ScriptPath))
                    yield return component;

        private void FlattenAndEnrich(IEnumerable<ParsedComponent> components)
        {
            foreach (var component in components)
            {
                // Custom logic if needed, e.g., enrich tooltip or validate UniqueId
                if (component.Children != null)
                    FlattenAndEnrich(component.Children);
            }
        }
    }
}