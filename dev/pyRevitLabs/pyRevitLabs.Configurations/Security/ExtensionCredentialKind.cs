namespace pyRevitLabs.Configurations.Security;

/// <summary>
/// Which shape <see cref="ExtensionCredential.Secret"/> has. Recorded in the blob so
/// a reader need not infer it from the username.
/// </summary>
public enum ExtensionCredentialKind {
    /// <summary>
    /// A personal access token. The username is a host convention rather than a
    /// real account: GitHub expects <c>oauth2</c>, GitLab <c>x-access-token</c>.
    /// </summary>
    Token,

    /// <summary>A real account's password, for HTTP basic auth on a self-hosted forge.</summary>
    Password
}
