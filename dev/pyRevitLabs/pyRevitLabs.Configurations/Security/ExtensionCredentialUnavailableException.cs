namespace pyRevitLabs.Configurations.Security;

/// <summary>
/// A stored extension credential exists but cannot be turned back into a usable
/// secret.
/// </summary>
/// <remarks>
/// The causes - another Windows profile, a rebuilt profile, a config file copied
/// off the machine, tampered bytes - are indistinguishable and none is
/// recoverable in place, so the underlying cause is not surfaced. Callers must
/// treat this as "the user has to re-enter their token", never as "no credential
/// is configured": the latter makes a fetch fall back to anonymous and fail
/// pointing at the wrong problem.
/// </remarks>
/// <param name="message">Description of the failure.</param>
public sealed class ExtensionCredentialUnavailableException(string message) : Exceptions.ConfigurationException(message) {
    /// <summary>Initializes the exception with an empty message.</summary>
    public ExtensionCredentialUnavailableException() : this("") {

    }
}
