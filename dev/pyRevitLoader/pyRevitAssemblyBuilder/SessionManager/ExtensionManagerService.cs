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

        private static readonly string[] SupportedBundleTypes = new[]
        {
            ".pushbutton", ".pulldownbutton", ".splitbutton", ".stack", ".panel", ".tab"
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
                    var commands = LoadCommands(dir);
                    if (commands.Any())
                        yield return new FileSystemExtension(extensionName, dir, commands, metadata);
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
                {
                    roots.AddRange(config.UserExtensions);
                }
            }

            return roots;
        }

        private IEnumerable<ICommandComponent> LoadCommands(string extensionPath)
        {
            var cmds = new List<ICommandComponent>();

            foreach (var bundleDir in Directory.GetDirectories(extensionPath, "*.*", SearchOption.AllDirectories))
            {
                var bundleType = Path.GetExtension(bundleDir).ToLowerInvariant();
                if (!SupportedBundleTypes.Contains(bundleType))
                    continue;

                var scriptPath = Path.Combine(bundleDir, "script.py");
                if (!File.Exists(scriptPath))
                    continue;

                var name = Path.GetFileNameWithoutExtension(bundleDir);
                cmds.Add(new FileCommandComponent
                {
                    Name = name,
                    ScriptPath = scriptPath,
                    Tooltip = $"Command: {name}",
                    UniqueId = $"{Path.GetFileNameWithoutExtension(extensionPath)}.{name}",
                    ExtensionName = Path.GetFileNameWithoutExtension(extensionPath)
                });
            }

            return cmds;
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
        }

        private class FileCommandComponent : ICommandComponent
        {
            public string Name { get; set; }
            public string ScriptPath { get; set; }
            public string Tooltip { get; set; }
            public string UniqueId { get; set; }
            public string ExtensionName { get; set; }
        }

        public class ExtensionMetadata
        {
            public string Author { get; set; }
            public string Version { get; set; }
            public string Description { get; set; }
        }
    }
}