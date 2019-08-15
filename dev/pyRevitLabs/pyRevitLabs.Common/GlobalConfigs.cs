using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace pyRevitLabs.Common {

    // class for configuring global behaviour of libraries
    public sealed class GlobalConfigs {
        private static GlobalConfigs instance = null;
        private static readonly object padlock = new object();

        GlobalConfigs() {
        }

        public static GlobalConfigs Instance {
            get {
                lock (padlock) {
                    if (instance is null) {
                        instance = new GlobalConfigs();
                    }
                    return instance;
                }
            }
        }

        public static bool UnderTest { get; set; }
        public static bool AllClonesAreValid { get; set; }
    }
}
