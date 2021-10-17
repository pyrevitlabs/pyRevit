using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Text.RegularExpressions;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;

using pyRevitLabs.NLog;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;


namespace pyRevitLabs.Common {
    public class JSONDataSource<T> {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        private List<T> _cache = new List<T>();
        private string _cacheVersion = string.Empty;

        private string _dataSourceName = string.Empty;
        private string _dataSourcePath = string.Empty;
        //private string _dataSourceURL = string.Empty;
        private string _dataSourceCachePath = string.Empty;

        // default path is sideloaded file for the assembly containing T
        public string DefaultDataFilePath => CommonUtils.GetAssemblyPath<T>();

        public string DataFileName {
            get {
                return _dataSourceName;
            }
            set {
                if (value != null || value != string.Empty)
                    _dataSourceName = value;
                else
                    throw new PyRevitException("Bad data file m=name");
            }
        }

        public string DataCachePath {
            get {
                if (CommonUtils.VerifyPath(_dataSourceCachePath))
                    return _dataSourceCachePath;
                return UserEnv.UserTemp;
            }
            private set {
                if (value != null && value != string.Empty) {
                    CommonUtils.EnsurePath(value);
                    _dataSourceCachePath = value;
                }
            }
        }

        public string DataSourceURL { get; private set; }
        public int DataSourceUpdateEveryDays { get; private set; }

        public JSONDataSource(string dataSourceFileName, string dataSourceUrl = null, string dataCachePath = null, int updateEveryDays = 1) {
            DataFileName = dataSourceFileName;

            DataSourceURL = dataSourceUrl;
            DataCachePath = dataCachePath;
            DataSourceUpdateEveryDays = updateEveryDays;
        }

        public List<T> GetAllData() {
            // deserialize
            var dataSourcesPaths = new List<string>() { DataCachePath, DefaultDataFilePath };
            foreach (string dataSourcePath in dataSourcesPaths) {

                var dataSource = Path.Combine(dataSourcePath, DataFileName);
                logger.Debug("Getting data source \"{0}\"", dataSource);

                if (CommonUtils.VerifyFile(dataSource)) {

                    logger.Debug("Data source exists \"{0}\"", dataSource);
                    var cacheVersion = CommonUtils.GetFileSignature(dataSource);

                    if ((_cacheVersion != string.Empty && cacheVersion != _cacheVersion) || _cache.Count == 0) {

                        logger.Debug("Reloading data from \"{0}\"", dataSource);
                        var dataSet = File.ReadAllText(dataSource);

                        _cache = JsonConvert.DeserializeObject<List<T>>(dataSet);
                        if (_cache != null && _cache.Count > 0) {
                            _cacheVersion = cacheVersion;
                            return _cache;
                        }
                    }

                    logger.Debug("Using already loaded data. Identical signatures \"{0}\" = \"{1}\"", cacheVersion, _cacheVersion);
                    break;
                }
            }
            return _cache;
        }

        public void UpdateData(bool forceUpdate = false) {
            if (DataSourceURL != null && DataSourceURL != string.Empty) {
                try {
                    logger.Debug("Updating source data from \"{0}\"", DataSourceURL);
                    var dataSourceCacheFile = Path.Combine(DataCachePath, DataFileName);

                    // if datasource is not older than given # of days
                    // return without updating
                    if (CommonUtils.VerifyFile(dataSourceCacheFile) && !forceUpdate) {
                        var lastWrite = File.GetLastWriteTimeUtc(dataSourceCacheFile);
                        if ((DateTime.UtcNow - lastWrite).Days < DataSourceUpdateEveryDays) {
                            logger.Debug("Data source is still young. Skipping update. \"{0}\"", dataSourceCacheFile);
                            return;
                        }
                    }

                    logger.Debug("Downloading to \"{0}\"", dataSourceCacheFile);
                    CommonUtils.DownloadFile(DataSourceURL, dataSourceCacheFile, progressToken: DataFileName);
                }
                catch (Exception dlEx) {
                    logger.Debug("Error downloading host database file. | {0}", dlEx.Message);
                }
            }
        }
    }
}
