using pyRevitLabs.Configurations.Attributes;

namespace pyRevitLabs.Configurations;

[SectionName("environment")]
public record EnvironmentSection
{
    [KeyName("sources")]
    public List<string> Sources { get; set; } = new();
    
    [KeyName("clones")]
    public Dictionary<string, string> Clones { get; set; } = new();
}