using System.ComponentModel;
using pyRevitLabs.Configurations.Attributes;

namespace pyRevitLabs.Configurations.Sections;

/// <summary>
/// Per-extension settings read from a dynamic "{name}.extension" or "{name}.lib"
/// section. The section name is supplied at read time rather than fixed, so this
/// record carries no [SectionName]; callers resolve it via
/// <see cref="Abstractions.IConfigurationService.GetExtensionSection"/>.
/// </summary>
public sealed record ExtensionSection
{
    [KeyName("disabled")]
    [DefaultValue(false)]
    public bool? Disabled { get; set; }

    [KeyName("private_repo")]
    [DefaultValue(false)]
    public bool? PrivateRepo { get; set; }

    [KeyName("username")]
    public string? Username { get; set; }

    [KeyName("password")]
    public string? Password { get; set; }
}
