using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace pyRevitLabs.DeffrelDB {
    // data formatter
    public enum EntryChangeType {
        Insert,
        Remove,
        Replace,
    }

    public class EntryRange {
        public int First { get; set; } = 0;
        public int Last { get; set; } = 0;
        public int Total { get; set; } = 0;

        public int Count { get { return Last - First + 1; } }

        public override string ToString() {
            return string.Format("<DataFormatRange {0}:{1} of {2} count:{3}>", First, Last, Total, Count);
        }
    }

    public class EntryChangeRequest {
        public EntryChangeRequest(EntryChangeType changeType, int entryIndex, string entry) {
            ChangeType = changeType;
            TargetIndex = entryIndex;
            Entry = entry;
        }

        public EntryChangeType ChangeType { get; private set; }
        public int TargetIndex { get; private set; }
        public string Entry { get; private set; }
    }

    public interface IDataFormatter {
        // datastore formatting methods
        EntryChangeRequest BuildDataStoreEntry(List<string> dstoreEntries, DataStoreType dstoreType);
        DataStoreType ReadDataStoreType(List<string> dstoreEntries);

        // database formatting methods
        EntryChangeRequest BuildDBEntry(List<string> dstoreEntries, DataStoreType dstoreType, DatabaseDefinition dbDef);
        List<DatabaseDefinition> ReadDBDefinitions(List<string> dstoreEntries, DataStoreType dstoreType);
        DatabaseDefinition ReadDBDefinition(List<string> dstoreEntries, DataStoreType dstoreType, string dbName);

        // tables
        EntryChangeRequest BuildTableEntry(List<string> dstoreEntries, DataStoreType dstoreType, DatabaseDefinition dbDef, TableDefinition tableDef);
        List<TableDefinition> ReadTableDefinitions(List<string> dstoreEntries, DataStoreType dstoreType, DatabaseDefinition dbDef);
        TableDefinition ReadTableDefinition(List<string> dstoreEntries, DataStoreType dstoreType, DatabaseDefinition dbDef, string tableName);

        // records
        EntryChangeRequest BuildRecordEntry(List<string> dstoreEntries, DataStoreType dstoreType, DatabaseDefinition dbDef, TableDefinition tableDef, IDictionary<string, object> fieldValues);
        List<Dictionary<string, object>> ReadRecordsData(List<string> dstoreEntries, DataStoreType dstoreType, DatabaseDefinition dbDef, TableDefinition tableDef);
        Dictionary<string, object> ReadRecordData(List<string> dstoreEntries, DataStoreType dstoreType, DatabaseDefinition dbDef, TableDefinition tableDef, object recordKey);
        EntryChangeRequest UpdateRecordEntry(List<string> dstoreEntries, DataStoreType dstoreType, DatabaseDefinition dbDef, TableDefinition tableDef, object recordKey, IDictionary<string, object> fieldValues);
        EntryChangeRequest DropRecordEntry(List<string> dstoreEntries, DataStoreType dstoreType, DatabaseDefinition dbDef, TableDefinition tableDef, object recordKey);
    }
}
