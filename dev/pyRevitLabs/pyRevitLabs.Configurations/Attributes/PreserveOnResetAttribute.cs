namespace pyRevitLabs.Configurations.Attributes;

/// <summary>
/// Marks a property whose stored value is user-registered state rather than a
/// preference, such as folders the user added. <see cref="Abstractions.IConfigurationService.ResetToDefaults"/>
/// leaves the key in place, because removing it would silently unregister what
/// the user set up.
/// </summary>
[AttributeUsage(AttributeTargets.Property)]
internal sealed class PreserveOnResetAttribute : Attribute {
}
