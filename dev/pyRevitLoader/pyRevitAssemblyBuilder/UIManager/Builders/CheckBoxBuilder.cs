#nullable enable
using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.SessionManager;
using pyRevitAssemblyBuilder.UIManager.Panels;
using pyRevitExtensionParser;
using AdwRibbonCheckBox = Autodesk.Windows.RibbonCheckBox;
using AdwRibbonPanelSource = Autodesk.Windows.RibbonPanelSource;
using AdwRibbonRowBreak = Autodesk.Windows.RibbonRowBreak;
using AdwRibbonRowPanel = Autodesk.Windows.RibbonRowPanel;

namespace pyRevitAssemblyBuilder.UIManager.Builders
{
    /// <summary>
    /// Builds .checkbox bundles as AdWindows ribbon checkboxes, on their own or stacked in rows.
    /// </summary>
    /// <remarks>
    /// Important: the Revit API has no ribbon checkbox, so the checkbox exists only in the AdWindows
    /// panel behind the Revit <see cref="RibbonPanel"/>, and <see cref="RibbonPanel.GetItems"/> never
    /// returns it. Reloads therefore find it by its AdWindows id, and checkboxes stack only with other
    /// checkboxes, because Revit API stacks cannot take AdWindows items.
    /// Invariant: <see cref="RibbonScanner"/> tracks checkboxes by their full id, and
    /// <see cref="UIManagerService"/> marks the ids these methods return, so a checkbox removed before
    /// a reload is hidden even when another one in the panel has the same name. A stacked checkbox's
    /// id also names its stack, so it never matches a standalone checkbox with the same name in the
    /// same panel. A stack row whose build fails is logged and still returned, as a button whose build
    /// fails is still marked, so the rows after it are still built and none of them is hidden as an
    /// orphan.
    /// Note: reloads refresh checkboxes where they are and never move them, so moving a checkbox into
    /// or out of a stack needs a Revit restart.
    /// </remarks>
    public class CheckBoxBuilder : ICheckBoxBuilder
    {
        private const string ControlIdPrefix = "pyRevitCheckBox";
        private const string StackIdPrefix = "pyRevitCheckBoxStack";
        private const int MaxStackRows = 3;

        private readonly ILogger _logger;
        private readonly IPanelStyleManager _panelStyleManager;
        private readonly CheckBoxScriptInitializer? _checkBoxScriptInitializer;

        /// <summary>
        /// Initializes a new instance of the <see cref="CheckBoxBuilder"/> class.
        /// </summary>
        /// <param name="panelStyleManager">Resolves the AdWindows panel behind a Revit panel.</param>
        /// <param name="checkBoxScriptInitializer">Wires each bundle script's handlers; without it the checkboxes get none.</param>
        public CheckBoxBuilder(
            ILogger logger,
            IPanelStyleManager panelStyleManager,
            CheckBoxScriptInitializer? checkBoxScriptInitializer = null)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _panelStyleManager = panelStyleManager ?? throw new ArgumentNullException(nameof(panelStyleManager));
            _checkBoxScriptInitializer = checkBoxScriptInitializer;
        }

        /// <inheritdoc/>
        public string? CreateOrUpdateCheckBox(ParsedComponent component, RibbonPanel parentPanel, string tabName)
        {
            var panelSource = GetPanelSource(component, parentPanel, tabName);
            if (panelSource == null)
                return null;

            try
            {
                var controlId = BuildControlId(tabName, parentPanel.Name, component.DisplayName);
                var checkBox = AdWindowsHelper.FindRibbonItemByName(panelSource.Items, controlId) as AdwRibbonCheckBox;
                if (checkBox == null)
                {
                    checkBox = CreateCheckBox(controlId, component);
                    panelSource.Items.Add(checkBox);
                }

                RefreshCheckBox(checkBox, component);
                return controlId;
            }
            catch (Exception ex)
            {
                _logger.Error($"Failed to build CheckBox '{component.DisplayName}'. Exception: {ex.Message}");
                return null;
            }
        }

        /// <inheritdoc/>
        public IReadOnlyCollection<string> CreateOrUpdateCheckBoxStack(
            ParsedComponent stackComponent,
            IReadOnlyList<ParsedComponent> checkBoxComponents,
            RibbonPanel parentPanel,
            string tabName)
        {
            var shownIds = new HashSet<string>();
            var panelSource = GetPanelSource(stackComponent, parentPanel, tabName);
            if (panelSource == null)
                return shownIds;

            if (checkBoxComponents.Count > MaxStackRows)
                _logger.Warning($"Stack '{stackComponent.DisplayName}' has {checkBoxComponents.Count} checkboxes; only the first {MaxStackRows} are shown.");

            try
            {
                var stackId = BuildStackId(tabName, parentPanel.Name, stackComponent.DisplayName);
                var rowPanel = AdWindowsHelper.FindRibbonItemByName(panelSource.Items, stackId) as AdwRibbonRowPanel;
                if (rowPanel == null)
                {
                    rowPanel = new AdwRibbonRowPanel { Id = stackId };
                    panelSource.Items.Add(rowPanel);
                }

                foreach (var component in checkBoxComponents.Take(MaxStackRows))
                {
                    var controlId = BuildStackedControlId(tabName, parentPanel.Name, stackComponent.DisplayName, component.DisplayName);
                    shownIds.Add(controlId);
                    BuildStackRow(rowPanel, controlId, component, stackComponent);
                }

                HideCheckBoxesNotIn(rowPanel, shownIds);
            }
            catch (Exception ex)
            {
                _logger.Error($"Failed to build CheckBox stack '{stackComponent.DisplayName}'. Exception: {ex.Message}");
            }

            return shownIds;
        }

        private void BuildStackRow(AdwRibbonRowPanel rowPanel, string controlId, ParsedComponent component, ParsedComponent stackComponent)
        {
            try
            {
                var checkBox = AdWindowsHelper.FindRibbonItemByName(rowPanel.Items, controlId) as AdwRibbonCheckBox;
                if (checkBox == null)
                {
                    checkBox = CreateCheckBox(controlId, component);
                    if (rowPanel.Items.Count > 0)
                        rowPanel.Items.Add(new AdwRibbonRowBreak());

                    rowPanel.Items.Add(checkBox);
                }

                RefreshCheckBox(checkBox, component);
            }
            catch (Exception ex)
            {
                _logger.Error($"Failed to build CheckBox '{component.DisplayName}' in stack '{stackComponent.DisplayName}'. Exception: {ex.Message}");
            }
        }

        private static string BuildControlId(string tabName, string panelName, string displayName)
        {
            return $"{ControlIdPrefix}%{tabName}%{panelName}%{displayName}";
        }

        private static string BuildStackId(string tabName, string panelName, string stackDisplayName)
        {
            return $"{StackIdPrefix}%{tabName}%{panelName}%{stackDisplayName}";
        }

        private static string BuildStackedControlId(string tabName, string panelName, string stackDisplayName, string displayName)
        {
            return $"{ControlIdPrefix}%{tabName}%{panelName}%{stackDisplayName}%{displayName}";
        }

        private static void HideCheckBoxesNotIn(AdwRibbonRowPanel rowPanel, ISet<string> shownIds)
        {
            foreach (var checkBox in rowPanel.Items.OfType<AdwRibbonCheckBox>())
            {
                if (shownIds.Contains(checkBox.Id))
                    continue;

                checkBox.IsVisible = false;
                checkBox.IsEnabled = false;
            }
        }

        private static AdwRibbonCheckBox CreateCheckBox(string controlId, ParsedComponent component)
        {
            return new AdwRibbonCheckBox
            {
                Id = controlId,
                Name = component.DisplayName,
                ShowText = true,
                IsChecked = component.IsChecked
            };
        }

        private AdwRibbonPanelSource? GetPanelSource(ParsedComponent component, RibbonPanel? parentPanel, string tabName)
        {
            if (parentPanel == null)
            {
                _logger.Warning($"Cannot build '{component.DisplayName}': parent panel is null.");
                return null;
            }

            var panelSource = _panelStyleManager.GetAdWindowsPanel(parentPanel, tabName)?.Source;
            if (panelSource?.Items == null)
            {
                _logger.Warning($"Cannot build '{component.DisplayName}': no AdWindows panel found for '{parentPanel.Name}' in tab '{tabName}'.");
                return null;
            }

            return panelSource;
        }

        private void RefreshCheckBox(AdwRibbonCheckBox checkBox, ParsedComponent component)
        {
            checkBox.Text = ExtensionParser.GetComponentTitle(component);
            var tooltip = ExtensionParser.GetComponentTooltip(component);
            checkBox.ToolTip = string.IsNullOrEmpty(tooltip) ? null : tooltip;
            checkBox.IsVisible = true;
            checkBox.IsEnabled = true;
            SetUpScriptHandlers(component, checkBox);
        }

        private void SetUpScriptHandlers(ParsedComponent component, AdwRibbonCheckBox checkBox)
        {
            if (_checkBoxScriptInitializer == null)
                return;

            try
            {
                _checkBoxScriptInitializer.ExecuteEventHandlerSetup(component, checkBox);
            }
            catch (Exception ex)
            {
                _logger.Warning($"CheckBox event handler setup failed for '{component.DisplayName}'. Exception: {ex.Message}");
            }
        }
    }
}
