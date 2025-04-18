using System.Collections.Generic;
using System.Linq;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.SessionManager
{
    public class ExtensionManagerService
    {
        public IEnumerable<WrappedExtension> GetInstalledExtensions()
        {
            var installedExtensions = ExtensionParser.ParseInstalledExtensions();
            foreach (var parsedExtension in installedExtensions)
            {
                var pushbuttonCommands = CollectCommandComponents(parsedExtension.Children)
                    .Select(ConvertComponent)
                    .ToList();

                yield return new WrappedExtension(
                    name: parsedExtension.Name,
                    path: parsedExtension.Directory,
                    commands: pushbuttonCommands,
                    children: parsedExtension.Children.Select(ConvertComponent).ToList(),
                    metadata: parsedExtension.Metadata
                );
            }
        }
        private IEnumerable<ParsedComponent> CollectCommandComponents(IEnumerable<ParsedComponent> components)
        {
            foreach (var component in components)
            {
                if (!string.IsNullOrEmpty(component.ScriptPath))
                    yield return component;

                if (component.Children != null)
                {
                    foreach (var child in CollectCommandComponents(component.Children))
                        yield return child;
                }
            }
        }
        private FileCommandComponent ConvertComponent(ParsedComponent parsed)
        {
            return new FileCommandComponent
            {
                Name = parsed.Name,
                ScriptPath = parsed.ScriptPath,
                Tooltip = parsed.Tooltip,
                UniqueId = parsed.UniqueId,
                ExtensionName = parsed.UniqueId.Split('.')[0],
                Type = parsed.Type,
                Children = parsed.Children?.Select(ConvertComponent).Cast<object>().ToList() ?? new List<object>()
            };
        }
    }
}