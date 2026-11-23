using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Runtime.CompilerServices;

namespace PyRevitLoader
{
    /// <summary>
    /// Keeps the change handlers a <see cref="CheckBoxExecutor"/> wired to checkbox controls, and
    /// keeps alive what each handler needs for as long as its control lives.
    /// </summary>
    /// <remarks>
    /// Important: keep this class free of IronPython, Revit API and AdWindows types; the tests compile
    /// it in to check the handler bookkeeping without Revit.
    /// </remarks>
    internal sealed class CheckBoxHandlerRegistry
    {
        private static readonly object _aliveReferencesLock = new object();
        private static readonly ConditionalWeakTable<INotifyPropertyChanged, List<object>> _aliveReferences =
            new ConditionalWeakTable<INotifyPropertyChanged, List<object>>();

        private readonly List<KeyValuePair<INotifyPropertyChanged, PropertyChangedEventHandler>> _wiredHandlers =
            new List<KeyValuePair<INotifyPropertyChanged, PropertyChangedEventHandler>>();
        private bool _released;

        /// <summary>
        /// Gets whether <see cref="Release"/> has run, after which nothing is wired.
        /// </summary>
        public bool IsReleased => _released;

        /// <summary>
        /// Removes the handler wired on <paramref name="checkBox"/> for an earlier bundle, if any.
        /// </summary>
        /// <returns>True when a handler was removed.</returns>
        public bool DetachEarlier(INotifyPropertyChanged checkBox)
        {
            lock (_aliveReferencesLock)
            {
                var earlier = _wiredHandlers.FindIndex(wired => ReferenceEquals(wired.Key, checkBox));
                if (earlier < 0)
                    return false;

                checkBox.PropertyChanged -= _wiredHandlers[earlier].Value;
                _wiredHandlers.RemoveAt(earlier);
                _aliveReferences.Remove(checkBox);
                return true;
            }
        }

        /// <summary>
        /// Subscribes <paramref name="handler"/> to <paramref name="checkBox"/> and keeps it and
        /// <paramref name="aliveReferences"/> alive while the control lives.
        /// </summary>
        /// <returns>False, subscribing nothing, once the registry is released.</returns>
        public bool Wire(INotifyPropertyChanged checkBox, PropertyChangedEventHandler handler, params object[] aliveReferences)
        {
            lock (_aliveReferencesLock)
            {
                if (_released)
                    return false;

                checkBox.PropertyChanged += handler;
                _wiredHandlers.Add(new KeyValuePair<INotifyPropertyChanged, PropertyChangedEventHandler>(checkBox, handler));
                var keptAlive = _aliveReferences.GetOrCreateValue(checkBox);
                keptAlive.Clear();
                keptAlive.AddRange(aliveReferences);
                keptAlive.Add(handler);
                return true;
            }
        }

        /// <summary>
        /// Detaches every handler, drops what it kept alive and refuses later wiring.
        /// </summary>
        /// <param name="onError">Receives each handler that failed to detach; the others are still detached,
        /// even when it throws.</param>
        public void Release(Action<string> onError)
        {
            lock (_aliveReferencesLock)
            {
                _released = true;

                foreach (var wired in _wiredHandlers)
                {
                    try
                    {
                        wired.Key.PropertyChanged -= wired.Value;
                    }
                    catch (Exception ex)
                    {
                        ReportWithoutThrowing(onError, $"Failed to detach CheckBox handler: {ex.Message}");
                    }
                    _aliveReferences.Remove(wired.Key);
                }
                _wiredHandlers.Clear();
            }
        }

        private static void ReportWithoutThrowing(Action<string> onError, string message)
        {
            try
            {
                onError?.Invoke(message);
            }
            catch (Exception)
            {
            }
        }
    }
}
