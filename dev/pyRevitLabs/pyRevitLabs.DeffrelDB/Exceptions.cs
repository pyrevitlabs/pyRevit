using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace pyRevitLabs.DeffrelDB {
    public class DeffrelDBException : Exception {
        public DeffrelDBException() { }

        public DeffrelDBException(string message) : base(message) { }

        public DeffrelDBException(string message, Exception innerException) : base(message, innerException) { }
    }

    public class AccessRestrictedException : DeffrelDBException {
        public AccessRestrictedException() { }

        public AccessRestrictedException(ConnectionLock newLock, ConnectionLock restrictingLock) {
            NewLock = newLock;
            RestrictingLock = restrictingLock;
        }

        public ConnectionLock NewLock { get; set; }
        public ConnectionLock RestrictingLock { get; set; }

        public override string Message {
            get {
                return string.Format("Requested lock {0} is restricted by {1}", NewLock, RestrictingLock);
            }
        }
    }

    public class AccessRestrictedByExistingLockException : DeffrelDBException {
        public AccessRestrictedByExistingLockException() { }

        public AccessRestrictedByExistingLockException(ConnectionLock newLock, ConnectionLock restrictingLock) {
            NewLock = newLock;
            RestrictingLock = restrictingLock;
        }

        public ConnectionLock NewLock { get; set; }
        public ConnectionLock RestrictingLock { get; set; }

        public override string Message {
            get {
                return string.Format("Requested lock {0} is not on the same path as active connection lock"
                                     + " {1}. Active lock must be released first.", NewLock, RestrictingLock);
            }
        }
    }


}
