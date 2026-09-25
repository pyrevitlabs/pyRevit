namespace pyRevitLabs.Configurations.Security;

/// <summary>
/// A credential for a private extension repository, in the shape it takes once
/// protected for storage.
/// </summary>
/// <remarks>
/// <para>
/// <see cref="Username"/> is not a secret on its own, but it is protected
/// together with <see cref="Secret"/> on purpose. Storing the pair in one blob
/// means the only way to clear a credential is to remove that blob, so a
/// migration can never delete a secret while leaving a stale username behind,
/// or the reverse.
/// </para>
/// <para>
/// Treat instances as secrets. The stored form is
/// <see cref="ExtensionCredentialProtector"/>.
/// </para>
/// </remarks>
public sealed record ExtensionCredential {
    /// <summary>Initializes an empty credential.</summary>
    public ExtensionCredential() {

    }

    /// <summary>Initializes the credential.</summary>
    /// <param name="username">Account name to send with the credential.</param>
    /// <param name="secret">Personal access token or password.</param>
    /// <param name="kind">Which of the two shapes <paramref name="secret"/> is.</param>
    public ExtensionCredential(string username, string secret, ExtensionCredentialKind kind) {
        Username = username;
        Secret = secret;
        Kind = kind;
    }

    /// <summary>Account name to send with the credential.</summary>
    public string Username { get; set; } = "";

    /// <summary>
    /// Personal access token or password. Never log this or write it to the
    /// config file in the clear.
    /// </summary>
    public string Secret { get; set; } = "";

    /// <summary>Which of the two credential shapes <see cref="Secret"/> is.</summary>
    public ExtensionCredentialKind Kind { get; set; }

    /// <summary>
    /// Describes the credential without the secret.
    /// </summary>
    /// <remarks>
    /// A <c>record</c> synthesizes <c>ToString</c> over every readable property,
    /// which would print the token into any log line, exception message or debug
    /// output that ever interpolates this type. Overriding it is the only thing
    /// standing between a routine diagnostic and a credential in a log file, and
    /// the Python counterpart's <c>__repr__</c> hides the secret for the same
    /// reason.
    /// </remarks>
    public override string ToString() =>
        $"ExtensionCredential {{ Username = {Username}, Secret = <hidden>, Kind = {Kind} }}";
}
