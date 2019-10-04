using System;
using System.Drawing;
using System.Globalization;
using System.Windows.Data;

namespace pyRevitLabs.CommonWPF.Converters
{
    public class BitmapToImageSourceConverter : IValueConverter
    {
        private static readonly Lazy<BitmapToImageSourceConverter> InstanceObj =
           new Lazy<BitmapToImageSourceConverter>(() => new BitmapToImageSourceConverter());

        public static BitmapToImageSourceConverter Instance
        {
            get { return InstanceObj.Value; }
        }

        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            var bmp = value as Bitmap;
            if (bmp is null)
            {
                var defaultBmp = parameter as Bitmap;
                if (defaultBmp != null)
                    return BitmapSourceConverter.ConvertFromImage(defaultBmp);
            }

            return bmp is null ? null : BitmapSourceConverter.ConvertFromImage(bmp);
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw new NotSupportedException();
        }
    }
}