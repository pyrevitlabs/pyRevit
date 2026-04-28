#nullable enable
using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.UI;
using pyRevitLabs.Common.Security;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Service for managing and querying installed pyRevit extensions.
    /// </summary>
    public class ExtensionManagerService : IExtensionManagerService
    {
        private readonly int _revitYear;
        private readonly UIApplication? _uiApplication;
        private readonly ILogger? _logger;
        private List<ParsedExtension>? _cachedExtensions;
        private readonly HashSet<string> _authorizedExtensions = new(StringComparer.OrdinalIgnoreCase);
        private readonly HashSet<string> _unauthorizedExtensions = new(StringComparer.OrdinalIgnoreCase);

        public ExtensionManagerService(int revitYear = 0, UIApplication? uiApplication = null, ILogger? logger = null)
        {
            _revitYear = revitYear;
            _uiApplication = uiApplication;
            _logger = logger;
        }

        private string GetRevitUsername()
        {
            var revitUsername = _uiApplication?.Application?.Username;
            var uname = revitUsername ?? Environment.UserName;
            var atIndex = uname.IndexOf('@');
            if (atIndex > 0)
                uname = uname.Substring(0, atIndex);
            uname = uname.Replace(".", "");
            return uname;
        }

        /// <summary>
        /// Gets all parsed extensions (cached).
        /// </summary>
        private List<ParsedExtension> GetAllExtensionsCached()
        {
            return _cachedExtensions ??= ExtensionParser.ParseInstalledExtensions(_revitYear).ToList();
        }

        /// <summary>
        /// Clears the extension cache, forcing a re-parse on next access.
        /// </summary>
        public void ClearCache()
        {
            _cachedExtensions = null;
            _authorizedExtensions.Clear();
            _unauthorizedExtensions.Clear();
        }
        
        /// <summary>
        /// Clears all parser caches including the static caches in ExtensionParser.
        /// This ensures newly installed or enabled extensions are discovered on reload.
        /// </summary>
        public void ClearParserCaches()
        {
            _cachedExtensions = null;
            _authorizedExtensions.Clear();
            _unauthorizedExtensions.Clear();
            ExtensionParser.ClearAllCaches();
        }

        /// <summary>
        /// Checks if the current user has access to the extension based on:
        /// 1. Whether the extension is disabled in config
        /// 2. Whether authorized users are defined and current user is in the list
        /// 3. Whether authorized groups are defined and user is member of at least one
        /// </summary>
        private bool IsExtensionAllowed(ParsedExtension ext)
        {
            if (ext.Config?.Disabled == true)
            {
                _logger?.Debug($"Extension '{ext.Name}' is disabled in config");
                return false;
            }

            var cacheKey = ext.Directory;

            if (_authorizedExtensions.Contains(cacheKey))
                return true;

            if (_unauthorizedExtensions.Contains(cacheKey))
                return false;

            var isAllowed = EvaluateAuthorization(ext, ext.AuthorizedUsers, ext.AuthorizedGroups);

            if (isAllowed)
                _authorizedExtensions.Add(cacheKey);
            else
                _unauthorizedExtensions.Add(cacheKey);

            return isAllowed;
        }

        private bool EvaluateAuthorization(
            ParsedExtension ext,
            List<string>? authorizedUsers,
            List<string>? authorizedGroups)
        {
            if (authorizedUsers is { Count: > 0 })
            {
                var currentUser = GetRevitUsername();
                if (!authorizedUsers.Contains(currentUser, StringComparer.OrdinalIgnoreCase))
                {
                    _logger?.Warning($"Extension '{ext.Name}' is NOT available for user '{currentUser}' (not in AuthorizedUsers)");
                    return false;
                }

                _logger?.Info($"User '{currentUser}' is authorized for extension '{ext.Name}'");
                return true;
            }

            if (authorizedGroups is { Count: > 0 })
            {
                foreach (var groupSid in authorizedGroups)
                {
                    if (UserIsInSecurityGroup(groupSid))
                    {
                        _logger?.Info($"User is authorized for extension '{ext.Name}' (AuthorizedGroups match)");
                        return true;
                    }
                }

                _logger?.Warning($"Extension '{ext.Name}' is NOT available for current user (not in AuthorizedGroups)");
                return false;
            }

            return true;
        }

        /// <summary>
        /// Checks if the current Windows user is a member of the specified security group.
        /// </summary>
        /// <param name="targetSid">The SID of the security group to check</param>
        /// <returns>True if user is member of the group</returns>
        private static bool UserIsInSecurityGroup(string targetSid)
        {
            if (string.IsNullOrEmpty(targetSid))
                return false;

            try
            {
                return UserAuth.UserIsInSecurityGroup(targetSid);
            }
            catch
            {
                // Ignore errors in security group enumeration
            }

            return false;
        }

        /// <summary>
        /// Gets all installed extensions that are not disabled and pass authorization checks.
        /// </summary>
        /// <returns>An enumerable collection of parsed extensions.</returns>
        public IEnumerable<ParsedExtension> GetInstalledExtensions()
        {
            return GetAllExtensionsCached()
                .Where(ext => IsExtensionAllowed(ext));
        }

        /// <summary>
        /// Gets all installed UI extensions (extensions ending with .extension) that are not disabled
        /// and pass authorization checks.
        /// </summary>
        /// <returns>An enumerable collection of parsed UI extensions.</returns>
        public IEnumerable<ParsedExtension> GetInstalledUIExtensions()
        {
            return GetAllExtensionsCached()
                .Where(ext => IsExtensionAllowed(ext) &&
                       ext.Directory.EndsWith(ExtensionConstants.UI_EXTENSION_SUFFIX, System.StringComparison.OrdinalIgnoreCase));
        }

        /// <summary>
        /// Gets all installed library extensions (extensions ending with .lib) that are not disabled
        /// and pass authorization checks.
        /// </summary>
        /// <returns>An enumerable collection of parsed library extensions.</returns>
        public IEnumerable<ParsedExtension> GetInstalledLibraryExtensions()
        {
            return GetAllExtensionsCached()
                .Where(ext => IsExtensionAllowed(ext) &&
                       ext.Directory.EndsWith(ExtensionConstants.LIBRARY_EXTENSION_SUFFIX, System.StringComparison.OrdinalIgnoreCase));
        }
    }
}
