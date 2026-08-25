#nullable enable

using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.SessionManager;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager
{
    /// <summary>
    /// Immutable snapshot of the per-build settings that affect component visibility.
    /// </summary>
    public sealed class BuildSettings
    {
        public string CurrentVersion { get; }
        public bool LoadBeta { get; }

        public BuildSettings(string? currentVersion, bool loadBeta)
        {
            CurrentVersion = currentVersion ?? string.Empty;
            LoadBeta = loadBeta;
        }

        public static BuildSettings Empty { get; } = new BuildSettings(string.Empty, false);
    }

    /// <summary>
    /// Mutable holder for the <see cref="BuildSettings"/> shared between
    /// <see cref="UIManagerService"/> (writer) and the button/stack builders (readers).
    /// Refreshed once per <c>BuildUI</c> call so beta / version toggles take effect on reload
    /// and every builder observes the same snapshot.
    /// </summary>
    public sealed class BuildContext
    {
        public BuildSettings CurrentSettings { get; private set; } = BuildSettings.Empty;

        public void Update(BuildSettings settings)
        {
            CurrentSettings = settings ?? BuildSettings.Empty;
        }
    }

    /// <summary>
    /// Shared helpers for evaluating whether a parsed component should be visible
    /// in the current Revit session.
    /// </summary>
    public static class ComponentSupportUtils
    {
        /// <summary>
        /// Reads the current build settings that affect component visibility.
        /// </summary>
        public static BuildSettings ReadBuildSettings(
            UIApplication? uiApplication,
            ILogger? logger)
        {
            var currentVersion = uiApplication?.Application?.VersionNumber ?? string.Empty;
            var loadBeta = false;

            try
            {
                loadBeta = PyRevitConfig.Load().LoadBeta;
            }
            catch (Exception ex)
            {
                logger?.Debug($"Failed to read LoadBeta config. Defaulting to false: {ex.Message}");
            }

            return new BuildSettings(currentVersion, loadBeta);
        }

        /// <summary>
        /// Checks if a component is supported based on beta and Revit version constraints.
        /// </summary>
        public static bool IsSupported(
            ParsedComponent? component,
            string currentVersion,
            bool loadBeta,
            ILogger? logger = null)
        {
            if (component == null)
                return false;

            var displayName = component.DisplayName ?? component.Name ?? component.Type.ToString();

            if (component.IsBeta)
            {
                if (!loadBeta)
                {
                    logger?.Debug($"Skipping beta component '{displayName}' - beta tools not enabled.");
                    return false;
                }

                logger?.Debug($"Component '{displayName}' is beta and will be shown.");
            }

            if (string.IsNullOrEmpty(currentVersion))
            {
                logger?.Warning("Could not determine Revit version. Allowing all components.");
                return true;
            }

            var currentVersionNum = NormalizeVersionNumber(currentVersion);

            if (!string.IsNullOrEmpty(component.MinRevitVersion))
            {
                var minVersionNum = NormalizeVersionNumber(component.MinRevitVersion);
                if (currentVersionNum < minVersionNum)
                {
                    logger?.Debug(
                        $"Component '{displayName}' requires Revit {component.MinRevitVersion} or later. " +
                        $"Current version: {currentVersion}. Skipping.");
                    return false;
                }
            }

            if (!string.IsNullOrEmpty(component.MaxRevitVersion))
            {
                var maxVersionNum = NormalizeVersionNumber(component.MaxRevitVersion);
                if (currentVersionNum > maxVersionNum)
                {
                    logger?.Debug(
                        $"Component '{displayName}' supports up to Revit {component.MaxRevitVersion}. " +
                        $"Current version: {currentVersion}. Skipping.");
                    return false;
                }
            }

            return true;
        }

        /// <summary>
        /// Returns visible children for pulldowns and split buttons, while collapsing
        /// orphan separators created by filtered-out items.
        /// </summary>
        public static List<ParsedComponent> GetVisibleButtonGroupChildren(
            IEnumerable<ParsedComponent>? children,
            string currentVersion,
            bool loadBeta,
            ILogger? logger = null)
        {
            var visibleChildren = new List<ParsedComponent>();
            var pendingSeparator = false;

            if (children == null)
                return visibleChildren;

            foreach (var child in children)
            {
                if (child == null)
                    continue;

                if (child.Type == ExtensionParser.CommandComponentType.Separator)
                {
                    if (visibleChildren.Count > 0)
                        pendingSeparator = true;
                    continue;
                }

                if (!IsSupported(child, currentVersion, loadBeta, logger))
                    continue;

                if (pendingSeparator)
                {
                    visibleChildren.Add(new ParsedComponent
                    {
                        Name = "---",
                        DisplayName = "---",
                        Type = ExtensionParser.CommandComponentType.Separator,
                        Directory = string.Empty
                    });
                    pendingSeparator = false;
                }

                visibleChildren.Add(child);
            }

            return visibleChildren;
        }

        /// <summary>
        /// Checks if a button group has at least one visible command child.
        /// Short-circuits on the first supported non-separator child.
        /// </summary>
        public static bool HasVisibleButtonGroupChildren(
            ParsedComponent? component,
            string currentVersion,
            bool loadBeta,
            ILogger? logger = null)
        {
            if (component?.Children == null)
                return false;

            foreach (var child in component.Children)
            {
                if (child == null)
                    continue;

                if (child.Type == ExtensionParser.CommandComponentType.Separator)
                    continue;

                if (IsSupported(child, currentVersion, loadBeta, logger))
                    return true;
            }

            return false;
        }

        /// <summary>
        /// Checks whether a stack child should be visible. A pulldown or split button
        /// whose own children are all filtered out is considered not visible.
        /// </summary>
        public static bool IsStackChildVisible(
            ParsedComponent? component,
            string currentVersion,
            bool loadBeta,
            ILogger? logger = null)
        {
            if (!IsSupported(component, currentVersion, loadBeta, logger))
                return false;

            if (component!.Type == ExtensionParser.CommandComponentType.PullDown
                || component.Type == ExtensionParser.CommandComponentType.SplitButton
                || component.Type == ExtensionParser.CommandComponentType.SplitPushButton)
            {
                return HasVisibleButtonGroupChildren(component, currentVersion, loadBeta, logger);
            }

            return true;
        }

        /// <summary>
        /// Normalizes a Revit version string for numeric comparison.
        /// Any 2-digit value is treated as a legacy 20xx year (e.g. "20" -> 2020).
        /// </summary>
        public static int NormalizeVersionNumber(string? version)
        {
            if (string.IsNullOrEmpty(version))
                return 0;

            var digits = new string(version.Where(char.IsDigit).ToArray());

            if (string.IsNullOrEmpty(digits))
                return 0;

            if (!int.TryParse(digits, out var versionNum))
                return 0;

            // Legacy 2-digit format: Revit 2017-2020 manifests used "17"-"20". Anything
            // under 100 is assumed to be that shorthand and widened to 20xx.
            if (versionNum < 100)
                versionNum = 2000 + versionNum;

            return versionNum;
        }
    }
}
