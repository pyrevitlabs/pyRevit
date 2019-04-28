using System;
using System.Drawing;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media.Imaging;


namespace pyRevitLabs.CommonWPF.Converters {
    public class BitmapSourceConverter {
        [System.Runtime.InteropServices.DllImport("gdi32.dll")]
        private static extern bool DeleteObject(IntPtr hObject);

        public static BitmapSource ConvertFromImage(Bitmap image) {
            lock (image) {
                IntPtr hBitmap = image.GetHbitmap();
                try {
                    var bs = Imaging.CreateBitmapSourceFromHBitmap(
                        hBitmap,
                        IntPtr.Zero,
                        Int32Rect.Empty,
                        BitmapSizeOptions.FromEmptyOptions());

                    return bs;
                }
                finally {
                    var res = DeleteObject(hBitmap);
                }
            }
        }

        public static BitmapSource ConvertFromIcon(Icon icon) {

            try {
                var bs = Imaging
                    .CreateBitmapSourceFromHIcon(icon.Handle,
                                                 new Int32Rect(0, 0, icon.Width, icon.Height),
                                                 BitmapSizeOptions.FromWidthAndHeight(icon.Width,
                                                                                      icon.Height));
                return bs;
            }
            finally {
                DeleteObject(icon.Handle);
                icon.Dispose();
                icon = null;
            }
        }
    }
}