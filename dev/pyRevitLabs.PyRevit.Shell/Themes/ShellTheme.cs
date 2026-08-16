using System.Windows;
using System.Windows.Media;

namespace PyRevitLabs.PyRevit.Shell {
    /// <summary>
    /// Applies the light or dark shell palette below a visual root.
    /// </summary>
    internal static class ShellTheme {
        public static void Apply(FrameworkElement root, bool useDarkTheme) {
            Set(root, "ShellBarBackground", useDarkTheme, 0x2A3847, 0xF0F0F0);
            Set(root, "ShellBarForeground", useDarkTheme, 0xD4D4D4, 0x1E1E1E);
            Set(root, "ShellSplitterBackground", useDarkTheme, 0x2A3847, 0xE0E0E0);
            Set(root, "ShellRunGlyph", useDarkTheme, 0x6CC26C, 0x3D9142);
            Set(root, "ShellScrollTrack", useDarkTheme, 0x1F2D3D, 0xF5F5F5);
            Set(root, "ShellScrollThumb", useDarkTheme, 0x46586B, 0xC8C8C8);
            Set(root, "ShellScrollThumbHover", useDarkTheme, 0x5C7188, 0xA0A0A0);
            Set(root, "ShellTitleBarBackground", useDarkTheme, 0x16202C, 0xF0F0F0);
            Set(root, "ShellTitleBarForeground", useDarkTheme, 0xD4D4D4, 0x1E1E1E);
            Set(root, "ShellTitleBarButtonHover", useDarkTheme, 0x2A3847, 0xD9D9D9);
            Set(root, "ShellTitleBarButtonPressed", useDarkTheme, 0x39495C, 0xC8C8C8);
            Set(root, SystemColors.ControlBrushKey, useDarkTheme, 0x1F2D3D, 0xF5F5F5);
        }

        static void Set(FrameworkElement root, object key, bool useDarkTheme, int dark, int light) {
            int rgb = useDarkTheme ? dark : light;
            var brush = new SolidColorBrush(Color.FromRgb(
                (byte)(rgb >> 16), (byte)(rgb >> 8), (byte)rgb));
            brush.Freeze();
            root.Resources[key] = brush;
        }
    }
}
