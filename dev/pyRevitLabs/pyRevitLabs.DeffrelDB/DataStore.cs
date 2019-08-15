using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

using pyRevitLabs.Common;

using pyRevitLabs.NLog;

namespace pyRevitLabs.DeffrelDB {
    // datastore
    public class DataStoreType {
        public readonly string TypeName = "txt";

        public DataStoreType(string dsource, Version dsourceVersion, Encoding dsourceEncoding) {
            Path = dsource;

            if (dsourceVersion is null)
                DataFormatVersion = new Version(0, 1);
            else
                DataFormatVersion = dsourceVersion;

            // https://stackoverflow.com/questions/2502990/create-text-file-without-bom
            if (dsourceEncoding is null)
                DataFormatEncoding = CommonUtils.GetUTF8NoBOMEncoding();
            else
                DataFormatEncoding = dsourceEncoding;
        }

        public string Path { get; private set; }
        public Version DataFormatVersion { get; private set; }
        public Encoding DataFormatEncoding { get; private set; }

        public override string ToString() {
            return string.Format("<DataStoreType path:{0} version:{1} encoding:{2}>", Path, DataFormatVersion, DataFormatEncoding);
        }

        // equality checks
        public override bool Equals(object other) {
            if (GetHashCode() != other.GetHashCode())
                return false;
            return true;
        }

        public override int GetHashCode() {
            return string.Format("{0}{1}", DataFormatVersion, DataFormatEncoding.WebName).GetHashCode();
        }
    }

    // datastore data lines
    internal enum DataLineCommitType {
        Created,
        Read,
        Updated,
        Dropped,
    }

    internal sealed class DataLine {
        public DataLine(string contents, DataLineCommitType commitType = DataLineCommitType.Read) {
            Contents = contents;
            CommitType = commitType;
        }

        public string Contents { get; set; } = "";
        public DataLineCommitType CommitType { get; set; }

        public override string ToString() {
            return string.Format("<DataLine contents:\"{0}...\" ctype:{1}", Contents, CommitType);
        }

        public override bool Equals(object obj) {
            return GetHashCode() == obj.GetHashCode();
        }

        public override int GetHashCode() {
            return Contents.GetHashCode();
        }
    }

    // data store IO
    internal enum DataStoreLockState {
        Unlocked,
        Locked,
    }

    internal class DataStore : IDisposable {
        public DataStore(DataStoreType dstoreType, bool exclusive = false, int ioTimeOut = 10000) {
            DataStoreType = dstoreType;
            ExclusiveAccess = exclusive;
            IOTimeOut = ioTimeOut;

            // confirm file exists
            CommonUtils.EnsureFile(FilePath);

            // open the datastore with requested access type
            Open();
        }

        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        // data type and access
        public DataStoreType DataStoreType { get; private set; }
        public bool ExclusiveAccess { get; private set; }

        // convenience properties
        public string FilePath { get { return DataStoreType.Path; } }
        public string FileName { get { return Path.GetFileName(FilePath); } }
        public Version Version { get { return DataStoreType.DataFormatVersion; } }
        public Encoding Encoding { get { return DataStoreType.DataFormatEncoding; } }
        public int IOTimeOut { get; private set; }

        // data lines formatter
        public IDataFormatter DataFormatter { get; private set; } = new DefaultDataFormatter();

        // data lines cache
        public List<DataLine> DataLines { get; private set; }

        // has datalines been modified?
        public bool IsModified {
            get { return true; }
        }

        // commit function
        public void Commit() {
            logger.Debug("    COMMIT");
            Close();
        }

        // private
        // access control lock mechanism
        private string LockFilePath {
            get {
                return Path.Combine(Path.GetDirectoryName(FilePath),
                                    Path.GetFileNameWithoutExtension(FileName) + ".lock");
            }
        }

        private bool LockExists { get { return File.Exists(LockFilePath); } }

        // main lock state control
        private DataStoreLockState LockState = DataStoreLockState.Unlocked;

        private void CreateLock() {
            // TODO: needs timeout
            bool isCreated = false;
            while (!isCreated) {
                try {
                    File.Create(LockFilePath).Close();
                    logger.Debug("    +lock");
                    isCreated = true;
                }
                catch { }
            }
        }

        private void DeleteLock() {
            // TODO: needs timeout
            bool isDeleted = false;
            while (!isDeleted) {
                try {
                    File.Delete(LockFilePath);
                    logger.Debug("    -lock");
                    isDeleted = true;
                }
                catch { }
            }
        }

        private void WaitForLockRelease() {
            logger.Debug("    WAIT FOR LOCK RELEASE...");
            var time = Stopwatch.StartNew();
            while (time.ElapsedMilliseconds < IOTimeOut)
                if (!LockExists)
                    return;
            throw new TimeoutException("Wait for unlock timeout.");
        }

        private void AcquireLock() {
            logger.Debug("    ACQUIRE");
            if (LockState == DataStoreLockState.Locked) {
                if (LockExists) {
                    // if already locked, return
                    logger.Debug("    ALREADY LOCKED");
                    return;
                }
                else {
                    logger.Debug("    ? MISSING LOCK");
                    // fall thru and create the missing lock
                }
            }
            else {
                // otherwise existing lock is not mine, wait for release
                if (LockExists) {
                    logger.Debug("    X NOT MY LOCK");
                    WaitForLockRelease();
                }
                // else fall thru and create the lock
            }

            // now that there are no existing locks, create one and own
            if (LockState == DataStoreLockState.Unlocked) {
                CreateLock();
                LockState = DataStoreLockState.Locked;
            }
        }

        private void ReleaseLock() {
            logger.Debug("    RELEASE");
            if (LockState == DataStoreLockState.Unlocked) {
                if (!LockExists)
                    // lock is missing
                    logger.Debug("    ALREADY UNLOCKED");
                else
                    logger.Debug("    X NOT MY LOCK");

                // in all cases the release is satisfied
                return;
            }
            else {
                if (!LockExists) {
                    logger.Debug("    ? MISSING LOCK");
                    return;
                }
                // else fall thru and delete the lock
            }

            // now that there are no existing locks, create one and own
            if (LockState == DataStoreLockState.Locked) {
                DeleteLock();
                LockState = DataStoreLockState.Unlocked;
            }
        }

        private void Open() {
            // create a public lock if exclusive access has been requested
            if (ExclusiveAccess) {
                logger.Debug("    OPEN EXCLUSIVE");
                AcquireLock();
            }
            else
                logger.Debug("    OPEN");

            DataLines = Load();
        }

        private void Close() {
            logger.Debug("    CLOSE");
            // only write if opened with modify and modification actually happened
            // merge releases all locks
            if (IsModified)
                Merge(DataLines);
        }

        // low level read and write
        private List<DataLine> Load() {
            logger.Debug("    LOAD");
            // make sure there is no other exlusive access on the datastore
            if (LockState != DataStoreLockState.Locked)
                WaitForLockRelease();
            return Read();
        }

        private void Merge(List<DataLine> dataLines) {
            logger.Debug("    AUTO RESOLVE MERGE");

#if TRACE
            TraceDump(dataLines);
# endif

            AcquireLock();

            var mergedDataLines = RunAutoMergeConflict(Read(), dataLines);
            string contents = string.Join(Environment.NewLine, mergedDataLines.Select(d => d.Contents));

#if TRACE
            TraceDump(mergedDataLines, marker: "merged");
# endif

            logger.Debug("    MERGE");

            File.WriteAllText(FilePath, contents, Encoding);

            ReleaseLock();
        }

        private static List<DataLine> RunAutoMergeConflict(List<DataLine> currentDataLines,
                                                           List<DataLine> newDataLines) {
            // merge existing version against new version
            // this function produces V3
            // V2: is currentDataLines
            // modified-A: is newDataLines with CommitType set on each data line (so we already know the diff between modified-A and V1 because they are the db actions)
            // modified-B: we don't know what it was. We only see V2
            //    V1----modified-B
            //   /              \
            // V1----------------V2----V3
            //   \                    /
            //    V1-----------modified-A

            var mergedDlines = new List<DataLine>();

            // create counters
            int currentCounter = 0, newCounter = 0;

            // create total counts to check counters against
            int currentTotal = currentDataLines.Count;
            int newTotal = newDataLines.Count;

            while (currentCounter < currentTotal || newCounter < newTotal) {
                // if both lists ended, break
                // otherwise keep processing if at least one list is not finished
                if (currentCounter >= currentTotal && newCounter >= newTotal)
                    break;

                // grab one item from each list
                var cLine = (currentCounter < currentTotal) ? currentDataLines[currentCounter] : null;
                var nLine = (newCounter < newTotal) ? newDataLines[newCounter] : null;

                // if current list ended
                if (cLine is null && nLine != null) {
                    if (nLine.CommitType == DataLineCommitType.Created || nLine.CommitType == DataLineCommitType.Updated)
                        mergedDlines.Add(new DataLine(nLine.Contents, nLine.CommitType));
                    newCounter++;
                    continue;
                }
                // if new list ended
                else if (cLine != null && nLine is null) {
                    mergedDlines.Add(new DataLine(cLine.Contents, cLine.CommitType));
                    currentCounter++;
                    continue;
                }
                // if both lists are finished
                else if (cLine is null && nLine is null)
                    break;

                // N is current line from newDataLines
                // (?) is the commit type for N (see DataLineCommitType)
                //      ( ) is DataLineCommitType.Read
                //      (+) is DataLineCommitType.Created
                //      (*) is DataLineCommitType.Updated
                //      (-) is DataLineCommitType.Dropped
                //      (?) is any of the above
                // C is current line from currentDataLines
                // (+1, +1) is increment indicator for new, current counters in that order

                // (?)N == C
                if (nLine.Contents == cLine.Contents) {
                    // ( )N == C --> ( )N (+1, +1)
                    // (+)N == C --> (+)N (+1, +1)
                    if (nLine.CommitType == DataLineCommitType.Read || nLine.CommitType == DataLineCommitType.Created || nLine.CommitType == DataLineCommitType.Updated) {
                        mergedDlines.Add(new DataLine(nLine.Contents, DataLineCommitType.Read));
                        currentCounter++;
                        newCounter++;
                    }
                    // (-)N == C --> (-)N (+1, +1)
                    else if (nLine.CommitType == DataLineCommitType.Dropped) {
                        mergedDlines.Add(new DataLine(nLine.Contents, DataLineCommitType.Dropped));
                        currentCounter++;
                        newCounter++;
                    }
                }

                // (?)N != C
                else {
                    // (?)N != C --> (+)C (--, +1)
                    //         N
                    if (currentDataLines.Skip(currentCounter).Contains(nLine)) {
                        mergedDlines.Add(new DataLine(cLine.Contents, DataLineCommitType.Created));
                        currentCounter++;
                    }
                    // ( |-)N != C --> (-)N (+1, --)
                    //      C
                    else if (newDataLines.Skip(newCounter).Contains(cLine) && (nLine.CommitType == DataLineCommitType.Read || nLine.CommitType == DataLineCommitType.Dropped)) {
                        mergedDlines.Add(new DataLine(nLine.Contents, DataLineCommitType.Dropped));
                        newCounter++;
                    }
                    // (+|*)N != C --> (+)N (+1, --)
                    //      C
                    else if ((nLine.CommitType == DataLineCommitType.Created || nLine.CommitType == DataLineCommitType.Updated) && newDataLines.Skip(newCounter).Contains(cLine)) {
                        mergedDlines.Add(new DataLine(nLine.Contents, DataLineCommitType.Created));
                        newCounter++;
                    }
                    // ( |-)N != C --> (-)N (+)C (+1, +1)
                    else if (nLine.CommitType == DataLineCommitType.Read || nLine.CommitType == DataLineCommitType.Dropped) {
                        mergedDlines.Add(new DataLine(nLine.Contents, DataLineCommitType.Dropped));
                        mergedDlines.Add(new DataLine(cLine.Contents, DataLineCommitType.Created));
                        currentCounter++;
                        newCounter++;
                    }
                    // (+)N != C --> (+)N (+)C (+1, +1)
                    else if (nLine.CommitType == DataLineCommitType.Created) {
                        mergedDlines.Add(new DataLine(cLine.Contents, DataLineCommitType.Created));
                        mergedDlines.Add(new DataLine(nLine.Contents, DataLineCommitType.Created));
                        currentCounter++;
                        newCounter++;
                    }
                    // (*)N != C --> (*)N (-)C (+1, +1)
                    // this means that N is the updated version of C
                    else if (nLine.CommitType == DataLineCommitType.Updated) {
                        mergedDlines.Add(new DataLine(cLine.Contents, DataLineCommitType.Dropped));
                        mergedDlines.Add(new DataLine(nLine.Contents, DataLineCommitType.Created));
                        currentCounter++;
                        newCounter++;
                    }
                }
            }

            var flattenedDlines = new List<DataLine>();
            foreach (var dline in mergedDlines)
                if (dline.CommitType != DataLineCommitType.Dropped)
                    flattenedDlines.Add(dline);

            return flattenedDlines;
        }

        private List<DataLine> Read() {
            logger.Debug("    READ");

            var time = Stopwatch.StartNew();
            string[] fileContents = { };
            bool isRead = false;
            while (time.ElapsedMilliseconds < IOTimeOut && !isRead) {
                try {
                    fileContents = File.ReadAllLines(FilePath, Encoding);
                    isRead = true;
                }
                catch { }
            }

            if (isRead) {
                var dlines = new List<DataLine>();
                foreach (string line in fileContents)
                    dlines.Add(new DataLine(line, DataLineCommitType.Read));
                return dlines;
            }
            else
                throw new TimeoutException("Read timeout.");
        }

#if TRACE
        private void TraceDump(List<DataLine> dataLines, string marker = "") {
            List<string> contents = new List<string>();
            foreach (var dline in dataLines) {
                string line = "  ";
                switch (dline.CommitType) {
                    case DataLineCommitType.Created: line = "+ "; break;
                    case DataLineCommitType.Dropped: line = "- "; break;
                    case DataLineCommitType.Updated: line = "* "; break;
                }

                line += dline.Contents;
                contents.Add(line);
            }

            File.WriteAllText(FilePath + "_" + DateTime.Now.ToString("yyyyMMddHHmmssffff") + marker + ".txt",
                              string.Join(Environment.NewLine, contents), Encoding);
        }
#endif

        // make sure to release the lock if object is being disposed
        public void Dispose() {
            logger.Debug("    DISPOSE");
            ReleaseLock();
        }
    }
}
