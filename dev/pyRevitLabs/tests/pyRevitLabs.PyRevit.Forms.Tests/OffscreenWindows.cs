#nullable enable
using System;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Windows;

namespace PyRevitLabs.PyRevit.Forms.Testing;

/// <summary>Keeps every WPF window a test opens off the developer's desktop and out of their focus.</summary>
/// <remarks>
/// Tests assert on WPF state (event routing, dispatcher behaviour, visibility, results), never on pixels,
/// focus or activation, so a real window moved off-screen exercises the same code as one on the desktop.
/// <see cref="FrameworkElement.SizeChangedEvent"/> is the earliest routed event a <see cref="Window"/> raises:
/// it fires after the HWND exists and before it is first shown, so the window never appears on screen.
/// Windows that place themselves, such as <c>CenterScreen</c> dialogs, a <c>Topmost</c> stop window or a
/// prompt bar that sizes itself to the Revit window, are overridden because the handler runs after their
/// constructors. A window that moves back later, as a prompt bar was seen doing under .NET Framework, is
/// returned from <see cref="Window.LocationChanged"/>.
/// </remarks>
public static class OffscreenWindows {
    const double FarOffscreen = -32000;

    static readonly ConditionalWeakTable<Window, object> Tracked = new();
    static readonly object Marker = new();

    static int installed;

    /// <summary>Registers the process-wide handler. Safe to call more than once and from any thread.</summary>
    /// <remarks>Call before the first test window is created.</remarks>
    public static void Install() {
        if (Interlocked.Exchange(ref installed, 1) != 0) {
            return;
        }
        EventManager.RegisterClassHandler(typeof(Window), FrameworkElement.SizeChangedEvent, new RoutedEventHandler(OnSizeChanged));
    }

    static void OnSizeChanged(object sender, RoutedEventArgs args) {
        var window = (Window)sender;
        if (!Tracked.TryGetValue(window, out _)) {
            Tracked.Add(window, Marker);
            window.LocationChanged += OnLocationChanged;
        }
        MoveOffscreen(window);
    }

    static void OnLocationChanged(object? sender, EventArgs args) {
        MoveOffscreen((Window)sender!);
    }

    static void MoveOffscreen(Window window) {
        if (window.Left == FarOffscreen && window.Top == FarOffscreen) {
            return;
        }
        window.ShowActivated = false;
        window.ShowInTaskbar = false;
        window.WindowStartupLocation = WindowStartupLocation.Manual;
        window.Left = FarOffscreen;
        window.Top = FarOffscreen;
    }
}
