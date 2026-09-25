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
/// The <c>'.'</c> separator is unambiguous because the standard base64 alphabet
/// does not contain it, which is what lets the split be done identically from
/// C# and from Python without either side carrying a JSON dependency. A JSON
/// payload was rejected for the same reason: it would have meant taking a
/// serializer dependency in <c>pyRevitLabs.Configurations</c>, which
/// deliberately has none.
/// </para>
/// <para><b>Scope.</b> The blob is sealed against the current Windows user
/// only, binding it to the Windows user profile that created it. It survives
/// pyRevit upgrades and config backups, and it is unreadable after an OS
/// reinstall without a profile backup, on another machine, or under another
/// account. That is the trade for a secret that is not sitting in a
/// world-readable INI: a lost profile means re-entering the token, which is why
/// <see cref="Unprotect"/> reports that case as its own exception instead of
/// returning nothing.</para>
/// <para><b>Coupling.</b> <see cref="Entropy"/> and the stored format are a
/// cross-language contract. <c>pyrevit.coreutils.credentials</c> implements the
/// same format so that a credential written by the out-of-Revit CLI can be read
/// by the in-Revit extension manager, and the reverse. Changing either side
/// without the other orphans every stored credential, so the two must change
/// together.</para>
/// <para><b>Machine-scope configs.</b> The admin-locked config lives in
/// ProgramData and is readable by every user of the machine, so a user-scope
/// blob copied into it is both useless to them and worse than useless to its
/// owner. Nothing in this assembly writes one; the merge that would copy it is
/// responsible for skipping the credential key.</para>
/// </remarks>
public static class ExtensionCredentialProtector {
    /// <summary>
    /// Additional entropy mixed into the DPAPI call. Fixed, and not a secret:
    /// its job is to bind a blob to pyRevit so an unrelated DPAPI ciphertext
    /// cannot be dropped into the config key and read back as a credential.
    /// </summary>
    public const string Entropy = "pyRevitLabs.ExtensionCredential.v1";

    /// <summary>
    /// Config key a sealed credential is stored under, inside its own extension's
    /// section. Declared here rather than in a constants class so the key and the
    /// format it holds stay one contract across every assembly that touches it:
    /// the CLI writes it, the in-Revit extension manager writes and reads it, the
    /// admin-config merge refuses to copy it, and
    /// <c>pyrevit.coreutils.credentials</c> reads and writes it.
    /// </summary>
    public const string ConfigKeyName = "credential";

    /// <summary>
    /// Every config key that can hold extension credential material, the sealed
    /// one plus the plaintext keys written before sealing existed.
    /// </summary>
    /// <remarks>
    /// Declared here so that every place which has to treat credential material
    /// as one set - the CLI clearing plaintext after a re-persist, and the
    /// admin-config promotion stripping it from a machine-scope file - works from
    /// the same list. A new key added to only one of them is how a secret ends up
    /// in a file every local user can read.
    /// </remarks>
    public static readonly IReadOnlyList<string> AllConfigKeyNames = new[]
    {
        ConfigKeyName,
        LegacyTokenKeyName,
        LegacyPasswordKeyName,
        LegacyUsernameKeyName
    };

    /// <summary>Legacy plaintext key holding a token. Read only, then removed, by the migration.</summary>
    public const string LegacyTokenKeyName = "token";

    /// <summary>Legacy plaintext key holding a password. Read only, then removed, by the migration.</summary>
    public const string LegacyPasswordKeyName = "password";

    /// <summary>Legacy plaintext key holding the username. Read only, then removed, by the migration.</summary>
    public const string LegacyUsernameKeyName = "username";

    private const string FieldSeparator = ".";
    private const string KindTokenTag = "t";
    private const string KindPasswordTag = "p";

    private static readonly byte[] EntropyBytes = Encoding.UTF8.GetBytes(Entropy);

    /// <summary>
    /// Seals a credential for storage in a config value.
    /// </summary>
    /// <param name="credential">The credential to protect.</param>
    /// <returns>
    /// A base64 string safe to store as a config value. Pass it to
    /// <see cref="Unprotect"/> to recover the credential.
    /// </returns>
    /// <exception cref="ArgumentNullException">
    /// <paramref name="credential"/> is null, or its
    /// <see cref="ExtensionCredential.Username"/> or
    /// <see cref="ExtensionCredential.Secret"/> is null or blank. An empty
    /// username is rejected because every forge needs one, and rejecting it
    /// here keeps a half-filled credential from being sealed and then failing
    /// every fetch.
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

    /// <summary>
    /// Recovers a credential sealed by <see cref="Protect"/>.
    /// </summary>
    /// <param name="storedValue">The base64 value read from the config file.</param>
    /// <returns>The recovered credential.</returns>
    /// <exception cref="ExtensionCredentialUnavailableException">
    /// The value is not a readable pyRevit credential: it was sealed under a
    /// different profile or app version, it was truncated or tampered with, or
    /// it is not a credential at all. The caller must ask the user to re-enter
    /// the token rather than falling back to an anonymous fetch.
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

        // The payload came out of a successful DPAPI unseal, so it is well-formed
        // text here; only the field count can be wrong.
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

    /// <summary>
    /// Recovers a credential without throwing, for call sites that need to
    /// degrade rather than fail.
    /// </summary>
    /// <param name="storedValue">The base64 value read from the config file.</param>
    /// <param name="credential">The recovered credential, or null when it could
    /// not be decrypted.</param>
    /// <returns>
    /// True when <paramref name="credential"/> was recovered. False is reported
    /// through <see cref="ConfigurationDiagnostics.Warn"/> so a silently
    /// anonymous fetch is still attributable in the log.
    /// </returns>
    public static bool TryUnprotect(string? storedValue, out ExtensionCredential? credential) {
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

    private static string DecodeField(string field) {
        // A malformed field is the only way to get here, since the bytes came
        // out of a successful DPAPI unseal.
        return Encoding.UTF8.GetString(Convert.FromBase64String(field));
    }
}
