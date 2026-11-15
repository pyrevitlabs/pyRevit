namespace PyRevitLabs.PyRevit.Renderer {
    /// <summary>
    /// Why a renderer cannot show a browser view.
    ///
    /// The owner needs the reason, not only the fact: an absent Evergreen
    /// runtime is something the user can install, while a broken deployment is
    /// something only a reinstall fixes. Reporting both as "runtime missing"
    /// sends people to install a runtime they already have and hides the real
    /// fault.
    /// </summary>
    public enum RendererFailure {
        /// <summary>The renderer has not failed.</summary>
        None,

        /// <summary>The browser runtime is not installed; installing it fixes this.</summary>
        RuntimeMissing,

        /// <summary>The renderer or one of its dependencies could not be loaded.</summary>
        BrokenDeployment,
    }
}
