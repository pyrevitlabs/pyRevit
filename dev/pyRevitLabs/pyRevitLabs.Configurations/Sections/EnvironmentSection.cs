using pyRevitLabs.Configurations.Attributes;

namespace pyRevitLabs.Configurations.Sections;

/// <summary>
/// The <c>[environment]</c> section: machine state pyRevit maintains for itself
/// rather than user preferences. Written by the CLI and the installer; editing
/// it by hand can desynchronize it from what is actually on disk. Null means
/// "not set in the file"; see <see cref="CoreSection"/> for how nulls resolve on
/// read.
/// </summary>
[SectionName("environment")]
public record EnvironmentSection
{
    // No initializers: unset values stay null so a sparse-section save does not
    // rewrite (and clobber) the sibling key. CreateSection supplies empty
    // collections on read.

    /// <summary>
    /// URLs of the extension definition files searched when looking up
    /// installable extensions. Read back as an empty list when unset.
    /// </summary>
    [KeyName("sources")]
    public List<string>? Sources { get; set; }

    /// <summary>
    /// Registered pyRevit clones, keyed by clone name with the install
    /// directory as the value. Read back as an empty dictionary when unset.
    /// </summary>
    [KeyName("clones")]
    public Dictionary<string, string>? Clones { get; set; }
}
