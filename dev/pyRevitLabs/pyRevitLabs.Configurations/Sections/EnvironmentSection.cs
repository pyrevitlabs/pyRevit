using pyRevitLabs.Configurations.Attributes;

namespace pyRevitLabs.Configurations.Sections;

[SectionName("environment")]
public record EnvironmentSection
{
    // No initializers: unset values stay null so a sparse-section save does not
    // rewrite (and clobber) the sibling key. CreateSection supplies empty
    // collections on read.
    [KeyName("sources")]
    public List<string>? Sources { get; set; }

    [KeyName("clones")]
    public Dictionary<string, string>? Clones { get; set; }
}
