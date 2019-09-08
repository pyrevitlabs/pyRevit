using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace pyRevitLabs.DeffrelDB {
    internal static class DataFunctions {
        // dstore
        public static void CreateDataStore(DataStore dstore) {
            // grab current line contents
            var dstoreEntries = dstore.DataLines.Select(x => x.Contents).ToList();

            // read current dstore type if any
            DataStoreType exstDStoreType =
                dstore.DataFormatter.ReadDataStoreType(dstoreEntries);

            // check if existing data store is defined and matches the provided type
            if (exstDStoreType != null && !exstDStoreType.Equals(dstore.DataStoreType))
                throw new Exception(
                    string.Format("Datastore type does not match existing \"{0}\"", exstDStoreType)
                    );

            // if no existing dstore type is found, create based on input dstore type
            if (exstDStoreType is null) {
                // if file is not empty, throw an exception
                if (dstore.DataLines.Count > 0)
                    throw new Exception("Datastore is not configured as a flat database and is not empty.");

                // if empty
                // ask the formatter to build the entry and submit a change request
                var ecReq = dstore.DataFormatter.BuildDataStoreEntry(dstoreEntries,
                                                                     dstore.DataStoreType);
                // submit dstore and entry change request for processing
                ProcessChangeRequest(dstore, ecReq);
            }
        }

        public static DataStoreType ReadDataStoreType(DataStore dstore) {
            var dstoreEntries = dstore.DataLines.Select(x => x.Contents).ToList();
            // read current dstore type if any
            DataStoreType exstDStoreType =
                dstore.DataFormatter.ReadDataStoreType(dstoreEntries);

            if (exstDStoreType is null)
                throw new FormatException(string.Format("Datastore does not have a type definition"));

            return dstore.DataFormatter.ReadDataStoreType(dstoreEntries); 
        }

        // db functions
        public static void CreateDB(DataStore dstore, string dbName, DatabaseDefinition dbDef) {
            // grab current line contents
            var dstoreEntries = dstore.DataLines.Select(x => x.Contents).ToList();

            // verify db does not exist
            var exstDBDef =
                dstore.DataFormatter.ReadDBDefinition(dstoreEntries, dstore.DataStoreType, dbName);
            if (exstDBDef != null)
                throw new Exception(string.Format("Database already exists \"{0}\"", dbName));

            // build db entries
            var ecReq = dstore.DataFormatter.BuildDBEntry(
                dstoreEntries,
                dstore.DataStoreType,
                new DatabaseDefinition(dbName: dbName) { Description = dbDef.Description }
                );
            // submit dstore and entry change request for processing
            ProcessChangeRequest(dstore, ecReq);
        }

        public static List<DatabaseDefinition> ReadAllDBs(DataStore dstore) {
            return dstore.DataFormatter.ReadDBDefinitions(
                dstore.DataLines.Select(x => x.Contents).ToList(), dstore.DataStoreType
                );
        }

        public static DatabaseDefinition ReadDB(DataStore dstore, string dbName) {
            var dbDef = dstore.DataFormatter.ReadDBDefinition(
                dstore.DataLines.Select(x => x.Contents).ToList(), dstore.DataStoreType, dbName
                );
            if (dbDef is null)
                throw new Exception(string.Format("Database \"{0}\" does not exist.", dbName));
            return dbDef;
        }

        // table functions
        public static void CreateTable(DataStore dstore, string dbName, string tableName, TableDefinition tableDef) {
            // grab current line contents
            var dstoreEntries = dstore.DataLines.Select(x => x.Contents).ToList();

            // verify db
            var existDBDef = ReadDB(dstore, dbName);

            // verify table does not exist
            var existTableDef =
                dstore.DataFormatter.ReadTableDefinition(dstoreEntries, dstore.DataStoreType, existDBDef, tableName);
            if (existTableDef != null)
                throw new Exception(
                    string.Format("Table \"{1}\" already exists in database \"{0}\"", dbName, tableName)
                    );

            // build table def
            var newTableDef = new TableDefinition(tableName: tableName) {
                Fields = tableDef.Fields,
                Wires = tableDef.Wires,
                Description = tableDef.Description,
                FieldDelimiter = tableDef.FieldDelimiter,
                SupportsTags = tableDef.SupportsTags,
                IsHidden = tableDef.IsHidden,
                SupportsHistory = tableDef.SupportsHistory
            };

            // build db entries
            var ecReq =
                dstore.DataFormatter.BuildTableEntry(dstoreEntries, dstore.DataStoreType, existDBDef, newTableDef);
            // submit dstore and entry change request for processing
            ProcessChangeRequest(dstore, ecReq);
        }

        public static List<TableDefinition> ReadAllTables(DataStore dstore, string dbName) {
            return dstore.DataFormatter.ReadTableDefinitions(
                dstore.DataLines.Select(x => x.Contents).ToList(),
                dstore.DataStoreType,
                ReadDB(dstore, dbName));
        }

        public static TableDefinition ReadTable(DataStore dstore, string dbName, string tableName) {
            // verify db
            var existDBDef = ReadDB(dstore, dbName);

            // verify table def
            var tableDef = dstore.DataFormatter.ReadTableDefinition(
                dstore.DataLines.Select(x => x.Contents).ToList(),
                dstore.DataStoreType,
                existDBDef,
                tableName);
            if (tableDef is null)
                throw new Exception(string.Format("Table \"{1}\" does not exist in database \"{0}\".", dbName, tableName));

            return tableDef;
        }

        public static void InsertRecord(DataStore dstore, string dbName, string tableName, object newRecordKey, IDictionary<string, object> fieldValues) {
            // grab current line contents
            var dstoreEntries = dstore.DataLines.Select(x => x.Contents).ToList();

            // verify db and table
            var exstDbDef = ReadDB(dstore, dbName);
            var exstTableDef = ReadTable(dstore, dbName, tableName);

            // verify record does not exist already
            if (newRecordKey != null) {
                var recordDef =
                    dstore.DataFormatter.ReadRecordData(
                        dstoreEntries,
                        dstore.DataStoreType,
                        exstDbDef,
                        exstTableDef,
                        newRecordKey);

                if (recordDef != null)
                    throw new Exception(
                        string.Format("Record with key \"{1}\" already exists in table \"{0}\".",
                                      tableName, newRecordKey)
                        );
            }
            else {
                // if new record does not have key throw exception
                throw new Exception(
                    string.Format("Record must provide a value for the key defined for table \"{0}\".", tableName)
                    );
            }

            // TODO: verify relationships to other records if any

            // build record data
            fieldValues[exstTableDef.Key.Name] = newRecordKey;
            var ecReq =
                dstore.DataFormatter.BuildRecordEntry(
                    dstoreEntries, dstore.DataStoreType, exstDbDef, exstTableDef, fieldValues
                    );
            // submit dstore and entry change request for processing
            ProcessChangeRequest(dstore, ecReq);
        }

        public static List<Dictionary<string, object>> ReadAllRecords(DataStore dstore, string dbName, string tableName) {
            // verify db and table
            var exstDbDef = ReadDB(dstore, dbName);
            var exstTableDef = ReadTable(dstore, exstDbDef.Name, tableName);

            return dstore.DataFormatter.ReadRecordsData(
                dstore.DataLines.Select(x => x.Contents).ToList(),
                dstore.DataStoreType,
                exstDbDef,
                exstTableDef);
        }

        public static Dictionary<string, object> ReadRecord(DataStore dstore, string dbName, string tableName, object recordKey) {
            // verify db and table
            var exstDbDef = ReadDB(dstore, dbName);
            var exstTableDef = ReadTable(dstore, exstDbDef.Name, tableName);

            var recordDef = dstore.DataFormatter.ReadRecordData(
                dstore.DataLines.Select(x => x.Contents).ToList(),
                dstore.DataStoreType,
                exstDbDef,
                exstTableDef,
                recordKey);

            if (recordDef is null)
                throw new Exception(string.Format("Record does not exist in table \"{0}\".", tableName));

            return recordDef;
        }

        public static void UpdateRecord(DataStore dstore, string dbName, string tableName, object recordKey, IDictionary<string, object> newFieldValues) {
            // grab current line contents
            var dstoreEntries = dstore.DataLines.Select(x => x.Contents).ToList();

            // verify db and table and record
            var exstDbDef = ReadDB(dstore, dbName);
            var exstTableDef = ReadTable(dstore, dbName, tableName);
            var recordDef = ReadRecord(dstore, dbName, tableName, recordKey);

            // verify record with new key does not exist already
            var targetRecordKey = GetTableKeyValue(exstTableDef, newFieldValues);
            if (targetRecordKey != null) {
                if (dstore.DataFormatter.ReadRecordData(dstoreEntries, dstore.DataStoreType, exstDbDef, exstTableDef, targetRecordKey) != null)
                    throw new Exception(
                        string.Format("Record with primary key already exists in the table (\"{0}\")",
                                      targetRecordKey)
                        );
            }

            // update the existing record data with new field values
            foreach (string fieldName in newFieldValues.Keys)
                recordDef[fieldName] = newFieldValues[fieldName];

            // build record data
            var ecReq =
                dstore.DataFormatter.UpdateRecordEntry(
                    dstoreEntries,
                    dstore.DataStoreType,
                    exstDbDef,
                    exstTableDef,
                    recordKey,
                    recordDef
                    );
            // submit dstore and entry change request for processing
            ProcessChangeRequest(dstore, ecReq);
        }

        public static void DropRecords(DataStore dstore, string dbName, string tableName) {
            // TODO: DropRecords
            throw new NotImplementedException();
        }

        public static void DropRecord(DataStore dstore, string dbName, string tableName, object recordKey) {
            // grab current line contents
            var dstoreEntries = dstore.DataLines.Select(x => x.Contents).ToList();

            // verify db and table and record
            var exstDbDef = ReadDB(dstore, dbName);
            var exstTableDef = ReadTable(dstore, dbName, tableName);
            var recordDef = ReadRecord(dstore, dbName, tableName, recordKey);

            // build record data
            var ecReq =
                dstore.DataFormatter.DropRecordEntry(
                    dstoreEntries,
                    dstore.DataStoreType,
                    exstDbDef,
                    exstTableDef,
                    recordKey
                    );
            // submit dstore and entry change request for processing
            ProcessChangeRequest(dstore, ecReq);
        }

        // privates
        private static object GetTableKeyValue(TableDefinition tableDef, IDictionary<string, object> fieldValues) {
            if (fieldValues.ContainsKey(tableDef.Key.Name))
                return fieldValues[tableDef.Key.Name];
            return null;
        }

        private static void ProcessChangeRequest(DataStore dstore, EntryChangeRequest ecReq) {
            if (ecReq != null) {
                // determine type of request and modify datastore datalines
                switch (ecReq.ChangeType) {
                    case EntryChangeType.Insert:
                        var newDline = new DataLine(ecReq.Entry, DataLineCommitType.Created);
                        // add data lines
                        if (ecReq.TargetIndex >= dstore.DataLines.Count)
                            dstore.DataLines.Add(newDline);
                        else
                            dstore.DataLines.Insert(ecReq.TargetIndex, newDline);
                        break;
                    case EntryChangeType.Remove:
                        var existingEntry = dstore.DataLines[ecReq.TargetIndex];
                        existingEntry.CommitType = DataLineCommitType.Dropped;
                        break;
                    case EntryChangeType.Replace:
                        dstore.DataLines[ecReq.TargetIndex] = new DataLine(ecReq.Entry, DataLineCommitType.Updated);
                        break;
                }
            }
        }
    }
}
