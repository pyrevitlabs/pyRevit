#nullable enable
using System;
using System.IO;
using System.Linq;
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.SessionManager;
using pyRevitAssemblyBuilder.UIManager.Buttons;
using pyRevitAssemblyBuilder.UIManager.Icons;
using pyRevitExtensionParser;
using RevitComboBoxMember = Autodesk.Revit.UI.ComboBoxMember;

namespace pyRevitAssemblyBuilder.UIManager.Builders
{
    /// <summary>
    /// Handles the creation and configuration of ComboBox controls.
    /// </summary>
    public class ComboBoxBuilder : IComboBoxBuilder
    {
        private readonly ILogger _logger;
        private readonly IButtonPostProcessor _buttonPostProcessor;
        private readonly ComboBoxScriptInitializer? _comboBoxScriptInitializer;

        /// <summary>
        /// Initializes a new instance of the <see cref="ComboBoxBuilder"/> class.
        /// </summary>
        /// <param name="logger">The logger instance.</param>
        /// <param name="buttonPostProcessor">The button post-processor for icon management.</param>
        /// <param name="comboBoxScriptInitializer">Optional ComboBox script initializer.</param>
        public ComboBoxBuilder(
            ILogger logger,
            IButtonPostProcessor buttonPostProcessor,
            ComboBoxScriptInitializer? comboBoxScriptInitializer = null)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _buttonPostProcessor = buttonPostProcessor ?? throw new ArgumentNullException(nameof(buttonPostProcessor));
            _comboBoxScriptInitializer = comboBoxScriptInitializer;
        }

        /// <inheritdoc/>
        public void CreateComboBox(ParsedComponent component, RibbonPanel parentPanel)
        {
            if (parentPanel == null)
            {
                _logger.Warning($"Cannot create ComboBox '{component.DisplayName}': parent panel is null.");
                return;
            }

            try
            {
                // Use localized title which handles fallback to DisplayName
                var comboBoxText = ExtensionParser.GetComponentTitle(component);

                // Create ComboBoxData - use DisplayName to match control ID format
                var comboBoxData = new ComboBoxData(component.DisplayName);

                // Add ComboBox to panel
                var comboBox = parentPanel.AddItem(comboBoxData) as ComboBox;
                if (comboBox == null)
                {
                    _logger.Warning($"Failed to create ComboBox '{comboBoxText}'.");
                    return;
                }

                // Set localized tooltip if available
                var localizedTooltip = ExtensionParser.GetComponentTooltip(component);
                if (!string.IsNullOrEmpty(localizedTooltip))
                {
                    comboBox.ToolTip = localizedTooltip;
                }

                // Set ItemText (initial display text)
                if (!string.IsNullOrEmpty(comboBoxText))
                {
                    try
                    {
                        comboBox.ItemText = comboBoxText;
                    }
                    catch (Exception ex)
                    {
                        _logger.Debug($"Could not set ItemText for ComboBox '{comboBoxText}'. Exception: {ex.Message}");
                    }
                }

                // Add members to ComboBox
                AddMembersToComboBox(comboBox, component, comboBoxText);

                // Apply icon to the ComboBox itself
                _buttonPostProcessor.IconManager.ApplyIcon(comboBox, component, null, IconMode.SmallOnly);

                // Execute event handler setup script if present
                if (_comboBoxScriptInitializer != null)
                {
                    try
                    {
                        _comboBoxScriptInitializer.ExecuteEventHandlerSetup(component, comboBox);
                    }
                    catch (Exception scriptEx)
                    {
                        _logger.Warning($"ComboBox event handler setup failed for '{comboBoxText}'. Exception: {scriptEx.Message}");
                    }
                }

                _logger.Debug($"Successfully created ComboBox '{comboBoxText}' with {component.Members?.Count ?? 0} members.");
            }
            catch (Exception ex)
            {
                _logger.Error($"Failed to create ComboBox '{component.DisplayName}'. Exception: {ex.Message}");
            }
        }

        /// <summary>
        /// Adds members to a ComboBox.
        /// </summary>
        private void AddMembersToComboBox(ComboBox comboBox, ParsedComponent component, string comboBoxText)
        {
            if (component.Members == null || component.Members.Count == 0)
                return;

            foreach (var member in component.Members)
            {
                if (string.IsNullOrEmpty(member.Id) || string.IsNullOrEmpty(member.Text))
                {
                    _logger.Debug("Skipping ComboBox member with missing id or text.");
                    continue;
                }

                try
                {
                    // Create member data
                    var memberData = new ComboBoxMemberData(member.Id, member.Text);

                    // Set group name on data before adding (GroupName is read-only on ComboBoxMember)
                    if (!string.IsNullOrEmpty(member.Group))
                    {
                        memberData.GroupName = member.Group;
                    }

                    // Add member to ComboBox
                    var addedMember = comboBox.AddItem(memberData);

                    if (addedMember != null)
                    {
                        // Set member tooltip if available
                        if (!string.IsNullOrEmpty(member.Tooltip))
                        {
                            addedMember.ToolTip = member.Tooltip;
                        }

                        // Set member icon if available
                        if (!string.IsNullOrEmpty(member.Icon))
                        {
                            ApplyIconToComboBoxMember(addedMember, member, component);
                        }
                    }
                }
                catch (Exception ex)
                {
                    _logger.Debug($"Error adding member '{member.Text}' to ComboBox '{comboBoxText}'. Exception: {ex.Message}");
                }
            }

            // Set current selection to first item
            var items = comboBox.GetItems();
            if (items != null && items.Count > 0)
            {
                try
                {
                    comboBox.Current = items[0];
                }
                catch (Exception ex)
                {
                    _logger.Debug($"Could not set current item for ComboBox '{comboBoxText}'. Exception: {ex.Message}");
                }
            }
        }

        /// <summary>
        /// Applies icon to a ComboBox member.
        /// </summary>
        private void ApplyIconToComboBoxMember(RevitComboBoxMember member, pyRevitExtensionParser.ComboBoxMember memberDef, ParsedComponent parentComponent)
        {
            if (string.IsNullOrEmpty(memberDef.Icon))
                return;

            try
            {
                // Resolve icon path (relative to bundle directory or absolute)
                var iconPath = memberDef.Icon;
                if (!Path.IsPathRooted(iconPath) && !string.IsNullOrEmpty(parentComponent.Directory))
                {
                    iconPath = Path.Combine(parentComponent.Directory, memberDef.Icon);
                }

                if (File.Exists(iconPath))
                {
                    var bitmap = _buttonPostProcessor.IconManager.LoadBitmapSource(iconPath, UIManagerConstants.ICON_SMALL);
                    if (bitmap != null)
                    {
                        member.Image = bitmap;
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.Debug($"Failed to apply icon to ComboBox member '{memberDef.Text}'. Exception: {ex.Message}");
            }
        }
    }
}
