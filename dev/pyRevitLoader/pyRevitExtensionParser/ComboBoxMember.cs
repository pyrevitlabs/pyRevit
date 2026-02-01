namespace pyRevitExtensionParser
{
    /// <summary>
    /// Represents a single member/item in a ComboBox control.
    /// </summary>
    /// <remarks>
    /// <para>ComboBox members are defined in bundle.yaml under the 'members' key.</para>
    /// <para>Each member has an id (internal identifier) and text (display text).</para>
    /// <para>Optional properties include icon, tooltip, and group for advanced customization.</para>
    /// </remarks>
    /// <example>
    /// <code>
    /// members:
    ///   - id: "one"
    ///     text: "Option One"
    ///     icon: "icon_one.png"
    ///     tooltip: "Select option one"
    ///   - id: "two"
    ///     text: "Option Two"
    /// </code>
    /// </example>
    public class ComboBoxMember
    {
        /// <summary>
        /// Gets or sets the unique identifier for this member.
        /// </summary>
        /// <remarks>
        /// This is used internally to identify the selected item.
        /// Must be unique within the ComboBox.
        /// </remarks>
        public string Id { get; set; }

        /// <summary>
        /// Gets or sets the display text for this member.
        /// </summary>
        /// <remarks>
        /// This is the text shown to the user in the ComboBox dropdown.
        /// </remarks>
        public string Text { get; set; }

        /// <summary>
        /// Gets or sets the icon path for this member.
        /// </summary>
        /// <remarks>
        /// Optional. Path can be relative to the bundle directory or absolute.
        /// </remarks>
        public string Icon { get; set; }

        /// <summary>
        /// Gets or sets the tooltip for this member.
        /// </summary>
        /// <remarks>
        /// Optional. Shown when hovering over this member in the dropdown.
        /// </remarks>
        public string Tooltip { get; set; }

        /// <summary>
        /// Gets or sets the group name for this member.
        /// </summary>
        /// <remarks>
        /// Optional. Used to group related members together in the ComboBox.
        /// </remarks>
        public string Group { get; set; }

        /// <summary>
        /// Gets or sets the tooltip image path for this member.
        /// </summary>
        /// <remarks>
        /// Optional. Path can be relative to the bundle directory or absolute.
        /// </remarks>
        public string TooltipImage { get; set; }
    }
}
