using System.Collections.Generic;
using System.Linq;

using pyRevitLabs.Common.Extensions;

namespace pyRevitLabs.PyRevit {
    public class PyRevitDeployment {
        public PyRevitDeployment(string name, IEnumerable<string> paths) {
            Name = name;
            Paths = paths.ToList();
        }

        public override string ToString() {
            return string.Format("PyRevitDeployment Name: \"{0}\" | Paths: \"{1}\"",
                                 Name, Paths.ConvertToCommaSeparatedString());
        }

        public string Name { get; private set; }
        public List<string> Paths { get; private set; }
    }
}
