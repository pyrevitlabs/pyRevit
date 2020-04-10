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

        private static bool _underTest = false;
        private static bool _allClonesAreValid = false;

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

        public static bool UnderTest {
            get {
                lock (padlock) {
                    return _underTest;
                }
            }
            set {
                lock (padlock) {
                     _underTest = value;
                }
            }
        }

        public static bool AllClonesAreValid {
            get {
                lock (padlock) {
                    return _allClonesAreValid;
                }
            }
            set {
                lock (padlock) {
                    _allClonesAreValid = value;
                }
            }
        }
    }
}
