using System;
using System.Diagnostics;
using System.Windows;
using System.Windows.Forms;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Collections;
using System.Collections.Generic;

using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB.Events;
using Autodesk.Revit.UI.Events;
using System.IO;

namespace PyRevitBaseClasses
{
    //public static class HostApp
    //{
    //    public static Screen HostAppScreen
    //    {
    //        get
    //        {
    //            return Screen.FromHandle(Process.GetCurrentProcess().MainWindowHandle);
    //        }
    //    }

    //    public static double HostAppScreenScaling
    //    {
    //        get
    //        {
    //            Screen appScreen = HostAppScreen;
    //            if (appScreen != null)
    //            {
    //                double actualWidth = SystemParameters.PrimaryScreenWidth;
    //                double scaledWidth = Screen.PrimaryScreen.WorkingArea.Width;
    //                return Math.Abs(scaledWidth / actualWidth);
    //            }

    //            return 1.0;
    //        }
    //    }
    //}


    //public static class PyRevitButtonIconSizes
    //{
    //    public static int small = 16;
    //    public static int medium = 24;
    //    public static int large = 32;

    //    public static int defaultDPI = 96;
    //}


    //public class PyRevitButtonIcon
    //{
    //    private string _iconFilePath = null;
    //    private int _largeIconSize = 32;

    //    public PyRevitButtonIcon(string iconPath, int largeSize)
    //    {
    //        _iconFilePath = iconPath;
    //        _largeIconSize = largeSize;
    //    }

    //    private BitmapSource CreateBitmap(string iconPath, int iconSize)
    //    {
    //        int adjustedIconSize = iconSize * 2;
    //        int adjusted_dpi = PyRevitButtonIconSizes.defaultDPI * 2;

    //        double screenScaling = HostApp.HostAppScreenScaling;

    //        var baseImage = new BitmapImage();
    //        baseImage.BeginInit();
    //        baseImage.UriSource = new Uri(iconPath);
    //        baseImage.DecodePixelHeight = Convert.ToInt32(adjustedIconSize * screenScaling);
    //        baseImage.EndInit();

    //        int imageSize = baseImage.PixelWidth;
    //        PixelFormat imageFormat = baseImage.Format;
    //        int imageBytePerPixel = baseImage.Format.BitsPerPixel / 8;

    //        int stride = imageSize * imageBytePerPixel;
    //        int array_size = stride * imageSize;
    //        Byte[] image_data = new Byte[array_size];
    //        baseImage.CopyPixels(image_data, stride, 0);

    //        BitmapSource iconSource =
    //            BitmapSource.Create(Convert.ToInt32(adjustedIconSize * screenScaling),
    //                                Convert.ToInt32(adjustedIconSize * screenScaling),
    //                                adjusted_dpi * screenScaling,
    //                                adjusted_dpi * screenScaling,
    //                                imageFormat,
    //                                null,
    //                                image_data,
    //                                stride);
    //        return iconSource;
    //    }

    //    //def recolour(image_data, size, stride, color):
    //    //# _ButtonIcons.recolour(image_data, image_size, stride, 0x8e44ad)
    //    //step = stride / size
    //    //for i in range(0, stride, step):
    //    //    for j in range(0, stride, step):
    //    //        idx = (i* size) + j
    //    //# R = image_data[idx+2]
    //    //# G = image_data[idx+1]
    //    //# B = image_data[idx]
    //    //# luminance = (0.299*R + 0.587*G + 0.114*B)
    //    //                image_data[idx] = color >> 0 & 0xff       # blue
    //    //                image_data[idx + 1] = color >> 8 & 0xff     # green
    //    //                image_data[idx + 2] = color >> 16 & 0xff    # red


    //    public BitmapSource SmallIcon
    //    {
    //        get
    //        {
    //            return CreateBitmap(this._iconFilePath, PyRevitButtonIconSizes.small);
    //        }
    //    }

    //    public BitmapSource LargeIcon
    //    {
    //        get
    //        {
    //            return CreateBitmap(this._iconFilePath, this._largeIconSize);
    //        }
    //    }
    //}

    public class UIDocUtils {
        private bool _txnCompleted = false;
        private Document _doc = null;
        private string _txnName = null;
        private BuiltInParameter _paramToUpdate;
        private string _paramToUpdateStringValue = null;

        public UIApplication App { get; private set; }
        public List<ElementId> NewElements { get; private set; }

        public UIDocUtils(UIApplication app) {
            if (app != null) {
                App = app;
                NewElements = new List<ElementId>();
            }
            else
                throw new Exception("Application can not be null.");
        }

        private void OnDocumentChanged(object sender, DocumentChangedEventArgs e) {
            NewElements.AddRange(e.GetAddedElementIds());
        }

        private void CancelAllDialogs(object sender, DialogBoxShowingEventArgs e) {
            if (e.Cancellable)
                e.Cancel();
            else
                e.OverrideResult(1);
        }

        private void NewElementPropertyValueUpdater(object sender, IdlingEventArgs e) {
            // cancel if txn is completed
            if(_txnCompleted) {
                App.Idling -= new EventHandler<IdlingEventArgs>(NewElementPropertyValueUpdater);
                EndCancellingAllDialogs();
                EndTrackingElements();
            }

            // now update element parameters
            try {
                var TXN = new Transaction(_doc, _txnName);
                TXN.Start();
                foreach (var newElId in NewElements) {
                    var element = _doc.GetElement(newElId);
                    if (element != null) {
                        var parameter = element.get_Parameter(_paramToUpdate);
                        if (parameter != null && !parameter.IsReadOnly)
                            parameter.Set(_paramToUpdateStringValue);
                    }
                }
                TXN.Commit();
            } catch (Exception ex) {
            }

            _txnCompleted = true;
        }

        public void StartTrackingElements() {
            App.Application.DocumentChanged += new EventHandler<DocumentChangedEventArgs>(OnDocumentChanged);
        }

        public void EndTrackingElements() {
            App.Application.DocumentChanged -= new EventHandler<DocumentChangedEventArgs>(OnDocumentChanged);
        }

        public void StartCancellingAllDialogs() {
            App.DialogBoxShowing += new EventHandler<DialogBoxShowingEventArgs>(CancelAllDialogs);
        }

        public void EndCancellingAllDialogs() {
            App.DialogBoxShowing -= new EventHandler<DialogBoxShowingEventArgs>(CancelAllDialogs);
        }

        public void PostElementPropertyUpdateRequest(Document doc,
                                                     string txnName,
                                                     BuiltInParameter bip,
                                                     string value) {
            _doc = doc;
            _txnName = txnName;
            _paramToUpdate = bip;
            _paramToUpdateStringValue = value;
            App.Idling += new EventHandler<IdlingEventArgs>(NewElementPropertyValueUpdater);
        }

        public void PostCommandAndUpdateNewElementProperties(Document doc,
                                                             PostableCommand postableCommand, string transactionName,
                                                             BuiltInParameter bip, string value) {
            StartTrackingElements();
            StartCancellingAllDialogs();
            var postableCommandId = RevitCommandId.LookupPostableCommandId(postableCommand);
            App.PostCommand(postableCommandId);
            PostElementPropertyUpdateRequest(doc, transactionName, bip, value);
        }
    }
}
