using System;
using System.IO;
using System.Threading;
using System.Collections.Generic;
using System.Text.RegularExpressions;

using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

using pyRevitLabs.Common;
using pyRevitLabs.PyRevit;

namespace PyRevitLabs.PyRevit.Runtime {
    public class UpdaterListener : IUpdater {
        public delegate void UpdaterExecuted(object source, UpdaterData data);

        public event UpdaterExecuted OnUpdaterExecute;

        static AddInId _appId;
        static UpdaterId _updaterId;

        public UpdaterListener() {
            _appId = new AddInId(new Guid(PyRevitConsts.AddinId));
            _updaterId = new UpdaterId(_appId, new Guid("c2fa20c6-0729-46c5-95f9-f79abfab566e"));
        }

        public void Execute(UpdaterData data) {
            OnUpdaterExecute?.Invoke(this, data);
        }

        public UpdaterId GetUpdaterId() => _updaterId;
        public string GetUpdaterName() => PyRevitLabsConsts.ProductName + "Updater";
        public string GetAdditionalInformation() => "Updater interface to execute updater hooks";
        public ChangePriority GetChangePriority() => 0;
    }
}