using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Microsoft.Extensions.DependencyInjection;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitAssemblyBuilder.Config;
using pyRevitAssemblyBuilder.Shared;

namespace pyRevitAssemblyBuilder.SessionManager
{
    public class ExtensionManagerService : IExtensionManager
    {
        private readonly ICommandTypeGenerator _typeGenerator;
        private readonly IServiceProvider _serviceProvider;
        private readonly List<string> _extensionRoots;

        private static readonly string[] BundleTypes = new[]
        {
            ".tab", ".panel", ".stack", ".splitbutton", ".splitpushbutton", ".pulldown", ".smartbutton", ".pushbutton"
        };

        public ExtensionManagerService(IServiceProvider serviceProvider)
        {
            _serviceProvider = serviceProvider;
            _typeGenerator = _serviceProvider.GetRequiredService<ICommandTypeGenerator>();
            _extensionRoots = GetExtensionRoots();
        }

        public IEnumerable<IExtension> GetInstalledExtensions()
        {
            foreach (var root in _extensionRoots)
            {
                if (!Directory.Exists(root))
                    continue;

                foreach (var dir in Directory.GetDirectories(root))
                {
                    if (!dir.EndsWith(".extension", StringComparison.OrdinalIgnoreCase))
                        continue;

                    var extensionName = Path.GetFileNameWithoutExtension(dir);
                    var metadata = LoadMetadata(dir);
                    var children = LoadBundleComponents(dir);

                    if (children.Any())
                        yield return new FileSystemExtension(extensionName, dir, children, metadata);
                }
            }
        }

        private List<string> GetExtensionRoots()
        {
            var roots = new List<string>();

            // Default: 4 folders up + extensions
            var current = Path.GetDirectoryName(typeof(ExtensionManagerService).Assembly.Location);
            var defaultPath = Path.GetFullPath(Path.Combine(current, "..", "..", "..", "..", "extensions"));
            roots.Add(defaultPath);

            // Custom userextensions from config
            var configPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "pyRevit", "pyRevit_config.ini");
            if (File.Exists(configPath))
            {
                var config = PyRevitConfig.Load(configPath);
                if (config.UserExtensions != null && config.UserExtensions.Count > 0)
                    roots.AddRange(config.UserExtensions);
            }

            return roots;
        }

        private IEnumerable<ICommandComponent> LoadBundleComponents(string baseDir)
        {
            var components = new List<ICommandComponent>();

            foreach (var dir in Directory.GetDirectories(baseDir))
            {
                var type = Path.GetExtension(dir).ToLowerInvariant();
                if (!BundleTypes.Contains(type))
                    continue;

                components.Add(ParseComponent(dir, type));
            }

            return components;
        }

        private FileCommandComponent ParseComponent(string dir, string type)
        {
            var name = Path.GetFileNameWithoutExtension(dir);
            var children = LoadBundleComponents(dir);
            var scriptPath = Path.Combine(dir, "script.py");

            return new FileCommandComponent
            {
                Name = name,
                ScriptPath = File.Exists(scriptPath) ? scriptPath : null,
                Tooltip = $"Command: {name}",
                UniqueId = $"{Path.GetFileNameWithoutExtension(dir)}.{name}",
                ExtensionName = FindExtensionNameFromPath(dir),
                Type = type,
                Children = children.Cast<object>().ToList()
            };
        }

        private string FindExtensionNameFromPath(string path)
        {
            var segments = path.Split(Path.DirectorySeparatorChar);
            var extDir = segments.FirstOrDefault(s => s.EndsWith(".extension"));
            return extDir != null ? Path.GetFileNameWithoutExtension(extDir) : "UnknownExtension";
        }

        private ExtensionMetadata LoadMetadata(string extensionPath)
        {
            var yamlPath = Path.Combine(extensionPath, "extension.yaml");
            if (!File.Exists(yamlPath))
                return null;

            try
            {
                var yamlText = File.ReadAllText(yamlPath);
                return ParseYamlToMetadata(yamlText);
            }
            catch
            {
                return null;
            }
        }

        private ExtensionMetadata ParseYamlToMetadata(string yaml)
        {
            var metadata = new ExtensionMetadata();
            var lines = yaml.Split('\n');
            foreach (var line in lines)
            {
                var trimmed = line.Trim();
                if (trimmed.StartsWith("author:"))
                    metadata.Author = trimmed.Substring("author:".Length).Trim();
                else if (trimmed.StartsWith("version:"))
                    metadata.Version = trimmed.Substring("version:".Length).Trim();
                else if (trimmed.StartsWith("description:"))
                    metadata.Description = trimmed.Substring("description:".Length).Trim();
            }
            return metadata;
        }

        private class FileSystemExtension : IExtension
        {
            private readonly IEnumerable<ICommandComponent> _commands;

            public FileSystemExtension(string name, string path, IEnumerable<ICommandComponent> commands, ExtensionMetadata metadata)
            {
                Name = name;
                Directory = path;
                _commands = commands;
                Metadata = metadata;
            }

            public string Name { get; }
            public string Directory { get; }
            public ExtensionMetadata Metadata { get; }

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

        public class ExtensionMetadata
        {
            public string Author { get; set; }
            public string Version { get; set; }
            public string Description { get; set; }
        }
    }
}
