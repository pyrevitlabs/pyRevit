using System.Collections.Generic;
using System.Linq;
using pyRevitExtensionParser;
using pyRevitAssemblyBuilder.Shared;

namespace pyRevitAssemblyBuilder.SessionManager
{
    public class ExtensionManagerService
    {
        public IEnumerable<IExtension> GetInstalledExtensions()
        {
            foreach (var parsedExtension in ExtensionParser.ParseInstalledExtensions())
            {
                yield return new FileSystemExtension(
                    name: parsedExtension.Name,
                    path: parsedExtension.Directory,
                    commands: parsedExtension.Children.Select(ConvertComponent).ToList(),
                    metadata: parsedExtension.Metadata
                );
            }
        }

        private ICommandComponent ConvertComponent(ParsedComponent parsed)
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

        private class FileSystemExtension : IExtension
        {
            private readonly IEnumerable<ICommandComponent> _commands;

            public FileSystemExtension(string name, string path, IEnumerable<ICommandComponent> commands, ParsedExtensionMetadata metadata)
            {
                Name = name;
                Directory = path;
                _commands = commands;
                Metadata = metadata;
            }

            public string Name { get; }
            public string Directory { get; }
            public ParsedExtensionMetadata Metadata { get; }

            public string GetHash() => Directory.GetHashCode().ToString("X");

            public IEnumerable<ICommandComponent> GetAllCommands() => _commands;

            public IEnumerable<object> Children => _commands;
            public string Type => ".extension";

            object IExtension.Children => Children;
        }

        private class FileCommandComponent : ICommandComponent
        {
            public string Name { get; set; }
            public string ScriptPath { get; set; }
            public string Tooltip { get; set; }
            public string UniqueId { get; set; }
            public string ExtensionName { get; set; }
            public string Type { get; set; }
            public IEnumerable<object> Children { get; set; } = Enumerable.Empty<object>();
        }
    }
}
