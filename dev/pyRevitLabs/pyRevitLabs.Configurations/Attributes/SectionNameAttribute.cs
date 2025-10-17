namespace pyRevitLabs.Configurations.Attributes;

[AttributeUsage(AttributeTargets.Class)]
internal sealed class SectionNameAttribute(string sectionName) : Attribute
{
    public string SectionName { get; } = sectionName;
}