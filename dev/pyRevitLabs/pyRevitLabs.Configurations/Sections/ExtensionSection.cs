using System.ComponentModel;
using pyRevitLabs.Configurations.Attributes;

namespace pyRevitLabs.Configurations.Sections;

/// <summary>
/// Per-extension settings read from a dynamic "{name}.extension" or "{name}.lib"
/// section. The section name is supplied at read time rather than fixed, so this
/// record carries no [SectionName]; callers resolve it via
/// <see cref="Abstractions.IConfigurationService.GetExtensionSection"/>.
/// </summary>
/// <remarks>
/// Deliberately has no member for the stored credential. The credential is a
/// DPAPI-sealed blob under
/// <see cref="Security.ExtensionCredentialProtector.ConfigKeyName"/>, and
/// decrypting it is a separate, deliberate step - see
/// <see cref="Security.ExtensionCredentialProtector"/>. Reading it through a
/// typed property would hand every caller of this record a plaintext secret
/// without asking.
/// </remarks>
public sealed record ExtensionSection {
    /// <summary>
    /// Whether the extension is excluded from the session. Default false, so an
    /// extension with no stored setting loads.
    /// </summary>
    [KeyName("disabled")]
    [DefaultValue(false)]
    public bool? Disabled { get; set; }

    /// <summary>
    /// Whether the extension's repository needs authentication to update.
    /// Default false.
    /// <para>
    /// A hint, not the source of truth: pyRevit sets it for shipped extensions
    /// that have no credential at all, and a stored credential can outlive it
    /// being cleared. Test for an actual credential instead.
    /// </para>
    /// </summary>
    [KeyName("private_repo")]
    [DefaultValue(false)]
    public bool? PrivateRepo { get; set; }

    /// <summary>
    /// Account name used against a private extension repository. No default:
    /// unset means no credential is supplied.
    /// <para>
    /// Legacy. Read only by the one-time migration in
    /// <c>pyrevit.versionmgr.upgrade</c>, which seals the credential it belongs
    /// to and then removes this key.
    /// </para>
    /// </summary>
    [KeyName("username")]
    public string? Username { get; set; }

    /// <summary>
    /// Credential used against a private extension repository. No default:
    /// unset means no credential is supplied.
    /// <para>
    /// Legacy, and a real secret in the clear for any config that still has it.
    /// Read only by the one-time migration in
    /// <c>pyrevit.versionmgr.upgrade</c>, which seals it and then removes this
    /// key. Nothing writes it.
    /// </para>
    /// </summary>
    [KeyName("password")]
    public string? Password { get; set; }
}
