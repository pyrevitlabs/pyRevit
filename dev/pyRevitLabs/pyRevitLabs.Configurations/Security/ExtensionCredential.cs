namespace pyRevitLabs.Configurations.Security;

/// <summary>
/// A credential for a private extension repository, in the shape it takes once
/// protected for storage.
/// </summary>
/// <remarks>
/// <see cref="Username"/> is protected together with <see cref="Secret"/> so that
/// clearing a credential cannot leave one behind without the other. Treat
/// instances as secrets.
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

    /// <summary>Personal access token or password. Never log or store this in the clear.</summary>
    public string Secret { get; set; } = "";

    /// <summary>Which of the two credential shapes <see cref="Secret"/> is.</summary>
    public ExtensionCredentialKind Kind { get; set; }

    /// <summary>Describes the credential without the secret.</summary>
    /// <remarks>
    /// A record's generated <c>ToString</c> prints every readable property, which
    /// would put the token into any log line or message that touches this type.
    /// A debugger or reflection can still reach <see cref="Secret"/>; hiding it
    /// from those would cost the value equality this type exists for.
    /// </remarks>
    public override string ToString() =>
        $"ExtensionCredential {{ Username = {Username}, Secret = <hidden>, Kind = {Kind} }}";
}
