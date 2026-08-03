using System.ComponentModel;
using pyRevitLabs.Configurations.Attributes;

namespace pyRevitLabs.Configurations.Sections;

/// <summary>
/// The <c>[routes]</c> section: the HTTP server that exposes Revit to external
/// callers. Null means "not set in the file"; see <see cref="CoreSection"/> for
/// how nulls resolve on read.
/// </summary>
[SectionName("routes")]
public sealed record RoutesSection
{
    /// <summary>Whether the routes server starts with the session. Default false.</summary>
    [KeyName("enabled")]
    [DefaultValue(false)]
    public bool? Status { get; set; }

    /// <summary>
    /// Address the server binds to. Default empty, which binds every available
    /// interface. Callers pass this straight to a socket bind, which rejects a
    /// null host.
    /// </summary>
    [KeyName("host")]
    [DefaultValue("")]
    public string? Host { get; set; }

    /// <summary>
    /// TCP port the server listens on. Default 48884. Each running Revit
    /// instance needs its own port.
    /// </summary>
    [KeyName("port")]
    [DefaultValue(48884)]
    public int? Port { get; set; }

    /// <summary>
    /// Whether the built-in pyRevit core API routes are registered alongside any
    /// extension-provided routes. Default false.
    /// </summary>
    [KeyName("core_api")]
    [DefaultValue(false)]
    public bool? LoadCoreApi { get; set; }
}
