namespace pyRevitLabs.Configurations.Attributes;

/// <summary>
/// An older key name a property was stored under before it was renamed. Read
/// falls back to this key when the current <see cref="KeyNameAttribute"/> key
/// is absent, so every reader (loader, CLI, Python) agrees on the value
/// regardless of which key name a given config file still carries.
/// </summary>
[AttributeUsage(AttributeTargets.Property)]
internal sealed class LegacyKeyNameAttribute(string keyName) : Attribute
{
    public string KeyName { get; } = keyName;
}
