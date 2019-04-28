using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace pyRevitLabs.DeffrelDB {
    // database
    public sealed class DatabaseDefinition {
        public DatabaseDefinition() { }

        public DatabaseDefinition(string dbName) {
            Name = dbName;
        }

        public string Name { get; private set; }

        public string Description = "";

        public override string ToString() {
            return string.Format("<DatabaseDefinition name:{0} desc:{1}>", Name, Description);
        }
    }

    // table
    public sealed class TableDefinition {
        public TableDefinition() { }

        public TableDefinition(string tableName) {
            Name = tableName;
        }

        public string Name { get; private set; }

        // table fields
        public IEnumerable<Field> Fields { get; set; } = new List<Field>();

        // table wires
        public IEnumerable<Wire> Wires { get; set; } = new List<Wire>();

        // first field is always treated as key
        public Field Key {
            get {
                return Fields.First();
            }
        }

        public string Description = "";
        public string FieldDelimiter { get; set; } = "\t";
        public bool IsHidden { get; set; } = false;
        public bool SupportsTags { get; set; } = true;
        public bool SupportsHistory { get; set; } = false;
        public bool EncapsulateValues { get; set; } = false;
        public bool SupportsHeaders { get; set; } = false;
    }

    // fields
    public enum FieldType {
        Undefined,
        Boolean,
        Byte,
        Integer,
        Text,
        Date,
        Time,
        TimeStamp,
        TimeStampTZ,
        Decimal,
        UUID,
        JSON,
        XML
    }

    public class Field {
        public Field(FieldType datatype, string name, string description = null, bool nullable = true) {
            FieldType = datatype;
            Name = name;
            Description = description;
            Nullable = nullable;
        }

        public FieldType FieldType { get; private set; }
        public string Name { get; private set; }
        public string Description { get; private set; }
        public bool Nullable { get; private set; }

        public override int GetHashCode() {
            return Name.GetHashCode();
        }
    }

    public class Wire {
        public Wire(string fromFieldName, string toFieldName) {
            FromFieldName = fromFieldName;
            ToFieldName = toFieldName;
        }

        public string FromFieldName { get; private set; }
        public string ToFieldName { get; private set; }

        public override int GetHashCode() {
            return (FromFieldName + ToFieldName).GetHashCode();
        }
    }

    public sealed class BooleanField : Field {
        public BooleanField(string name, string description = "") : base(FieldType.Boolean, name, description) { }
    }

    public sealed class ByteField : Field {
        public ByteField(string name, string description = "") : base(FieldType.Byte, name, description) { }
    }

    public sealed class IntegerField : Field {
        public IntegerField(string name, string description = "") : base(FieldType.Integer, name, description) { }
    }

    public sealed class TextField : Field {
        public TextField(string name, string description = "") : base(FieldType.Text, name, description) { }
    }

    public sealed class DateField : Field {
        public DateField(string name, string description = "") : base(FieldType.Date, name, description) { }
    }

    public sealed class TimeField : Field {
        public TimeField(string name, string description = "") : base(FieldType.Time, name, description) { }
    }

    public sealed class TimeStampField : Field {
        public TimeStampField(string name, string description = "") : base(FieldType.TimeStamp, name, description) { }
    }

    public sealed class TimeStampTZField : Field {
        public TimeStampTZField(string name, string description = "") : base(FieldType.TimeStampTZ, name, description) { }
    }

    public sealed class DecimalField : Field {
        public DecimalField(string name, string description = "") : base(FieldType.Decimal, name, description) { }
    }

    public sealed class UUIDField : Field {
        public UUIDField(string name, string description = "") : base(FieldType.UUID, name, description) { }
    }

    public sealed class JSONField : Field {
        public JSONField(string name, string description = "") : base(FieldType.JSON, name, description) { }
    }

    public sealed class XMLField : Field {
        public XMLField(string name, string description = "") : base(FieldType.XML, name, description) { }
    }

    public sealed class RecordCommitLog {
    }

    public sealed class RecordCommit {
    }
}
