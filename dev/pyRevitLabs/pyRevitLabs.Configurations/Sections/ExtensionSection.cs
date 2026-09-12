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
    /// <summary>
    /// Whether the extension is excluded from the session. Default false, so an
    /// extension with no stored setting loads.
    /// </summary>
    [KeyName("disabled")]
    [DefaultValue(false)]
    public bool? Disabled { get; set; }

    /// <summary>
    /// Whether the extension's repository needs authentication to update.
    /// Default false. When true, <see cref="Username"/> and
    /// <see cref="Password"/> are used for the fetch.
    /// </summary>
    [KeyName("private_repo")]
    [DefaultValue(false)]
    public bool? PrivateRepo { get; set; }

    /// <summary>
    /// Account name used against a private extension repository. No default:
    /// unset means no credential is supplied.
    /// </summary>
    [KeyName("username")]
    public string? Username { get; set; }

    /// <summary>
    /// Credential used against a private extension repository. Stored in the
    /// config file as plain text, so treat a config carrying one as a secret.
    /// No default: unset means no credential is supplied.
    /// </summary>
    [KeyName("password")]
    public string? Password { get; set; }
}
