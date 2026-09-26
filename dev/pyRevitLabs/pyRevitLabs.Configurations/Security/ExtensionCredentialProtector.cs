using System.ComponentModel;
using System.Text;

namespace pyRevitLabs.Configurations.Security;

/// <summary>
/// Converts an <see cref="ExtensionCredential"/> to and from the single config
/// value that holds it, so a token or password is never written to the pyRevit
/// config file in the clear.
/// </summary>
/// <remarks>
/// <para><b>Stored format.</b> The three fields are base64-encoded, joined with
/// <c>'.'</c>, encoded as UTF-8, and sealed with DPAPI:</para>
/// <code>
/// base64( DPAPI.Protect( utf8( b64(kind) + "." + b64(username) + "." + b64(secret) ) ) )
/// </code>
/// <para>
/// Base64 never contains <c>'.'</c>, so the split is unambiguous on both sides
/// without either carrying a serializer dependency.
/// </para>
/// <para><b>Scope.</b> Sealed against the current Windows user only. Survives
/// pyRevit upgrades and config backups; unreadable after an OS reinstall without a
/// profile backup, on another machine, or under another account. That is why
/// <see cref="Unprotect"/> reports that case as its own exception instead of
/// returning nothing.</para>
/// <para><b>Coupling.</b> This format and <see cref="Entropy"/> are a
/// cross-language contract with <c>pyrevit.coreutils.credentials</c>, so a
/// credential written by the out-of-Revit CLI is readable by the in-Revit
/// extension manager. Changing either side alone orphans every stored
/// credential.</para>
/// </remarks>
public static class ExtensionCredentialProtector {
    /// <summary>
    /// Fixed entropy mixed into the DPAPI call. Not a secret: it binds a blob to
    /// pyRevit so an unrelated DPAPI ciphertext cannot be read back as a credential.
    /// </summary>
    public const string Entropy = "pyRevitLabs.ExtensionCredential.v1";

    /// <summary>Config key a sealed credential is stored under, inside its own extension's section.</summary>
    public const string ConfigKeyName = "credential";

    /// <summary>
    /// Every config key that can hold credential material: the sealed one plus the
    /// plaintext keys written before sealing existed. Kept as one list so that
    /// clearing plaintext and stripping a machine-scope config cannot drift apart.
    /// </summary>
    public static readonly IReadOnlyList<string> AllConfigKeyNames = new[]
    {
        ConfigKeyName,
        LegacyTokenKeyName,
        LegacyPasswordKeyName,
        LegacyUsernameKeyName
    };

    /// <summary>Legacy plaintext key holding a token. Read then removed by the migration.</summary>
    public const string LegacyTokenKeyName = "token";

    /// <summary>Legacy plaintext key holding a password. Read then removed by the migration.</summary>
    public const string LegacyPasswordKeyName = "password";

    /// <summary>Legacy plaintext key holding the username. Read then removed by the migration.</summary>
    public const string LegacyUsernameKeyName = "username";

    private const string FieldSeparator = ".";
    private const string KindTokenTag = "t";
    private const string KindPasswordTag = "p";

    private static readonly byte[] EntropyBytes = Encoding.UTF8.GetBytes(Entropy);

    /// <summary>Seals a credential for storage in a config value.</summary>
    /// <param name="credential">The credential to protect.</param>
    /// <returns>
    /// A base64 string safe to store as a config value. Pass it to
    /// <see cref="Unprotect"/> to recover the credential.
    /// </returns>
    /// <exception cref="ArgumentNullException">
    /// <paramref name="credential"/> is null, or its username or secret is null or
    /// blank. A blank username is rejected because every forge needs one, and
    /// sealing a half-filled credential only defers the failure to the first fetch.
    /// </exception>
    public static string Protect(ExtensionCredential credential) {
        if (credential is null)
            throw new ArgumentNullException(nameof(credential));
        if (string.IsNullOrWhiteSpace(credential.Username))
            throw new ArgumentException(
                "A credential username is required; every forge authenticates with a username and secret pair.",
                nameof(credential));
        if (string.IsNullOrWhiteSpace(credential.Secret))
            throw new ArgumentException(
                "A credential secret is required; use a null credential to clear a stored one instead.",
                nameof(credential));

        string payload = string.Join(
            FieldSeparator.ToString(),
            EncodeField(credential.Kind == ExtensionCredentialKind.Password ? KindPasswordTag : KindTokenTag),
            EncodeField(credential.Username),
            EncodeField(credential.Secret));

        return Convert.ToBase64String(
            Dpapi.Protect(payload, EntropyBytes, description: null));
    }

    /// <summary>Recovers a credential sealed by <see cref="Protect"/>.</summary>
    /// <param name="storedValue">The base64 value read from the config file.</param>
    /// <returns>The recovered credential.</returns>
    /// <exception cref="ExtensionCredentialUnavailableException">
    /// The value is not a readable pyRevit credential: sealed under a different
    /// profile or app version, truncated, tampered with, or not a credential at
    /// all. Ask the user to re-enter the token; do not fall back to an anonymous
    /// fetch.
    /// </exception>
    public static ExtensionCredential Unprotect(string? storedValue) {
        if (string.IsNullOrWhiteSpace(storedValue))
            throw new ExtensionCredentialUnavailableException(
                "No stored credential value to decrypt.");

        string payload;
        try {
            byte[] sealedBytes = Convert.FromBase64String(storedValue);
            payload = Dpapi.Unprotect(sealedBytes, EntropyBytes, out _);
        }
        catch (Exception error) when (error is FormatException or ArgumentException
                                      or Win32Exception) {
            throw new ExtensionCredentialUnavailableException(
                "The stored extension credential could not be decrypted. It was encrypted for a different "
                + "Windows user or a different pyRevit version, or the config value was altered. Re-enter the "
                + "access token for this extension.");
        }

        string[] fields = payload.Split(FieldSeparator[0]);
        if (fields.Length != 3) {
            throw new ExtensionCredentialUnavailableException(
                "The stored extension credential is not in the expected format. Re-enter the access token "
                + "for this extension.");
        }

        ExtensionCredentialKind kind;
        try {
            kind = DecodeField(fields[0]) == KindPasswordTag
                ? ExtensionCredentialKind.Password
                : ExtensionCredentialKind.Token;
        }
        catch (FormatException) {
            throw new ExtensionCredentialUnavailableException(
                "The stored extension credential is not in the expected format. Re-enter the access token "
                + "for this extension.");
        }

        string username;
        string secret;
        try {
            username = DecodeField(fields[1]);
            secret = DecodeField(fields[2]);
        }
        catch (FormatException) {
            throw new ExtensionCredentialUnavailableException(
                "The stored extension credential is not in the expected format. Re-enter the access token "
                + "for this extension.");
        }

        return new ExtensionCredential(username, secret, kind);
    }

    /// <summary>Recovers a credential without throwing, for call sites that must degrade.</summary>
    /// <param name="storedValue">The base64 value read from the config file.</param>
    /// <param name="credential">The recovered credential, or null when it could not be decrypted.</param>
    /// <returns>
    /// True when <paramref name="credential"/> was recovered. False is reported
    /// through <see cref="ConfigurationDiagnostics.ReportWarning"/> so a silently
    /// anonymous fetch stays attributable in the log.
    /// </returns>
    /// <remarks>
    /// Internal on purpose. This is the one entry point that downgrades an
    /// unreadable credential to "absent" - the confusion this design exists to
    /// avoid - so production callers should catch
    /// <see cref="ExtensionCredentialUnavailableException"/> and act on it.
    /// </remarks>
    internal static bool TryUnprotect(string? storedValue, out ExtensionCredential? credential) {
        try {
            credential = Unprotect(storedValue);
            return true;
        }
        catch (ExtensionCredentialUnavailableException error) {
            credential = null;
            ConfigurationDiagnostics.ReportWarning(
                "A stored extension credential could not be decrypted and will be treated as absent: "
                + error.Message);
            return false;
        }
    }

    private static string EncodeField(string value) =>
        Convert.ToBase64String(Encoding.UTF8.GetBytes(value));

    private static string DecodeField(string field) =>
        Encoding.UTF8.GetString(Convert.FromBase64String(field));
}
