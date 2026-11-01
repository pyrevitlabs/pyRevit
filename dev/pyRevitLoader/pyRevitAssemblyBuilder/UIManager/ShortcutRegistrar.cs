#nullable enable
using System;
using System.Collections.Generic;
using System.Windows.Threading;
using Autodesk.Windows;
using pyRevitAssemblyBuilder.SessionManager;
using UIFramework;
using UIFrameworkServices;

namespace pyRevitAssemblyBuilder.UIManager.Buttons
{
    /// <summary>
    /// Registers keyboard shortcuts for ribbon buttons through Revit's internal shortcut services.
    /// </summary>
    /// <remarks>
    /// <para>Requests are queued and applied in a single batch on the ribbon dispatcher at
    /// <see cref="DispatcherPriority.ApplicationIdle"/>, after the ribbon items exist.</para>
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
            var changedCommands = new Dictionary<string, ShortcutItem>();

            foreach (var request in batch)
            {
                if (!commands.TryGetValue(request.ItemId, out var command))
                {
                    _logger.Debug($"Cannot register shortcuts for '{request.ButtonName}': Revit has no command '{request.ItemId}'.");
                    continue;
                }

                foreach (var shortcut in request.Shortcuts)
                {
                    if (OwnsShortcut(command, shortcut))
                        continue;

                    if (!usedShortcuts.Add(shortcut))
                    {
                        _logger.Debug($"Shortcut '{shortcut}' for button '{request.ButtonName}' is already assigned to another command and was skipped.");
                        continue;
                    }

                    command.Shortcuts.Add(shortcut);
                    changedCommands[request.ItemId] = command;
                }
            }

            if (changedCommands.Count > 0)
                KeyboardShortcutService.applyShortcutChanges(changedCommands);
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

        private static bool OwnsShortcut(ShortcutItem command, string shortcut)
        {
            foreach (var existing in command.Shortcuts)
            {
                if (string.Equals(existing, shortcut, StringComparison.OrdinalIgnoreCase))
                    return true;
            }

            return false;
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
