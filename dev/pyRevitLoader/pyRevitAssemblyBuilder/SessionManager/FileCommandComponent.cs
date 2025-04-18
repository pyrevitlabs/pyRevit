using System.Collections.Generic;
using System.Linq;

namespace pyRevitAssemblyBuilder.SessionManager
{
    public class FileCommandComponent
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