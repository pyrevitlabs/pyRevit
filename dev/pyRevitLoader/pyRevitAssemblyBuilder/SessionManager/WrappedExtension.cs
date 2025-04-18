using System.Collections.Generic;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.SessionManager
{
    public class WrappedExtension
    {
        public string Name { get; }
        public string Directory { get; }
        public ParsedExtensionMetadata Metadata { get; }
        public List<FileCommandComponent> Commands { get; }
        public object Children { get; internal set; }

        public WrappedExtension(string name, string path, List<FileCommandComponent> commands, ParsedExtensionMetadata metadata, List<FileCommandComponent> children)
        {
            Name = name;
            Directory = path;
            Commands = commands;
            Metadata = metadata;
            Children = children;
        }

        public string GetHash() => Directory.GetHashCode().ToString("X");

        public IEnumerable<FileCommandComponent> GetAllCommands() => Commands;
    }
}