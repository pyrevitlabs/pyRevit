using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Management;
using System.Security.Principal;
using System.IO;

using DotNetVersionFinder;
using System.Security.AccessControl;

namespace pyRevitLabs.Common {
    // https://stackoverflow.com/a/22020271
    public class UserSecurity {
        WindowsIdentity _currentUser;
        WindowsPrincipal _currentPrincipal;

        public UserSecurity() {
            _currentUser = WindowsIdentity.GetCurrent();
            _currentPrincipal = new WindowsPrincipal(_currentUser);
        }

        public bool HasAccess(DirectoryInfo directory, FileSystemRights right) {
            // Get the collection of authorization rules that apply to the directory.
            AuthorizationRuleCollection acl = directory.GetAccessControl()
                .GetAccessRules(true, true, typeof(SecurityIdentifier));
            return HasFileOrDirectoryAccess(right, acl);
        }

        public bool HasAccess(FileInfo file, FileSystemRights right) {
            // Get the collection of authorization rules that apply to the file.
            AuthorizationRuleCollection acl = file.GetAccessControl()
                .GetAccessRules(true, true, typeof(SecurityIdentifier));
            return HasFileOrDirectoryAccess(right, acl);
        }

        private bool HasFileOrDirectoryAccess(FileSystemRights right,
                                              AuthorizationRuleCollection acl) {
            bool allow = false;
            bool inheritedAllow = false;
            bool inheritedDeny = false;

            for (int i = 0; i < acl.Count; i++) {
                var currentRule = (FileSystemAccessRule)acl[i];
                // If the current rule applies to the current user.
                if (_currentUser.User.Equals(currentRule.IdentityReference) ||
                    _currentPrincipal.IsInRole(
                                    (SecurityIdentifier)currentRule.IdentityReference)) {

                    if (currentRule.AccessControlType.Equals(AccessControlType.Deny)) {
                        if ((currentRule.FileSystemRights & right) == right) {
                            if (currentRule.IsInherited) {
                                inheritedDeny = true;
                            }
                            else { // Non inherited "deny" takes overall precedence.
                                return false;
                            }
                        }
                    }
                    else if (currentRule.AccessControlType
                                                    .Equals(AccessControlType.Allow)) {
                        if ((currentRule.FileSystemRights & right) == right) {
                            if (currentRule.IsInherited) {
                                inheritedAllow = true;
                            }
                            else {
                                allow = true;
                            }
                        }
                    }
                }
            }

            if (allow) { // Non inherited "allow" takes precedence over inherited rules.
                return true;
            }
            return inheritedAllow && !inheritedDeny;
        }
    }
}
