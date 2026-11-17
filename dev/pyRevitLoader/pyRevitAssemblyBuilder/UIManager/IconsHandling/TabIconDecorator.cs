#nullable enable
using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using Autodesk.Windows;

namespace pyRevitAssemblyBuilder.UIManager.Icons
{
    /// <summary>
    /// Draws a tab icon by inserting an <see cref="Image"/> into the AdWindows tab header.
    /// </summary>
    /// <remarks>
    /// AdWindows has no tab image property. Each tab header is a <c>RibbonTabButton</c> generated
    /// from the <c>RibbonTabTemplate</c> data template, whose content is a horizontal
    /// <see cref="StackPanel"/> holding the title <see cref="TextBlock"/>.
    /// Invariant: AdWindows regenerates and may reuse tab headers (theme switches, tab overflow),
    /// so headers are decorated from a process-wide <see cref="FrameworkElement.LoadedEvent"/>
    /// class handler and on <see cref="FrameworkElement.DataContextChanged"/>, not just once. That
    /// handler cannot be unregistered, so it routes to the decorator of the current session, the
    /// last one <see cref="Reset"/> was called on.
    /// </remarks>
    public sealed class TabIconDecorator : ITabIconDecorator
    {
        private const double IconSize = 14;

        private static readonly object IconMarker = new object();
        private static readonly ConditionalWeakTable<ButtonBase, object> WatchedHeaders =
            new ConditionalWeakTable<ButtonBase, object>();
        private static TabIconDecorator? _active;
        private static bool _classHandlerRegistered;

        private readonly Func<string, BitmapSource?> _loadBitmap;
        private readonly Func<bool> _isDarkTheme;
        private readonly Dictionary<RibbonTab, TabIcons> _iconsByTab = new Dictionary<RibbonTab, TabIcons>();
        private bool _darkTheme;

        /// <summary>
        /// Initializes a new instance of the <see cref="TabIconDecorator"/> class.
        /// </summary>
        /// <param name="loadBitmap">Loads an icon file; returns <c>null</c> when it cannot.</param>
        /// <param name="isDarkTheme">Reports the current Revit theme; read on <see cref="RefreshHeaders"/>.</param>
        public TabIconDecorator(Func<string, BitmapSource?> loadBitmap, Func<bool> isDarkTheme)
        {
            _loadBitmap = loadBitmap ?? throw new ArgumentNullException(nameof(loadBitmap));
            _isDarkTheme = isDarkTheme ?? throw new ArgumentNullException(nameof(isDarkTheme));
        }

        /// <inheritdoc/>
        public void Reset()
        {
            EnsureClassHandler();
            _active = this;
            _iconsByTab.Clear();
        }

        /// <inheritdoc/>
        public string? GetIconSource(RibbonTab tab) =>
            tab != null && _iconsByTab.TryGetValue(tab, out var icons) ? icons.Source : null;

        /// <inheritdoc/>
        public bool TryAddIcons(RibbonTab tab, string iconSource, string? lightIconPath, string? darkIconPath)
        {
            if (tab == null || _iconsByTab.ContainsKey(tab))
                return false;

            var light = Load(lightIconPath);
            var dark = Load(darkIconPath);
            if (light == null && dark == null)
                return false;

            _iconsByTab[tab] = new TabIcons(iconSource, light, dark);
            return true;
        }

        /// <inheritdoc/>
        public void RefreshHeaders()
        {
            RibbonThemeRegistry.Register(this, ApplyTheme);
            _darkTheme = _isDarkTheme();
            DecorateLiveHeaders();
        }

        private void ApplyTheme(bool isDarkTheme)
        {
            _darkTheme = isDarkTheme;
            DecorateLiveHeaders();
        }

        private void DecorateLiveHeaders()
        {
            if (ComponentManager.Ribbon is DependencyObject ribbon)
            {
                foreach (var button in FindVisualDescendants<ButtonBase>(ribbon))
                    Decorate(button);
            }
        }

        private BitmapSource? Load(string? path) => string.IsNullOrEmpty(path) ? null : _loadBitmap(path!);

        private static void EnsureClassHandler()
        {
            if (_classHandlerRegistered)
                return;
            EventManager.RegisterClassHandler(
                typeof(ButtonBase),
                FrameworkElement.LoadedEvent,
                new RoutedEventHandler((sender, _) => _active?.Decorate(sender as ButtonBase)));
            _classHandlerRegistered = true;
        }

        private void Decorate(ButtonBase? button)
        {
            if (button?.DataContext is not RibbonTab tab)
                return;

            WatchForReuse(button);

            if (button.Content is not StackPanel header)
                return;

            var existing = header.Children.OfType<Image>().FirstOrDefault(i => i.Tag == IconMarker);
            var source = _iconsByTab.TryGetValue(tab, out var icons) ? icons.For(_darkTheme) : null;

            if (source == null)
            {
                if (existing != null)
                    header.Children.Remove(existing);
                return;
            }

            if (existing == null)
            {
                existing = new Image
                {
                    Tag = IconMarker,
                    Width = IconSize,
                    Height = IconSize,
                    Stretch = Stretch.Uniform,
                    VerticalAlignment = VerticalAlignment.Center,
                    Margin = new Thickness(0, 1, 4, 1),
                    UseLayoutRounding = true,
                };
                RenderOptions.SetBitmapScalingMode(existing, BitmapScalingMode.HighQuality);
                header.Children.Insert(0, existing);
            }

            existing.Source = source;
        }

        private static void WatchForReuse(ButtonBase button)
        {
            if (WatchedHeaders.TryGetValue(button, out _))
                return;
            WatchedHeaders.Add(button, IconMarker);
            button.DataContextChanged += (sender, _) => _active?.Decorate(sender as ButtonBase);
        }

        private static IEnumerable<T> FindVisualDescendants<T>(DependencyObject root) where T : DependencyObject
        {
            var pending = new Stack<DependencyObject>();
            pending.Push(root);
            while (pending.Count > 0)
            {
                var current = pending.Pop();
                var count = VisualTreeHelper.GetChildrenCount(current);
                for (var i = 0; i < count; i++)
                {
                    var child = VisualTreeHelper.GetChild(current, i);
                    if (child is T match)
                        yield return match;
                    pending.Push(child);
                }
            }
        }

        private sealed class TabIcons
        {
            private readonly BitmapSource? _light;
            private readonly BitmapSource? _dark;

            public string Source { get; }

            public TabIcons(string source, BitmapSource? light, BitmapSource? dark)
            {
                Source = source;
                _light = light;
                _dark = dark;
            }

            public BitmapSource? For(bool isDarkTheme) => isDarkTheme ? _dark ?? _light : _light ?? _dark;
        }
    }
}
