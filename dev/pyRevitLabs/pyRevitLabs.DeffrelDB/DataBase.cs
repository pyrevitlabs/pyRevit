using System;
using System.Collections.Generic;
using System.Text;

using pyRevitLabs.Common;
using NLog.Targets;
using NLog.Config;

#if DEBUG
using pyRevitLabs.CommonCLI;
#endif

using NLog;


// TODO: add log messages
// TODO: field keys must be unique in the datastore: @pk() expects a unique keyname
//       nullify broken relations or delete records?
// TODO: lines with exact definitions will break. so each line must have a unique key in the dstore,
//       unless merge conflict resolver can work table-by-table
// TODO: Datastore watcher: https://stackoverflow.com/questions/721714/notification-when-a-file-changes 
// TODO: see IsModified. Only write the data if DataLines is modified
// TODO: implement commit line range?
// TODO: implement headers e.g. (*FIELD1FIELD2)
// TODO: Fix readonly file issue when datastore can not write and gets stuck
// TODO: release keys on init
// TODO: create unit tests
//       + lock unlock
//       + WaitForLockRelease needs to gurantee lock is released and acquired?
//       + A connection could leave locks behind if it can't access the file for unlocking before timeout

/* NOTES:
 * Why unique ids are required for db objects?
 * Allowing same ids for tables and dbs, causes exact same line definition on the dstore and messes up with the
 * merge conflict resolution since multiple lines would be identical. Improvements to merge conflict logic could
 * help remove this barrier but at the same time the uniqueness of ids across the dstore simplifies many other db
 * processes, table relationships, and integrity checks.
 
    TRANSACTION PROCESS:

     CONNECTION    DATASTORE OBJ     LOCK       DATAFILE     COMMENTS
     C             |                 |          |            TXN_BEGIN
     C             |                 |          |            1) First phase is updating the locks table
     :             :                 :          :                   locks table controls access to db elements
     C-----NEW---->DS-E              |          |               New DataStore Obj with Exclusive access* (DS-E)
     C             DS-E------------->L+         |               DS-E creates a shared lock for exclusive access;
     :             :                 :          :                   OTHER CONNECTIONS WILL NOT READ OR WRITE
     C             DS-E<-------------~----------READ            DS-E will read the dstore dfile
     C----R------->DS-E              L          |               Connection modifies the lock table with new locks
     C----E--L---->DS-E              L          |               
     C----C--O---->DS-E              L          READ  X ------> Other connections CAN NOT read the dstore                              
     C----O--C---->DS-E              L          WRITE X <------ Other connections CAN NOT modify the dstore
     C----R--K---->DS-E              L          |               
     C----D------->DS-E              L          |               
     C             DS-E              L          |               
     C---COMMIT--->DS-E              L          |               After modifications, connection COMMITs the Datastore
     C             DS-E------------->L!         |               DS-E requests a lock before write, but since it is an
     :             :                 :          :                   exclusive DS, lock already exists
     C             DS-E      +-------~----------READ            DS-e reads the current state of dfile  
     C             DS-E      |       L          |               
     C             DS-E--->MERGE     L          |               DS-E performs an auto merge-conflict against the read
     C             DS-E      +----------------->WRITE           DS-E writes the merged content to dfile     
     C             DS-E------------->L-         |               DS-E releases the lock
     C             X---------------->?          |               DS-E dies and releases all remaining locks on dispose
     C             |                 |          |               
     C             |                 |          |               
     C             |                 |          |               
     C             |                 |          |               
     C             |                 |          |               
     C             |                 |          |            2) Second phase is modification of data by dbms
     C-----NEW---->DS                |          |               New DataStore Obj
     C             DS<---------------~----------READ            DS will read the dstore dfile
     C             DS                |          |               Connection modifies data as needed
     :             :                 :          :                  OTHER CONNECTIONS CAN READ OR WRITE
     C----M------->DS                |          |               Connection modifies data as needed
     C----O--D---->DS                |          |               
     C----D--A---->DS                |          READ  --------> Other connections can read the dstore               
     C----I--T---->DS                |          WRITE <-------- Other connections can modify the dstore
     C----F--A---->DS                |          |               
     C----Y------->DS                |          |               
     C             DS                |          |            TXN_END
     C---COMMIT--->DS                |          |               After modifications, connection COMMITs the Datastore
     C             DS--------------->L+         |               DS requests a lock before write
     C             DS        +-------~----------READ            DS reads the current state of dfile  
     C             DS        |       L          |               
     C             DS----->MERGE     L          |               DS performs an auto merge-conflict against the read
     C             DS        +-------~--------->WRITE           DS writes the merged content to dfile     
     C             DS--------------->L-         |               DS releases the lock
     C             X---------------->?          |               DS dies and releases all remaining locks on dispose
     C             |                 |          |               
     C             |                 |          |               
     C             |                 |          |               
     C             |                 |          |               
     C             |                 |          |               
     C             |                 |          |            3) Third phase is releasing the locks
     C-----NEW---->DS-E              |          |               New DataStore Obj with Exclusive access* (DS-E)
     C             DS-E------------->L+         |               DS-E creates a shared lock for exclusive access;
     :             :                 :          :                   OTHER CONNECTIONS WILL NOT READ OR WRITE
     C             DS-E<-------------~----------READ            DS-E will read the dstore dfile
     C----R--U---->DS-E              L          |               Connection modifies the lock table with new locks
     C----E--N---->DS-E              L          |               
     C----C--L---->DS-E              L          READ  X ------> Other connections CAN NOT read the dstore                              
     C----O--O---->DS-E              L          WRITE X <------ Other connections CAN NOT modify the dstore
     C----R--C---->DS-E              L          |               
     C----D--K---->DS-E              L          |               
     C             DS-E              L          |               
     C---COMMIT--->DS-E              L          |               After modifications, connection COMMITs the Datastore
     C             DS-E------------->L!         |               DS-E requests a lock before write, but since it is an
     :             :                 :          :                   exclusive DS, lock already exists
     C             DS-E      +-------~----------READ            DS-e reads the current state of dfile  
     C             DS-E      |       L          |               
     C             DS-E--->MERGE     L          |               DS-E performs an auto merge-conflict against the read
     C             DS-E      +-------~--------->WRITE           DS-E writes the merged content to dfile     
     C             DS-E------------->L-         |               DS-E releases the lock
     C             DS-E------------->?          |               DS-E dies and releases all remaining locks on dispose
     :             :                 :          :               
     :             :                 :          :               
     :             :                 :          :               Connection stays alive while app is communicating
     :             :                 :          :               When all db access needs are done and app closes,
     X             |                 |          |               connection dies and performs lock release on dispose

   * Exclusive access could be requested by the connection for managing shared data inside the DS.
     In current implementation, exlusive access is used to modify db element locks in locks table. When a connection
     is updating locks, other connections must wait for the lock table to be updated.
 */


namespace pyRevitLabs.DeffrelDB {
    public enum ConnectionLockType {
        DataStore,
        DB,
        Table,
        Record,
    }

    public sealed class ConnectionLock {
        // TODO: change to internal for Release
        public ConnectionLock(string source,
                              string requester,
                              string connId,
                              string dbName,
                              string tableName,
                              object recordKey,
                              string lockId = null) {
            // use exisitng or generate new lock uuid
            if (lockId == null)
                LockId = CommonUtils.NewShortUUID();
            else
                LockId = lockId;

            // set lock source requester
            LockSource = source;
            LockRequester = requester;
            LockConnId = connId;

            // db might be null
            LockTargetDB = dbName;

            // make sure db is specified when locking a table
            if (tableName != null && dbName == null)
                throw new Exception("DB must be specified when locking a table.");
            LockTargetTable = tableName;

            // make sure db:table is specified when locking a record
            if (recordKey != null && (tableName == null || dbName == null))
                throw new Exception("DB and Table must be specified when locking a record.");
            LockTargetRecordKey = recordKey;
        }

        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        public string LockId { get; private set; }
        public string LockSource { get; private set; }
        public string LockRequester { get; private set; }
        public string LockConnId { get; private set; }
        public string LockTargetDB { get; private set; }
        public string LockTargetTable { get; private set; }
        public object LockTargetRecordKey { get; private set; }

        public bool IsDataStoreLock {
            get { return LockTargetDB == null && LockTargetTable == null && LockTargetRecordKey == null; }
        }

        public bool IsDBLock {
            get { return LockTargetDB != null && LockTargetTable == null && LockTargetRecordKey == null; }
        }

        public bool IsTableLock {
            get { return LockTargetDB != null && LockTargetTable != null && LockTargetRecordKey == null; }
        }

        public bool IsRecordLock {
            get { return LockTargetDB != null && LockTargetTable != null && LockTargetRecordKey != null; }
        }

        public override string ToString() {
            return string.Format("<ConnectionLock id:\"{0}\" sig:\"{1}\" locking:\"{2}\">",
                                 LockId, LockConnectionSignature, LockHierarchy);
        }

        public ConnectionLockType LockType {
            get {
                if (IsDataStoreLock)
                    return ConnectionLockType.DataStore;

                if (IsDBLock)
                    return ConnectionLockType.DB;

                if (IsTableLock)
                    return ConnectionLockType.Table;

                // then it must be a record lock
                return ConnectionLockType.Record;
            }
        }

        public string LockConnectionSignature {
            get { return LockSource + ':' + LockRequester + ':' + LockConnId; }
        }

        public string LockHierarchy {
            get { return LockTargetDB + ':' + LockTargetTable + ':' + LockTargetRecordKey; }
        }

        public override bool Equals(object obj) {
            return GetHashCode() == obj.GetHashCode();
        }

        public bool IsIdenticalTo(ConnectionLock connLock) {
            return connLock.LockId == LockId
                        && connLock.LockConnectionSignature == LockConnectionSignature
                        && connLock.LockHierarchy == LockHierarchy;
        }

        public bool IsRestrictedBy(ConnectionLock otherLock) {
            // this method checks two-way locking conflicts
            // db:table conflicts with db:table:record both ways.
            // because if a connection has a lock on db:table:record, another connection should not
            // be able to lock its parent db:table
            // also if a connection has a lock on db:table, another connection should not
            // be able to lock its child db:table:record

            // checking for master datastore locks first
            // if any lock is a datastore lock, all other locks are in conflict
            if (IsDataStoreLock || otherLock.IsDataStoreLock) {
                logger.Debug("At least one lock is a datastore lock.");
                return true;
            }

            // checking db:table:record locks
            if (LockType == otherLock.LockType) {
                logger.Debug("Lock types are equal = {0}", LockType);
                // if lock types are equal
                // check if we have equal lock targets
                switch (LockType) {
                    case ConnectionLockType.DB:
                        if (otherLock.LockTargetDB == LockTargetDB)
                            return true;
                        break;
                    case ConnectionLockType.Table:
                        if (otherLock.LockTargetDB == LockTargetDB
                            && otherLock.LockTargetTable == LockTargetTable)
                            return true;
                        break;
                    case ConnectionLockType.Record:
                        if (otherLock.LockTargetDB == LockTargetDB
                            && otherLock.LockTargetTable == LockTargetTable
                            && otherLock.LockTargetRecordKey.Equals(LockTargetRecordKey))
                            return true;
                        break;
                }
            }
            else if (LockType < otherLock.LockType) {
                logger.Debug("This lock is higher-level than other.");
                // if I have a higher-degree lock, test if I'm holding a lock on other lock targets
                if (LockType == ConnectionLockType.DB) {
                    // Am I trying to lock other locks target db?
                    if (otherLock.LockTargetDB == LockTargetDB) {
                        logger.Debug("This lock is locking other locks DB.");
                        return true;
                    }
                }
                else if (LockType == ConnectionLockType.Table) {
                    // Am I trying to lock other locks target db:table?
                    if (otherLock.LockTargetDB == LockTargetDB
                        && otherLock.LockTargetTable == LockTargetTable) {
                        logger.Debug("This lock is locking other locks DB:Table.");
                        return true;
                    }
                }
                // there is nothing lower than the record lock and I'm higher-degree than other lock
                // so I'm definitely not record otherwise we would have been equal
            }
            else {
                logger.Debug("This lock is lower-level than other.");
                // if no condition above is met, then LockType > otherLock.LockType
                // if I have a lower-degree lock, test if other lock is trying to lock my targets
                if (otherLock.LockType == ConnectionLockType.DB) {
                    // Is other lock trying to lock the db containing my table?
                    if (otherLock.LockTargetDB == LockTargetDB) {
                        logger.Debug("Other lock is locking this locks DB.");
                        return true;
                    }
                }
                else if (otherLock.LockType == ConnectionLockType.Table) {
                    // Is other lock trying to lock the db containing my table?
                    if (otherLock.LockTargetDB == LockTargetDB
                        && otherLock.LockTargetTable == LockTargetTable) {
                        logger.Debug("Other lock is locking this locks DB:Table.");
                        return true;
                    }
                }
                // there is nothing lower than the record lock and otherLock is higher-degree than me
                // so otherLock is definitely not record otherwise we would have been equal
            }

            return false;
        }

        public bool BelongsTo(DataBase conn) {
            return conn.ConnectionSource == LockSource
                       && conn.ConnectionRequester == LockRequester
                       && conn.ConnectionId == LockConnId;
        }

        public override int GetHashCode() {
            return LockHierarchy.GetHashCode();
        }
    }

    public sealed class DataBase : IDisposable {
        // public 
        public static DataBase Connect(string sourcePath,
                                       string requester,
                                       Version sourceVersion = null,
                                       Encoding sourceEncoding = null,
                                       bool debug = false) {
            if (debug)
                ActivateDebugLogging();

            return new DataBase(sourcePath, requester, sourceVersion, sourceEncoding);
        }

        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        private static void ActivateDebugLogging() {
            var config = new LoggingConfiguration();
            var logconsole = new ConsoleTarget("logconsole") { Layout = @"${level}: ${message} ${exception}" };
            config.AddTarget(logconsole);
            config.AddRuleForOneLevel(LogLevel.Debug, logconsole);
            LogManager.Configuration = config;
        }

        public string ConnectionSource { get { return Environment.MachineName.ToLower(); } }
        public string ConnectionRequester { get; private set; }
        public string ConnectionId { get; private set; }
        public DataStoreType ActiveDataStoreType;

        public void BEGIN(string dbName, string tableName = null, object recordKey = null) {
            // validate input
            // internal db txn database is private
            if (dbName == connDbName)
                throw new Exception("Can not access private database.");
            // user opens a transaction block
            TXN_BEGIN(dbName, tableName, recordKey, block: true);
        }

        public void END(ConnectionLock cLock = null) {
            // user ends a transaction block
            TXN_END(block: true);
        }

        // state query functions
        public List<ConnectionLock> ReadLocks() {
            using (var dstore = new DataStore(ActiveDataStoreType))
                return ReadActiveLocks(dstore);
        }

        public DataStoreType ReadDataStoreType() {
            using (var dstore = new DataStore(ActiveDataStoreType))
                return DataFunctions.ReadDataStoreType(dstore);
        }

        // CRUD functions
        public void CreateDB(string dbName, DatabaseDefinition dbDef = null) {
            try {
                TXN_BEGIN(dbName: dbName);
                DataFunctions.CreateDB(activeDStore, dbName, dbDef);
            }
            finally {
                TXN_END();
            }
        }

        public List<DatabaseDefinition> ReadAllDBs() {
            using (var dstore = new DataStore(ActiveDataStoreType))
                return DataFunctions.ReadAllDBs(dstore);
        }

        public DatabaseDefinition ReadDB(string dbName) {
            using (var dstore = new DataStore(ActiveDataStoreType))
                return DataFunctions.ReadDB(dstore, dbName);
        }

        public void CreateTable(string dbName, string tableName, TableDefinition tableDef) {
            try {
                TXN_BEGIN(dbName: dbName, tableName: tableName);
                DataFunctions.CreateTable(activeDStore, dbName, tableName, tableDef);
            }
            finally {
                TXN_END();
            }
        }

        public List<TableDefinition> ReadAllTables(string dbName) {
            using (var dstore = new DataStore(ActiveDataStoreType))
                return DataFunctions.ReadAllTables(dstore, dbName);
        }

        public TableDefinition ReadTable(string dbName, string tableName) {
            using (var dstore = new DataStore(ActiveDataStoreType))
                return DataFunctions.ReadTable(dstore, dbName, tableName);
        }

        public bool UpdateTable(string tableName, TableDefinition tableConfig) {
            // TODO: Connection.UpdateTable
            throw new NotImplementedException();
        }

        public bool RenameTable(string tableName, string tableNewName) {
            // TODO: Connection.RenameTable
            throw new NotImplementedException();
        }

        public bool DropTable(string tableName) {
            // TODO: Connection.DropTable
            throw new NotImplementedException();
        }

        public void InsertRecord(string dbName, string tableName, object recordKey, IDictionary<string, object> fieldValues) {
            try {
                TXN_BEGIN(dbName: dbName, tableName: tableName, recordKey: recordKey);
                DataFunctions.InsertRecord(activeDStore, dbName, tableName, recordKey, fieldValues);
            }
            finally {
                TXN_END();
            }
        }

        public List<Dictionary<string, object>> ReadAllRecords(string dbName, string tableName) {
            using (var dstore = new DataStore(ActiveDataStoreType))
                return DataFunctions.ReadAllRecords(dstore, dbName, tableName);
        }

        public IDictionary<string, object> ReadRecord(string dbName, string tableName, object recordKey) {
            using (var dstore = new DataStore(ActiveDataStoreType))
                return DataFunctions.ReadRecord(dstore, dbName, tableName, recordKey);
        }

        public void UpdateRecord(string dbName,
                                 string tableName,
                                 object recordKey,
                                 IDictionary<string, object> updatedFieldValues) {
            try {
                TXN_BEGIN(dbName: dbName, tableName: tableName, recordKey: recordKey);
                DataFunctions.UpdateRecord(activeDStore, dbName, tableName, recordKey, updatedFieldValues);
            }
            finally {
                TXN_END();
            }
        }

        public void TagRecord(string dbName,
                              string tableName,
                              object recordKey,
                              KeyValuePair<string, string> tagValue) {
            // TODO: Connection.TagRecord
            throw new NotImplementedException();
        }

        public void ReadRecordCommits(string dbName, string tableName, object recordKey) {
            // TODO: Connection.ReadRecordHistory
            throw new NotImplementedException();
        }

        public void RestoreRecordCommit(string dbName, string tableName, object recordKey, RecordCommit commit) {
            // TODO: Connection.RestoreRecordCommit
            throw new NotImplementedException();
        }

        public void TagRecordCommit(string dbName,
                                    string tableName,
                                    object recordKey,
                                    KeyValuePair<string, string> tagValue) {
            // TODO: Connection.TagRecordCommit
            throw new NotImplementedException();
        }

        public void DropRecord(string dbName, string tableName, object recordKey) {
            try {
                TXN_BEGIN(dbName: dbName, tableName: tableName, recordKey: recordKey);
                DataFunctions.DropRecord(activeDStore, dbName, tableName, recordKey);
            }
            finally {
                TXN_END();
            }
        }

        public bool DropRecords(string dbName, string tableName) {
            // TODO: Connection.DropRecords
            throw new NotImplementedException();
        }

        // private
        private const string connDbName = "txn_db";
        private const string connDbLocksTableName = "locks_table";
        private const string connDbLockUUIDField = "lock_uuid";
        private const string connDbLockSourceField = "lock_source";
        private const string connDbLockRequesterField = "lock_requester";
        private const string connDbLockConnUUIDField = "lock_conn_uuid";
        private const string connDbLockDBField = "lock_dbname";
        private const string connDbLockTableField = "lock_tablename";
        private const string connDbLockRecordKeyField = "lock_recordkey";

        private DataStore activeDStore = null;
        private bool blockTxn = false;

        private DataBase(string filePath, string requester, Version sourceVersion, Encoding sourceEncoding) {
#if DEBUG
            //ConsoleProvider.Attach();
#endif
            ActiveDataStoreType = new DataStoreType(filePath, sourceVersion, sourceEncoding);
            ConnectionId = CommonUtils.NewShortUUID();
            ConnectionRequester = requester.ToLower();

            // verify datastore type
            using (var dstore = new DataStore(ActiveDataStoreType, exclusive: true)) {
                VerifyDataStoreType(dstore);
                VerifyLocksTable(dstore);
                try {
                    dstore.Commit();
                }
                catch (Exception initEx) {
                    throw new Exception(
                        string.Format("Exception occured when trying to initialize connection. | {0}",
                                      initEx.Message));
                }
            }
        }

        private void TXN_BEGIN(string dbName, string tableName = null, object recordKey = null, bool block = false) {
            logger.Debug("TXN_BEGIN");

            // PURPOSE:
            // Create a lock
            // Open/prepare shared datastore for all the future modify functions

            // verify block transaction status
            if (block && !blockTxn)
                blockTxn = block;

            // validate input
            // db might be null
            // make sure db is specified when locking a table
            if (tableName != null && dbName == null)
                throw new Exception("DB must be specified when opening a table-level transaction.");
            // make sure db:table is specified when locking a record
            if (recordKey != null && (tableName == null || dbName == null))
                throw new Exception("DB and Table must be specified when opening a record-level transaction.");

            // write the lock
            AcquireLocks(new ConnectionLock(ConnectionSource, ConnectionRequester, ConnectionId,
                                            dbName, tableName, recordKey));

            // if no active datastore (means that this is the first BEGIN in a txn chain,
            // then set the active datastore
            if (activeDStore == null) {
                activeDStore = new DataStore(ActiveDataStoreType);
            }
        }

        private void TXN_END(bool block = false) {
            logger.Debug("TXN_END");

            // close the block if block is true (called by END)
            // if block is false, the TXN_END is being called from commands
            if (block)
                blockTxn = false;

            // if there is no active block txn, close and commit
            // otherwise skip writing changes until END block is requested
            if (!blockTxn) {
                // close only if there is an active dstore
                if (activeDStore != null) {
                    try {
                        // now close and commit the datastore
                        activeDStore.Commit();
                        activeDStore.Dispose();
                        activeDStore = null;
                    }
                    catch (Exception commitEx) {
                        throw new Exception(
                            string.Format("Exception occured while trying to commit changes. | {0}",
                                          commitEx.Message));
                    }
                    finally {
                        // drop all new locks created by this connection
                        ReleaseLocks();
                    }
                }
            }
        }

        private List<ConnectionLock> ReadActiveLocks(DataStore dstore) {
            var lockList = new List<ConnectionLock>();

            try {
                foreach (var lockRecord in DataFunctions.ReadAllRecords(dstore, connDbName, connDbLocksTableName)) {
                    lockList.Add(new ConnectionLock(
                        lockRecord[connDbLockSourceField] as string,
                        lockRecord[connDbLockRequesterField] as string,
                        lockRecord[connDbLockConnUUIDField] as string,
                        lockRecord[connDbLockDBField] as string,
                        lockRecord[connDbLockTableField] as string,
                        lockRecord[connDbLockRecordKeyField],
                        lockId: lockRecord[connDbLockUUIDField] as string
                        ));
                }
            }
            catch (Exception ex) {
                // throw an exception if the lock table is not configured
                throw new Exception(
                    string.Format("Transaction database has not been configured. | {0}", ex.Message)
                    );
            }

            return lockList;
        }

        private void AcquireLocks(ConnectionLock newLock) {
            logger.Debug("RECORD LOCK");

            // open datastore for exclusive access
            using (var dstore = new DataStore(ActiveDataStoreType, exclusive: true)) {
                // get all existing locks
                // check access, find the highest-level compatible lock
                ConnectionLock txnLock = newLock;
                foreach (ConnectionLock activeLock in ReadActiveLocks(dstore)) {
                    logger.Debug("Lock Found: {0}", activeLock);
                    // is existing lock restricting access?
                    if (newLock.IsRestrictedBy(activeLock)) {
                        //  does restricting lock belong to this connection?
                        //  if yes and it is a higher-level lock, use that
                        if (activeLock.BelongsTo(this) && activeLock.LockType <= newLock.LockType) {
                            logger.Debug("Existing lock {0} is higher than new {1}", activeLock, newLock);
                            txnLock = activeLock;
                        }
                        //  does the lock not belong to this connection in which case reject
                        //  or is trying to acquire a higher level lock that active lock
                        else {
                            logger.Debug("New lock {0} is restricted by {1}", newLock, activeLock);
                            throw new AccessRestrictedException(newLock, activeLock);
                        }
                    }
                    // if not restricting, does this connection already have a txn block lock of equal level
                    // reject again since the connection need to close its block lock first and then
                    // work on another entry
                    else {
                        if (activeLock.BelongsTo(this)) {
                            logger.Debug("New lock {0} not on the same path as existing {1}", newLock, activeLock);
                            throw new AccessRestrictedByExistingLockException(newLock, activeLock);
                        }
                    }
                }

                logger.Debug("Using lock: {0}", txnLock);
                // at this point, the are no locks that restrict access
                // but we might be re-using an active compatible lock
                // so only write the lock if is not existing compatible
                if (txnLock == newLock) {
                    try {
                        // register the new lock: if target is not locked, lock it
                        DataFunctions.InsertRecord(
                            dstore,
                            connDbName,
                            connDbLocksTableName,
                            newLock.LockId,
                            new Dictionary<string, object>() {
                                { connDbLockSourceField, newLock.LockSource },
                                { connDbLockRequesterField, newLock.LockRequester },
                                { connDbLockConnUUIDField, newLock.LockConnId },
                                { connDbLockDBField, newLock.LockTargetDB},
                                { connDbLockTableField, newLock.LockTargetTable},
                                { connDbLockRecordKeyField, newLock.LockTargetRecordKey},
                            });
                    }
                    catch (Exception lockEx) {
                        // finally statement closes the dstore and release the exclusivity if throwing an exception
                        throw new Exception(
                            string.Format("Error creating lock: {0} | {1}", newLock, lockEx.Message)
                            );
                    }
                    finally {
                        try {
                            // write changes
                            dstore.Commit();
                        }
                        catch (Exception commitEx) {
                            // finally statement closes the dstore and release the exclusivity if throwing an exception
                            throw new Exception(
                                string.Format("Exception occured when commiting new locks. | {0}", commitEx.Message)
                                );
                        }
                    }
                }
            }
        }

        private void ReleaseLocks() {
            logger.Debug("RECORD UN-LOCK");

            // open datastore for exclusive access
            using (var dstore = new DataStore(ActiveDataStoreType, exclusive: true)) {
                try {
                    // get all existing locks
                    // release locks belonging to this connection
                    foreach (ConnectionLock activeLock in ReadActiveLocks(dstore)) {
                        logger.Debug("Lock found: {0}", activeLock);
                        if (activeLock.BelongsTo(this)) {
                            logger.Debug("Dropping lock: {0}", activeLock);
                            DataFunctions.DropRecord(dstore, connDbName, connDbLocksTableName, activeLock.LockId);
                        }
                    }
                }
                catch (Exception dropEx) {
                    // finally statement closes the dstore and release the exclusivity if throwing an exception
                    throw new Exception(
                        string.Format("Exception occured when dropping lock records. | {0}", dropEx.Message)
                        );
                }
                finally {
                    try {
                        // write changes
                        dstore.Commit();
                    }
                    catch (Exception commitEx) {
                        // finally statement closes the dstore and release the exclusivity if throwing an exception
                        throw new Exception(
                            string.Format("Exception occured when commiting released locks. | {0}", commitEx.Message)
                            );
                    }
                }
            }
        }

        private void VerifyDataStoreType(DataStore dstore) {
            logger.Debug("VerifyDataStoreType");

            DataStoreType existingDStoreType = null;
            try {
                existingDStoreType = DataFunctions.ReadDataStoreType(dstore);

                if (!existingDStoreType.Equals(dstore.DataStoreType))
                    throw new Exception(
                        string.Format("Requested Datastore type \"{0}\" does not match existing \"{1}\"",
                                      dstore.DataStoreType, existingDStoreType)
                        );
            }
            catch (FormatException) {
                // there is no datastore so there is no point in opening a txn
                DataFunctions.CreateDataStore(dstore);
            }
        }

        private void VerifyLocksTable(DataStore dstore) {
            logger.Debug("VerifyLocksTable");

            // ensure connection database
            DatabaseDefinition connDbDef;
            try {
                // if db exists we're good
                connDbDef = DataFunctions.ReadDB(dstore, connDbName);
            }
            catch {
                // otherwise create it
                var newConnDbDef = new DatabaseDefinition(dbName: connDbName) {
                    Description = "Internal DB"
                };

                // create the connection management database
                DataFunctions.CreateDB(dstore, connDbName, newConnDbDef);
            }

            // ensue locks table
            TableDefinition locksTableDef;
            try {
                // if table exists we're good
                locksTableDef = DataFunctions.ReadTable(dstore, connDbName, connDbLocksTableName);
            }
            catch {
                // otherwise create it
                // locks have fields for dbname, tablename and record keys but they're not wired
                // - to allow implicit locking of nonexisting entries
                // - to remove the need to update wires when new tables and dbs are created
                var newlocksTableDef = new TableDefinition() {
                    Fields = new List<Field>() {
                        new UUIDField(connDbLockUUIDField),
                        new TextField(connDbLockSourceField),
                        new TextField(connDbLockRequesterField),
                        new UUIDField(connDbLockConnUUIDField),
                        new TextField(connDbLockDBField),
                        new TextField(connDbLockTableField),
                        new TextField(connDbLockRecordKeyField),
                    },
                    Description = "Locks Table",
                    IsHidden = true,
                    SupportsHistory = false
                };

                // create transaction locks table
                DataFunctions.CreateTable(dstore, connDbName, connDbLocksTableName, newlocksTableDef);
            }
        }

        // ending connection
        public void Dispose() {
            logger.Debug("DISPOSE CONNECTION");
            ReleaseLocks();
        }
    }
}