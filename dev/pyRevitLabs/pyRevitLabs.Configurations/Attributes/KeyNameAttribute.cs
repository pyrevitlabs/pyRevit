namespace pyRevitLabs.Configurations.Attributes;

[AttributeUsage(AttributeTargets.Property)]
internal sealed class KeyNameAttribute(string keyName) : Attribute
{
    
    public string KeyName { get; } = keyName;
}