using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;

using pyRevitLabs.NLog;

namespace pyRevitLabs.DeffrelDB {
    internal class DefaultDataFormatter: IDataFormatter {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        // interface methods =========================================================================================

        // dstore
        public EntryChangeRequest BuildDataStoreEntry(List<string> dstoreEntries,
                                                      DataStoreType dstoreType) {
            var lineParts = new List<string>();
            lineParts.Add(medataLineStart);
            lineParts.Add(buildMdataString(mdataDStore, dstoreType.TypeName));
            lineParts.Add(buildMdataString(mdataDStoreSource, dstoreType.Path));
            lineParts.Add(buildMdataString(mdataDStoreVersion, dstoreType.DataFormatVersion));
            lineParts.Add(buildMdataString(mdataDStoreEncoding, dstoreType.DataFormatEncoding.WebName.ToUpper()));

            return new EntryChangeRequest(EntryChangeType.Insert, 0, string.Join(mdataSeparator, lineParts));
        }

        public DataStoreType ReadDataStoreType(List<string> dstoreEntries) {
            DataStoreType dstoreType = null;

            var dstoreFinder = buildMdataRegex(mdataDStore, "dstoretype");
            var dstoreSourceFinder = buildMdataRegex(mdataDStoreSource, "dstorefile");
            var dstoreVersionFinder = buildMdataRegex(mdataDStoreVersion, "dstoreversion");
            var dstoreEncodingFinder = buildMdataRegex(mdataDStoreEncoding, "dstoreencoding");
            foreach (string dsEntry in dstoreEntries) {
                var match = dstoreFinder.Match(dsEntry);
                if (match.Success) {
                    var dbinfo = decodeValue(match.Groups["dstoretype"].Value);
                    var sourceMatch = dstoreSourceFinder.Match(dsEntry);
                    var versionMatch = dstoreVersionFinder.Match(dsEntry);
                    var encodingMatch = dstoreEncodingFinder.Match(dsEntry);
                    dstoreType = new DataStoreType(
                        dsource: decodeValue(sourceMatch.Groups["dstorefile"].Value),
                        dsourceVersion: new Version(decodeValue(versionMatch.Groups["dstoreversion"].Value)),
                        dsourceEncoding: Encoding.GetEncoding(decodeValue(encodingMatch.Groups["dstoreencoding"].Value))
                        );
                    break;
                }
            }

            return dstoreType;
        }

        // databases
        public EntryChangeRequest BuildDBEntry(List<string> dstoreEntries,
                                               DataStoreType dstoreType,
                                               DatabaseDefinition dbDef) {
            var lineParts = new List<string>();
            lineParts.Add(medataLineStart);
            lineParts.Add(mdataDBPrefix);
            lineParts.Add(buildMdataKeyValueString(mdataDB, dbDef.Name, dbDef.Description));

            var dstoreRange = extractDStoreRange(dstoreType.TypeName, dstoreEntries);

            return new EntryChangeRequest(
                EntryChangeType.Insert,
                dstoreRange.Last + 1,
                string.Join(mdataSeparator, lineParts)
                );
        }

        public List<DatabaseDefinition> ReadDBDefinitions(List<string> dstoreEntries,
                                                          DataStoreType dstoreType) {
            var dbDefsList = new List<DatabaseDefinition>();

            var dbFinder = buildMdataRegex(mdataDB, "dbinfo");
            foreach (string dsEntry in dstoreEntries) {
                var match = dbFinder.Match(dsEntry);
                if (match.Success) {
                    var dbinfo = decodeKeyValue(match.Groups["dbinfo"].Value);
                    dbDefsList.Add(new DatabaseDefinition(dbName: dbinfo.Key) {
                        Description = dbinfo.Value,
                    });
                }
            }

            return dbDefsList;
        }

        public DatabaseDefinition ReadDBDefinition(List<string> dstoreEntries,
                                                   DataStoreType dstoreType,
                                                   string dbName) {
            foreach (var dbDef in ReadDBDefinitions(dstoreEntries, dstoreType))
                if (dbDef.Name == dbName)
                    return dbDef;
            return null;
        }

        // tables
        public EntryChangeRequest BuildTableEntry(List<string> dstoreEntries,
                                                  DataStoreType dstoreType,
                                                  DatabaseDefinition dbDef,
                                                  TableDefinition tableDef) {
            // build table title line
            var lineParts = new List<string>();

            lineParts.Add(medataLineStart);
            if (mdataTablePrefix != string.Empty)
                lineParts.Add(mdataTablePrefix);

            lineParts.Add(buildMdataKeyValueString(mdataTable, tableDef.Name, tableDef.Description));
            lineParts.Add(buildMdataString(mdataTableFieldSeparator, tableDef.FieldDelimiter));
            lineParts.Add(buildMdataString(mdataTableInternal, tableDef.IsHidden));
            lineParts.Add(buildMdataString(mdataTableTags, tableDef.SupportsTags));
            lineParts.Add(buildMdataString(mdataTableHistory, tableDef.SupportsHistory));
            lineParts.Add(buildMdataString(mdataTableEncapsulation, tableDef.EncapsulateValues));
            lineParts.Add(buildMdataString(mdataTableHeaders, tableDef.SupportsHeaders));

            // build table fields
            if (tableDef.Key != null)
                lineParts.Add(buildMdataString(mdataTablePKField, tableDef.Key.Name, wrapInQuotes: false));
            else
                lineParts.Add(buildMdataString(mdataTablePKField, mdataNotSet));

            foreach (Field field in tableDef.Fields) {
                string typeKeyName;
                switch (field.FieldType) {
                    case FieldType.Boolean: typeKeyName = mdataFieldBool; break;
                    case FieldType.Byte: typeKeyName = mdataFieldByte; break;
                    case FieldType.Integer: typeKeyName = mdataFieldInteger; break;
                    case FieldType.Text: typeKeyName = mdataFieldText; break;
                    case FieldType.Date: typeKeyName = mdataFieldDate; break;
                    case FieldType.Time: typeKeyName = mdataFieldTime; break;
                    case FieldType.TimeStamp: typeKeyName = mdataFieldTimeStamp; break;
                    case FieldType.TimeStampTZ: typeKeyName = mdataFieldTimeStampTZ; break;
                    case FieldType.Decimal: typeKeyName = mdataFieldDecimal; break;
                    case FieldType.UUID: typeKeyName = mdataFieldUUID; break;
                    case FieldType.JSON: typeKeyName = mdataFieldJSON; break;
                    case FieldType.XML: typeKeyName = mdataFieldXML; break;
                    default:
                        typeKeyName = mdataFieldText; break;
                }

                // TODO: implement nullable property
                lineParts.Add(buildMdataKeyValueString(typeKeyName, field.Name, field.Description));
            }

            // build table wires
            foreach (Wire wire in tableDef.Wires) {
                lineParts.Add(buildMdataKeyValue(mdataTableFieldWire, wire.FromFieldName, wire.ToFieldName));
            }

            var dbRange = extractDBRange(dstoreType.TypeName, dstoreEntries, dbDef);

            return new EntryChangeRequest(
                EntryChangeType.Insert,
                dbRange.Last + 1,
                string.Join(mdataSeparator, lineParts)
                );
        }

        public List<TableDefinition> ReadTableDefinitions(List<string> dstoreEntries,
                                                          DataStoreType dstoreType,
                                                          DatabaseDefinition dbDef) {
            var tableList = new List<TableDefinition>();

            // find range of data lines for gien db
            var dbRange = extractDBRange(dstoreType.TypeName, dstoreEntries, dbDef);

            var tableFinder = buildMdataRegex(mdataTable, "tableinfo");
            var tableInternalFinder = buildMdataRegex(mdataTableInternal, "tableinternal");
            var tableHistFinder = buildMdataRegex(mdataTableHistory, "tablehistory");
            var tableSepFinder = buildMdataRegex(mdataTableFieldSeparator, "tablesep");
            var tableTagFinder = buildMdataRegex(mdataTableTags, "tabletags");

            // tabke key field finder
            var tableKeyFinder = buildMdataRegex(mdataTablePKField, "keyfieldname");
            // field and wire def finders
            var tableFieldDefsFinder = new Regex(mdataPrefix + mdataTablePKField
                                                 + "\\" + mdataValueOpen + ".*?" + "\\" + mdataValueClose
                                                 + "\\s(?<fielddefs>.*)");
            var tableFieldFinder = new Regex(mdataPrefix + "(?<fieldtype>.*?)"
                                             + "\\" + mdataValueOpen
                                             + "(?<fielddef>.*?)"
                                             + "\\" + mdataValueClose);

            foreach (string entryLine in dstoreEntries.GetRange(dbRange.First, dbRange.Count)) {
                var match = tableFinder.Match(entryLine);
                if (match.Success) {
                    var tableinfo = decodeKeyValue(match.Groups["tableinfo"].Value);
                    var internalMatch = tableInternalFinder.Match(entryLine);
                    var histMatch = tableHistFinder.Match(entryLine);
                    var sepMatch = tableSepFinder.Match(entryLine);
                    var tagsMatch = tableTagFinder.Match(entryLine);

                    var fields = new List<Field>();
                    var wires = new List<Wire>();

                    // find key field name
                    Field keyField = null;
                    var keyMatch = tableKeyFinder.Match(entryLine);
                    string keyFieldName = decodeValue(keyMatch.Groups["keyfieldname"].Value);

                    // find all defined fields
                    var fieldDefs = tableFieldDefsFinder.Match(entryLine).Groups["fielddefs"].Value;
                    foreach (Match fmatch in tableFieldFinder.Matches(fieldDefs)) {
                        Field newField = null;
                        Wire newWire = null;

                        var fieldType = decodeValue(fmatch.Groups["fieldtype"].Value);
                        var fieldDefParts = decodeKeyValue(fmatch.Groups["fielddef"].Value);

                        switch (fieldType) {
                            case mdataFieldBool:
                                newField = new BooleanField(name: fieldDefParts.Key, description: fieldDefParts.Value); break;
                            case mdataFieldByte:
                                newField = new ByteField(name: fieldDefParts.Key, description: fieldDefParts.Value); break;
                            case mdataFieldInteger:
                                newField = new IntegerField(name: fieldDefParts.Key, description: fieldDefParts.Value); break;
                            case mdataFieldText:
                                newField = new TextField(name: fieldDefParts.Key, description: fieldDefParts.Value); break;
                            case mdataFieldDate:
                                newField = new DateField(name: fieldDefParts.Key, description: fieldDefParts.Value); break;
                            case mdataFieldTime:
                                newField = new TimeField(name: fieldDefParts.Key, description: fieldDefParts.Value); break;
                            case mdataFieldTimeStamp:
                                newField = new TimeStampField(name: fieldDefParts.Key, description: fieldDefParts.Value); break;
                            case mdataFieldTimeStampTZ:
                                newField = new TimeStampTZField(name: fieldDefParts.Key, description: fieldDefParts.Value); break;
                            case mdataFieldDecimal:
                                newField = new DecimalField(name: fieldDefParts.Key, description: fieldDefParts.Value); break;
                            case mdataFieldUUID:
                                newField = new UUIDField(name: fieldDefParts.Key, description: fieldDefParts.Value); break;
                            case mdataFieldJSON:
                                newField = new JSONField(name: fieldDefParts.Key, description: fieldDefParts.Value); break;
                            case mdataFieldXML:
                                newField = new XMLField(name: fieldDefParts.Key, description: fieldDefParts.Value); break;

                            // if field type is a wire
                            case mdataTableFieldWire:
                                newWire = new Wire(fromFieldName: fieldDefParts.Key,
                                                   toFieldName: fieldDefParts.Value);
                                break;

                            // default to generic if type is unknown
                            default:
                                newField = new Field(datatype: FieldType.Undefined, name: fieldDefParts.Key, description: fieldDefParts.Value); break;
                        }

                        if (newField != null) {
                            if (fieldDefParts.Key == keyFieldName)
                                keyField = newField;

                            fields.Add(newField);
                        }

                        if (newWire != null) {
                            wires.Add(newWire);
                        }
                    }

                    // TODO: implement nullable property read
                    // TODO: implement reaky @key (currently first field is considered key)

                    // create table def
                    tableList.Add(new TableDefinition(tableName: tableinfo.Key) {
                        Fields = fields,
                        Wires = wires,
                        Description = tableinfo.Value,
                        FieldDelimiter = decodeValue(sepMatch.Groups["tablesep"].Value),
                        SupportsTags = decodeValue(tagsMatch.Groups["tabletags"].Value) == mdataBoolTrue,
                        IsHidden = decodeValue(internalMatch.Groups["tableinternal"].Value) == mdataBoolTrue,
                        SupportsHistory = decodeValue(histMatch.Groups["tablehistory"].Value) == mdataBoolTrue,
                    });
                }
            }

            return tableList;
        }

        public TableDefinition ReadTableDefinition(List<string> dstoreEntries,
                                                   DataStoreType dstoreType,
                                                   DatabaseDefinition dbDef,
                                                   string tableName) {
            foreach (var tableDef in ReadTableDefinitions(dstoreEntries, dstoreType, dbDef))
                if (tableDef.Name == tableName)
                    return tableDef;
            return null;
        }

        // records
        public EntryChangeRequest BuildRecordEntry(List<string> dstoreEntries,
                                                   DataStoreType dstoreType,
                                                   DatabaseDefinition dbDef,
                                                   TableDefinition tableDef,
                                                   IDictionary<string, object> fieldValues) {

            var tableRange = extractTableRange(dstoreType.TypeName, dstoreEntries, dbDef, tableDef);

            return new EntryChangeRequest(
                EntryChangeType.Insert,
                tableRange.Last + 1,
                buildRecordentry(tableDef, fieldValues)
                );
        }

        public List<Dictionary<string, object>> ReadRecordsData(List<string> dstoreEntries,
                                                                DataStoreType dstoreType,
                                                                DatabaseDefinition dbDef,
                                                                TableDefinition tableDef) {
            var recordList = new List<Dictionary<string, object>>();

            // find table range
            var tableRange = extractTableRange(dstoreType.TypeName, dstoreEntries, dbDef, tableDef);

            // skip the table def line
            foreach (string entryLine in dstoreEntries.GetRange(tableRange.First + 1, tableRange.Count - 1)) {
                string cleanedDLine = entryLine;
                if (tableDef.IsHidden)
                    cleanedDLine = cleanedDLine.Replace(medataLineStart + mdataRecordSeparator, "");
                var fieldValues = cleanedDLine.Split(new string[] { tableDef.FieldDelimiter }, StringSplitOptions.None);
                var fieldValuesDict = new Dictionary<string, object>();
                int fieldIndex = 0;

                foreach (var field in tableDef.Fields) {
                    fieldValuesDict.Add(field.Name, decodeFieldValue(fieldValueString: fieldValues[fieldIndex],
                                                                     fieldType: field.FieldType));
                    fieldIndex++;
                }

                recordList.Add(fieldValuesDict);
            }

            return recordList;
        }

        public Dictionary<string, object> ReadRecordData(List<string> dstoreEntries,
                                                         DataStoreType dstoreType,
                                                         DatabaseDefinition dbDef,
                                                         TableDefinition tableDef,
                                                         object recordKey) {
            var tableKey = tableDef.Key;
            foreach (var record in ReadRecordsData(dstoreEntries, dstoreType, dbDef, tableDef)) {
                if (record.ContainsKey(tableKey.Name) && recordKey.Equals(record[tableKey.Name]))
                    return record;
            }
            return null;
        }

        public EntryChangeRequest UpdateRecordEntry(List<string> dstoreEntries,
                                                    DataStoreType dstoreType,
                                                    DatabaseDefinition dbDef,
                                                    TableDefinition tableDef,
                                                    object recordKey,
                                                    IDictionary<string, object> fieldValues) {
            var exstRecordFieldValues = ReadRecordData(dstoreEntries, dstoreType, dbDef, tableDef, recordKey);
            var exstRecordEntry = buildRecordentry(tableDef, exstRecordFieldValues);

            return new EntryChangeRequest(
                EntryChangeType.Replace,
                dstoreEntries.IndexOf(exstRecordEntry),
                buildRecordentry(tableDef, fieldValues)
                );
        }

        public EntryChangeRequest DropRecordEntry(List<string> dstoreEntries,
                                                  DataStoreType dstoreType,
                                                  DatabaseDefinition dbDef,
                                                  TableDefinition tableDef,
                                                  object recordKey) {
            var exstRecordFieldValues = ReadRecordData(dstoreEntries, dstoreType, dbDef, tableDef, recordKey);
            var exstRecordEntry = buildRecordentry(tableDef, exstRecordFieldValues);

            return new EntryChangeRequest(
                EntryChangeType.Remove,
                dstoreEntries.IndexOf(exstRecordEntry),
                exstRecordEntry
                );
        }


        // private methods ==========================================================================================

        // generic metadata
        private const string medataLineStart = "#";
        private const string mdataPrefix = "@";
        private const string mdataValueOpen = "(";
        private const string mdataValueSeparator = ":";
        private const string mdataValueClose = ")";
        private const string mdataSeparator = " ";
        private const string mdataRecordSeparator = " ";

        // values
        private const string mdataBoolTrue = "yes";
        private const string mdataBoolFalse = "no";
        private const string mdataNotSet = "none";
        private const string mdataNULL = "NULL";
        private const string mdataQuotation = "&quot;";
        private const string mdataTab = "\\t";
        private const string mdataAtSign = "&#64;";
        private const string mdataOpenParan = "&#40;";
        private const string mdataCloseParan = "&#41;";

        // dstore
        private const string mdataDStore = "datastore";
        private const string mdataDStoreSource = "source";
        private const string mdataDStoreVersion = "version";
        private const string mdataDStoreEncoding = "encoding";

        // db
        private const string mdataDBPrefix = "=====================";
        private const string mdataDB = "db";

        private const string dbLocksTableName = "locks_table";

        // tables
        private const string mdataTablePrefix = "---------------------";
        private const string mdataTable = "table";
        private const string mdataTablePKField = "key";
        private const string mdataTableFieldSeparator = "sep";
        private const string mdataTableInternal = "internal";
        private const string mdataTableTags = "tags";
        private const string mdataTableHistory = "history";
        private const string mdataTableEncapsulation = "encap";
        private const string mdataTableHeaders = "headers";
       
        private const string mdataFieldBool = "bool";
        private const string mdataFieldByte = "byte";
        private const string mdataFieldInteger = "int";
        private const string mdataFieldText = "text";
        private const string mdataFieldDate = "date";
        private const string mdataFieldTime = "time";
        private const string mdataFieldTimeStamp = "tstamp";
        private const string mdataFieldTimeStampTZ = "tstamptz";
        private const string mdataFieldDecimal = "decimal";
        private const string mdataFieldUUID = "uuid";
        private const string mdataFieldJSON = "json";
        private const string mdataFieldXML = "xml";

        private const string mdataTableFieldWire = "wire";

        private string wrapStringInQuotes(string value) {
            return "\"" + value + "\"";
        }

        private Regex buildMdataRegex(string dataname, string captureId) {
            return new Regex(mdataPrefix + dataname
                             + "\\" + mdataValueOpen
                             + "(?<" + captureId + ">.*?)"
                             + "\\" + mdataValueClose);
        }

        private string decodeValue(string valueString) {
            valueString = valueString.Replace("\"", "");
            valueString = valueString.Replace(mdataQuotation, "\"");
            valueString = valueString.Replace(mdataTab, "\t");
            valueString = valueString.Replace(mdataAtSign, "@");
            valueString = valueString.Replace(mdataOpenParan, "(");
            valueString = valueString.Replace(mdataCloseParan, ")");
            return valueString;
        }

        private KeyValuePair<string, string> decodeKeyValue(string valueString) {
            var keyValue = valueString.Split(new string[] { mdataValueSeparator }, StringSplitOptions.None);
            return new KeyValuePair<string, string>(keyValue[0], decodeValue(keyValue[1]));
        }

        private string encodeValue(object value, bool wrapInQuotes = true) {
            if (value is bool)
                return (bool)value ? mdataBoolTrue : mdataBoolFalse;

            string valueString = value.ToString();

            valueString = valueString.Replace("\t", mdataTab);
            valueString = valueString.Replace("\"", mdataQuotation);
            valueString = valueString.Replace("@", mdataAtSign);
            valueString = valueString.Replace("(", mdataOpenParan);
            valueString = valueString.Replace(")", mdataCloseParan);
            if (wrapInQuotes)
                valueString = wrapStringInQuotes(valueString);

            return valueString;
        }

        private object decodeFieldValue(string fieldValueString, FieldType fieldType) {
            if (fieldValueString == mdataNULL)
                return null;

            object fieldValueObj = null;

            // TODO: implement data types
            switch (fieldType) {
                case FieldType.Boolean: fieldValueObj = bool.Parse(fieldValueString); break;
                case FieldType.Byte: fieldValueObj = fieldValueObj.ToString(); break;
                case FieldType.Integer: fieldValueObj = int.Parse(fieldValueString); break;
                case FieldType.Text: fieldValueObj = fieldValueString; break;
                case FieldType.Date: fieldValueObj = fieldValueObj.ToString(); break;
                case FieldType.Time: fieldValueObj = fieldValueObj.ToString(); break;
                case FieldType.TimeStamp: fieldValueObj = fieldValueObj.ToString(); break;
                case FieldType.TimeStampTZ: fieldValueObj = fieldValueObj.ToString(); break;
                case FieldType.Decimal: fieldValueObj = decimal.Parse(fieldValueString); break;
                case FieldType.UUID: fieldValueObj = fieldValueString; break;
                case FieldType.JSON: fieldValueObj = fieldValueString; break;
                case FieldType.XML: fieldValueObj = fieldValueString; break;
                default:
                    fieldValueObj = fieldValueObj.ToString(); break;
            }

            return fieldValueObj;
        }

        private string encodeFieldValue(object fieldValue, FieldType fieldType) {
            if (fieldValue is null)
                return mdataNULL;

            string fieldValueString = "";
            // TODO: implement data types
            switch (fieldType) {
                case FieldType.Boolean: fieldValueString = fieldValue.ToString(); break;
                case FieldType.Byte: fieldValueString = fieldValue.ToString(); break;
                case FieldType.Integer: fieldValueString = fieldValue.ToString(); break;
                case FieldType.Text: fieldValueString = fieldValue.ToString(); break;
                case FieldType.Date: fieldValueString = fieldValue.ToString(); break;
                case FieldType.Time: fieldValueString = fieldValue.ToString(); break;
                case FieldType.TimeStamp: fieldValueString = fieldValue.ToString(); break;
                case FieldType.TimeStampTZ: fieldValueString = fieldValue.ToString(); break;
                case FieldType.Decimal: fieldValueString = fieldValue.ToString(); break;
                case FieldType.UUID: fieldValueString = fieldValue.ToString(); break;
                case FieldType.JSON: fieldValueString = fieldValue.ToString(); break;
                case FieldType.XML: fieldValueString = fieldValue.ToString(); break;
                default:
                    fieldValueString = fieldValue.ToString(); break;
            }

            return fieldValueString;
        }

        private string buildMdataString(string dataName, IEnumerable<object> values, bool wrapInQuotes = true) {
            var stringValues = new List<string>();
            foreach (var valueObj in values)
                stringValues.Add(valueObj.ToString());
            return string.Format("{0}{1}" + mdataValueOpen + "{2}" + mdataValueClose, mdataPrefix, dataName, string.Join(mdataValueSeparator, stringValues));
        }

        private string buildMdataString(string dataName, object dataObj, bool wrapInQuotes = true) {
            return buildMdataString(dataName, new List<object>() { encodeValue(dataObj, wrapInQuotes) });
        }

        private string buildMdataKeyValueString(string dataName, string dataKey, string dataValue) {
            return buildMdataString(dataName, new List<string>() { dataKey, encodeValue(dataValue) });
        }

        private string buildMdataKeyValue(string dataName, string dataKey, string dataValue) {
            return buildMdataString(dataName, new List<string>() { dataKey, dataValue });
        }

        private EntryRange extractRange(List<string> dstoreEntries,
                                                  string itemTag, string itemValue, bool keyvalue = false,
                                                  EntryRange relativeRange = null) {
            if (relativeRange is null) {
                relativeRange = new EntryRange();
                relativeRange.First = 0;
                relativeRange.Last = dstoreEntries.Count() - 1;
            }

            var range = new EntryRange();
            range.Total = dstoreEntries.Count();

            bool count = false;
            int counter = relativeRange.First;
            string captureName = "iteminfo";
            var itemFinder = buildMdataRegex(itemTag, captureName);

            foreach (string entryLine in dstoreEntries.GetRange(relativeRange.First, relativeRange.Count)) {
                // find def line
                var match = itemFinder.Match(entryLine);
                if (match.Success) {
                    bool itemsMatch = false;

                    if (keyvalue) {
                        var extractedValue = decodeKeyValue(match.Groups[captureName].Value);
                        itemsMatch = extractedValue.Key == itemValue;
                    }
                    else {
                        var extractedValue = decodeValue(match.Groups[captureName].Value);
                        itemsMatch = extractedValue == itemValue;
                    }

                    // start recording lines if def line found
                    if (itemsMatch) {
                        range.First = counter;
                        count = true;
                    }
                    else {
                        range.Last = counter - 1;
                        if (count) {
                            count = false;
                            break;
                        }
                    }
                }

                if (count)
                    range.Last = counter;
                else
                    range.First = range.Last = counter;

                counter++;
            }

            return range;
        }

        private EntryRange extractDStoreRange(string dstoreTypeName, List<string> dstoreEntries) => extractRange(dstoreEntries, mdataDStore, dstoreTypeName);

        private EntryRange extractDBRange(string dstoreTypeName, List<string> dstoreEntries, DatabaseDefinition dbDef) {
            var dstoreRange = extractDStoreRange(dstoreTypeName, dstoreEntries);
            return extractRange(dstoreEntries, mdataDB, dbDef.Name, keyvalue: true, relativeRange: dstoreRange);
        }

        private EntryRange extractTableRange(string dstoreTypeName, List<string> dstoreEntries, DatabaseDefinition dbDef, TableDefinition tableDef) {
            var dbRange = extractDBRange(dstoreTypeName, dstoreEntries, dbDef);
            return extractRange(dstoreEntries, mdataTable, tableDef.Name, keyvalue: true, relativeRange: dbRange);
        }

        private string buildRecordentry(TableDefinition tableDef, IDictionary<string, object> fieldValues) {
            var recordParts = new List<string>();
            foreach (var field in tableDef.Fields) {
                if (fieldValues.ContainsKey(field.Name)) {
                    var fieldStringValue =
                        encodeFieldValue(fieldValue: fieldValues[field.Name], fieldType: field.FieldType);

                    recordParts.Add(
                        tableDef.EncapsulateValues ? wrapStringInQuotes(fieldStringValue) : fieldStringValue
                        );
                }
                else
                    recordParts.Add(mdataNULL);

            }
            string combinedRecord = string.Join(tableDef.FieldDelimiter, recordParts);

            // internal data always start with medataLineStart
            if (tableDef.IsHidden)
                combinedRecord = medataLineStart + mdataRecordSeparator + combinedRecord;

            return combinedRecord;
        }
    }
}
