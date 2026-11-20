#nullable enable
using System;
using System.Collections.Generic;
using System.Windows.Threading;
using Autodesk.Windows;
using pyRevitAssemblyBuilder.SessionManager;
using UIFramework;
using UIFrameworkServices;

namespace pyRevitAssemblyBuilder.UIManager
{
    /// <summary>
    /// Registers keyboard shortcuts for ribbon buttons through Revit's internal shortcut services.
    /// </summary>
    /// <remarks>
    /// <para>Requests are queued and applied in a single batch on the ribbon dispatcher at
    /// <see cref="DispatcherPriority.ApplicationIdle"/>, after the ribbon items exist.</para>
    /// <para>Shortcuts rejected by <see cref="ShortcutKeyManager.IsLegalShortcutKey"/> are skipped and logged
    /// at Warning, since an illegal entry saved into Revit's shortcut table triggers an "Import Errors" dialog on the next start.</para>
    /// <para>Important: a shortcut already assigned to another command is never overridden; it is
    /// skipped and logged. The first button to claim a shortcut within a batch wins.</para>
    /// </remarks>
    internal sealed class ShortcutRegistrar
    {
        private readonly ILogger _logger;
        private readonly object _gate = new object();
        private readonly List<PendingShortcuts> _pending = new List<PendingShortcuts>();
        private bool _flushScheduled;

        public ShortcutRegistrar(ILogger logger)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
        }

        public void Enqueue(string itemId, string buttonName, IReadOnlyList<string> shortcuts)
        {
            if (string.IsNullOrEmpty(itemId) || shortcuts.Count == 0)
                return;

            lock (_gate)
            {
                _pending.Add(new PendingShortcuts(itemId, buttonName, shortcuts));
                if (_flushScheduled)
                    return;
                _flushScheduled = true;
            }

            var dispatcher = ComponentManager.Ribbon?.Dispatcher ?? Dispatcher.CurrentDispatcher;
            dispatcher.InvokeAsync(Flush, DispatcherPriority.ApplicationIdle);
        }

        private void Flush()
        {
            List<PendingShortcuts> batch;
            lock (_gate)
            {
                batch = new List<PendingShortcuts>(_pending);
                _pending.Clear();
                _flushScheduled = false;
            }

            if (batch.Count == 0)
                return;

            try
            {
                Apply(batch);
            }
            catch (Exception ex)
            {
                _logger.Debug($"Failed to register keyboard shortcuts. Exception: {ex.Message}");
            }
        }

        private void Apply(List<PendingShortcuts> batch)
        {
            if (NeedsCommandReload(batch))
                ShortcutsHelper.LoadCommands();

            var commands = ShortcutsHelper.Commands;
            var usedShortcuts = CollectUsedShortcuts(commands);
            var applyDict = new Dictionary<string, ShortcutItem>();

            foreach (var request in batch)
            {
                if (!commands.TryGetValue(request.ItemId, out var command))
                {
                    _logger.Debug($"Cannot register shortcuts for '{request.ButtonName}': Revit has no command '{request.ItemId}'.");
                    continue;
                }

                var added = false;
                foreach (var shortcut in request.Shortcuts)
                {
                    if (!ShortcutKeyManager.IsLegalShortcutKey(shortcut))
                    {
                        _logger.Warning($"Shortcut '{shortcut}' for button '{request.ButtonName}' is not a valid Revit shortcut and was skipped.");
                        continue;
                    }

                    if (ContainsShortcut(command.Shortcuts, shortcut))
                        continue;

                    if (!usedShortcuts.Add(shortcut))
                    {
                        _logger.Debug($"Shortcut '{shortcut}' for button '{request.ButtonName}' is already assigned to another command and was skipped.");
                        continue;
                    }

                    command.Shortcuts.Add(shortcut);
                    added = true;
                }

                if (added)
                    applyDict[request.ItemId] = CreateApplyItem(command);
            }

            if (applyDict.Count > 0)
                KeyboardShortcutService.applyShortcutChanges(applyDict);
        }

        /// <summary>
        /// Builds the throwaway <see cref="ShortcutItem"/> passed to
        /// <see cref="KeyboardShortcutService.applyShortcutChanges"/> for a single command.
        /// </summary>
        /// <remarks>
        /// <para>applyShortcutChanges reconciles the passed items against Revit's native shortcut
        /// array and MUTATES the Shortcuts lists it receives: a native key found in the passed
        /// list is consumed (matched, native binding kept); a native key missing from the passed
        /// list is treated as stale and its native binding is repurposed or deleted. Passing the
        /// live master item therefore strips already-native keys (e.g. a user's manual shortcut)
        /// out of the master list, which the next dialog save then erases from
        /// KeyboardShortcuts.xml.</para>
        /// <para>The copy is seeded from the master item (which already contains the newly added
        /// key) and then unioned with the keys currently bound natively, obtained via
        /// <see cref="KeyboardShortcutService.getShortcutRep"/>. Keys that exist natively but are
        /// missing from the master list — e.g. leftovers from earlier appends — are also restored
        /// to the master list so the next dialog save persists them.</para>
        /// </remarks>
        private ShortcutItem CreateApplyItem(ShortcutItem command)
        {
            var item = new ShortcutItem(command);

            var nativeRep = KeyboardShortcutService.getShortcutRep(command.CommandId);
            if (!string.IsNullOrEmpty(nativeRep))
            {
                foreach (var nativeKey in nativeRep.Split('#'))
                {
                    if (string.IsNullOrEmpty(nativeKey))
                        continue;

                    if (!ContainsShortcut(item.Shortcuts, nativeKey))
                        item.Shortcuts.Add(nativeKey);

                    if (!ContainsShortcut(command.Shortcuts, nativeKey))
                    {
                        command.Shortcuts.Add(nativeKey);
                        _logger.Debug($"Restored native shortcut '{nativeKey}' to the master list of command '{command.CommandId}'.");
                    }
                }
            }

            return item;
        }

        private static bool ContainsShortcut(IEnumerable<string> shortcuts, string shortcut)
        {
            foreach (var existing in shortcuts)
            {
                if (string.Equals(existing, shortcut, StringComparison.OrdinalIgnoreCase))
                    return true;
            }

            return false;
        }

        private static bool NeedsCommandReload(List<PendingShortcuts> batch)
        {
            var commands = ShortcutsHelper.Commands;
            if (commands.Count == 0)
                return true;

            foreach (var request in batch)
            {
                if (!commands.ContainsKey(request.ItemId))
                    return true;
            }

            return false;
        }

        private static HashSet<string> CollectUsedShortcuts(Dictionary<string, ShortcutItem> commands)
        {
            var used = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var command in commands.Values)
            {
                if (command.Shortcuts == null)
                    continue;

                foreach (var shortcut in command.Shortcuts)
                    used.Add(shortcut);
            }

            return used;
        }

        private sealed class PendingShortcuts
        {
            public PendingShortcuts(string itemId, string buttonName, IReadOnlyList<string> shortcuts)
            {
                ItemId = itemId;
                ButtonName = buttonName;
                Shortcuts = shortcuts;
            }

            public string ItemId { get; }
            public string ButtonName { get; }
            public IReadOnlyList<string> Shortcuts { get; }
        }
    }
}
