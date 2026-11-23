using System;
using System.Windows;
using Autodesk.Revit.UI;

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>
    /// Owns a native WPF page for a Revit dockable pane without requiring a Python-generated CLR type.
    /// </summary>
    public sealed class DockablePaneProvider : IDockablePaneProvider {
        private readonly FrameworkElement _frameworkElement;

        /// <summary>
        /// Initializes a provider for an already-created WPF page.
        /// </summary>
        /// <param name="frameworkElement">The page Revit hosts in its dockable-pane chrome.</param>
        /// <param name="visibleByDefault">Whether Revit should show the pane after registration.</param>
        /// <exception cref="ArgumentNullException">Thrown when <paramref name="frameworkElement"/> is null.</exception>
        public DockablePaneProvider(FrameworkElement frameworkElement, bool visibleByDefault) {
            _frameworkElement = frameworkElement ?? throw new ArgumentNullException(nameof(frameworkElement));
            VisibleByDefault = visibleByDefault;
        }

        /// <summary>
        /// Gets or sets Revit's initial docking state for the pane.
        /// </summary>
        public DockablePaneState InitialState { get; set; }

        /// <summary>
        /// Gets or sets the editor interaction policy for the pane.
        /// </summary>
        public EditorInteraction EditorInteraction { get; set; }

        /// <summary>
        /// Gets or sets the contextual help displayed by Revit for the pane.
        /// </summary>
        public ContextualHelp ContextualHelp { get; set; }

        /// <summary>
        /// Gets whether Revit should show the pane after registration.
        /// </summary>
        public bool VisibleByDefault { get; }

        /// <summary>
        /// Supplies the native page and optional pane settings during Revit registration.
        /// </summary>
        /// <param name="data">The Revit registration data to populate.</param>
        /// <exception cref="ArgumentNullException">Thrown when <paramref name="data"/> is null.</exception>
        public void SetupDockablePane(DockablePaneProviderData data) {
            if (data == null)
                throw new ArgumentNullException(nameof(data));

            data.FrameworkElement = _frameworkElement;
            data.VisibleByDefault = VisibleByDefault;
            if (InitialState != null)
                data.InitialState = InitialState;
            if (EditorInteraction != null)
                data.EditorInteraction = EditorInteraction;
            if (ContextualHelp != null)
                data.ContextualHelp = ContextualHelp;
        }
    }
}
