namespace pyRevitLabs.Configurations.Security;

/// <summary>
/// A stored extension credential exists but cannot be turned back into a
/// usable secret.
/// </summary>
/// <remarks>
/// <para>
/// Raised when the blob was encrypted under a different Windows profile, when
/// the machine's user profile was rebuilt without a backup, when the config
/// file was copied off the machine, or when the stored bytes were tampered
/// with. Those are indistinguishable from the outside, which is the point:
/// none of them is recoverable in place, so the underlying cause carries no
/// action and is deliberately not surfaced to the caller.
/// </para>
/// <para>
/// Callers must treat this as "the user has to re-enter their token", never as
/// "no credential is configured". Answering the latter makes a libgit2 fetch
/// fall back to an anonymous request and fail with a message about a missing
/// authentication callback, which points at the wrong problem entirely.
/// </para>
/// </remarks>
/// <param name="message">Description of the failure.</param>
public sealed class ExtensionCredentialUnavailableException(string message) : Exceptions.ConfigurationException(message) {
    /// <summary>Initializes the exception with an empty message.</summary>
    public ExtensionCredentialUnavailableException() : this("") {

    }
}
