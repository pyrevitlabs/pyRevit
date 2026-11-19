#nullable enable
using System.Collections.Generic;
using System.Linq;
using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager
{
    /// <summary>
    /// Splits a stack's visible children between a Revit API stack and a checkbox stack.
    /// </summary>
    /// <remarks>
    /// Note: checkboxes stack only with other checkboxes, because Revit API stacks cannot hold
    /// AdWindows items. A mixed stack therefore becomes its other items plus its checkboxes beside
    /// them. The other items form a stack when there are two or more, and a single one is built on
    /// its own. The checkboxes always go through the checkbox stack builder, even when there is only
    /// one, so their ids name the stack.
    /// Important: keep this class free of AdWindows and Revit API types, so the split is tested
    /// without Revit.
    /// </remarks>
    internal sealed class StackItemSplit
    {
        private readonly List<ParsedComponent> _visibleChildren;

        private StackItemSplit(List<ParsedComponent> visibleChildren)
        {
            _visibleChildren = visibleChildren;
            var items = visibleChildren.Where(child => child.Type != CommandComponentType.Separator).ToList();
            CheckBoxes = items.Where(IsCheckBox).ToList();
            OtherItems = items.Where(child => !IsCheckBox(child)).ToList();
        }

        /// <summary>Gets the checkboxes, in layout order.</summary>
        public IReadOnlyList<ParsedComponent> CheckBoxes { get; }

        /// <summary>Gets the items that are neither checkboxes nor separators, in layout order.</summary>
        public IReadOnlyList<ParsedComponent> OtherItems { get; }

        /// <summary>
        /// Gets whether the stack is a single item that is not a checkbox, which is built as if it
        /// were not stacked.
        /// </summary>
        public bool IsSingleItem => OtherItems.Count == 1 && CheckBoxes.Count == 0;

        public bool IsMixed => CheckBoxes.Count > 0 && OtherItems.Count > 0;

        /// <summary>
        /// Gets the only other item, which is built on its own because a Revit API stack needs two or
        /// more; null when there is no other item or there are several.
        /// </summary>
        public ParsedComponent? LoneOtherItem => OtherItems.Count == 1 ? OtherItems[0] : null;

        public bool HasRevitApiStack => OtherItems.Count > 1;

        public static StackItemSplit Of(IEnumerable<ParsedComponent> visibleChildren)
        {
            return new StackItemSplit(visibleChildren.ToList());
        }

        /// <summary>
        /// Lists the keys the ribbon scanner marks as touched for the built stack.
        /// </summary>
        /// <param name="shownCheckBoxIds">The ids the checkbox stack builder returned.</param>
        /// <remarks>
        /// Invariant: the other children are marked by name and the checkboxes by id, because
        /// <see cref="RibbonScanner"/> tracks checkboxes by their full id: a standalone checkbox in
        /// the same panel can share a stacked checkbox's name.
        /// </remarks>
        public IEnumerable<string> ScannerKeys(IEnumerable<string> shownCheckBoxIds)
        {
            return _visibleChildren
                .Where(child => !IsCheckBox(child))
                .Select(child => child.DisplayName)
                .Concat(shownCheckBoxIds);
        }

        private static bool IsCheckBox(ParsedComponent component)
        {
            return component.Type == CommandComponentType.CheckBox;
        }
    }
}
