using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using pyRevitLabs.PyRevit;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Dispatcher-bound overlay compositor. SetCurrentValue preserves binding and resource
    /// expressions; restoration never replaces a value another add-in installed.
    /// </summary>
    internal sealed class AgentTabHighlightVisuals : IAgentTabHighlightVisuals, IDisposable {
        private sealed class TabValues {
            internal AgentTabHighlightValue Style;
            internal AgentTabHighlightValue Tooltip;
        }

        private readonly Dispatcher dispatcher;
        private readonly Dictionary<long, Func<IEnumerable<TabItem>>> tabs = new Dictionary<long, Func<IEnumerable<TabItem>>>();
        private readonly Dictionary<long, Dictionary<TabItem, TabValues>> values = new Dictionary<long, Dictionary<TabItem, TabValues>>();
        internal Action Refresh;
        internal Action<Exception> VisualFailure;

        internal AgentTabHighlightVisuals(Dispatcher dispatcher) {
            this.dispatcher = dispatcher;
            TabColoringTheme.TabStylesChanging += OnTabStylesChanging;
        }

        internal void Register(UIApplication application, Document document, long key) {
            dispatcher.VerifyAccess();
            tabs[key] = () => DocumentTabLocator.FindTabs(application, document);
        }

        internal void Schedule(int milliseconds, Action callback) {
            dispatcher.VerifyAccess();
            var timer = new DispatcherTimer(DispatcherPriority.Normal, dispatcher) {
                Interval = TimeSpan.FromMilliseconds(milliseconds)
            };
            timer.Tick += (sender, args) => {
                timer.Stop();
                callback();
            };
            timer.Start();
        }

        /// <summary>Refreshes native-identity matches, restores departed tabs and overlays every current tab.</summary>
        /// <param name="documentKey">The registered native document identity.</param>
        /// <param name="tooltip">The label applied to every current document tab.</param>
        /// <returns>Whether the document currently has any matching tabs.</returns>
        public bool Apply(long documentKey, string tooltip) {
            dispatcher.VerifyAccess();
            if (!tabs.TryGetValue(documentKey, out var findTabs))
                return false;
            var documentTabs = new HashSet<TabItem>(findTabs());
            if (!values.TryGetValue(documentKey, out var documentValues)) {
                documentValues = new Dictionary<TabItem, TabValues>();
                values.Add(documentKey, documentValues);
            }
            foreach (var tab in documentValues.Keys.Where(tab => !documentTabs.Contains(tab)).ToArray()) {
                Restore(documentValues[tab]);
                documentValues.Remove(tab);
            }
            foreach (var tab in documentTabs) {
                if (!documentValues.TryGetValue(tab, out var entry)) {
                    entry = new TabValues {
                        Style = Capture(tab, FrameworkElement.StyleProperty),
                        Tooltip = Capture(tab, FrameworkElement.ToolTipProperty)
                    };
                    documentValues.Add(tab, entry);
                    var style = new Style(tab.GetType(), tab.Style);
                    style.Setters.Add(new Setter(TabItem.BackgroundProperty, PyRevitConsts.PyRevitAccentBrush));
                    style.Setters.Add(new Setter(TabItem.ForegroundProperty, Brushes.Black));
                    for (var selected = 0; selected < 2; selected++) {
                        var trigger = new Trigger { Property = TabItem.IsSelectedProperty, Value = selected == 1 };
                        trigger.Setters.Add(new Setter(TabItem.BackgroundProperty, PyRevitConsts.PyRevitAccentBrush));
                        trigger.Setters.Add(new Setter(TabItem.ForegroundProperty, Brushes.Black));
                        style.Triggers.Add(trigger);
                    }
                    entry.Style.Apply(style);
                }
                entry.Tooltip.Apply(tooltip);
            }
            if (documentTabs.Count == 0)
                return false;
            dispatcher.Invoke(DispatcherPriority.Render, new Action(() => { }));
            return true;
        }

        private static AgentTabHighlightValue Capture(TabItem tab, DependencyProperty property) {
            var original = tab.GetValue(property);
            var unset = tab.ReadLocalValue(property) == DependencyProperty.UnsetValue;
            return new AgentTabHighlightValue(() => tab.GetValue(property),
                value => tab.SetCurrentValue(property, value),
                () => {
                    if (unset)
                        tab.ClearValue(property);
                    else
                        tab.SetCurrentValue(property, original);
                });
        }

        /// <summary>Restores only properties whose current values are still owned by this adapter.</summary>
        public void Restore(long documentKey) {
            dispatcher.VerifyAccess();
            if (!values.TryGetValue(documentKey, out var documentValues))
                return;
            Exception failure = null;
            foreach (var entry in documentValues.Values) {
                try { Restore(entry); }
                catch (Exception exception) { failure = exception; }
            }
            if (failure != null)
                throw failure;
            values.Remove(documentKey);
        }

        private static void Restore(TabValues entry) {
            try { entry.Style.Restore(); }
            finally { entry.Tooltip.Restore(); }
        }

        /// <summary>Releases tab references after the last lease and visibility delay end.</summary>
        public void Forget(long key) {
            tabs.Remove(key);
        }

        private void OnTabStylesChanging(bool before) {
            try {
                dispatcher.VerifyAccess();
                if (before) {
                    foreach (var key in values.Keys.ToArray())
                        Restore(key);
                }
                else
                    Refresh?.Invoke();
            }
            catch (Exception exception) {
                VisualFailure?.Invoke(exception);
            }
        }

        /// <summary>Detaches the colorizer hook and removes owned overlays on the window dispatcher.</summary>
        public void Dispose() {
            if (!dispatcher.CheckAccess()) {
                dispatcher.Invoke(new Action(Dispose));
                return;
            }
            TabColoringTheme.TabStylesChanging -= OnTabStylesChanging;
            foreach (var key in values.Keys.ToArray()) {
                try { Restore(key); }
                catch { }
            }
            tabs.Clear();
        }
    }
}
