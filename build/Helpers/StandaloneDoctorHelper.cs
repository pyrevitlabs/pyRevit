namespace Build.Helpers;

/// <summary>
/// Keeps <c>pyrevit-doctor.exe</c> usable as a download on its own, without the rest of <c>bin/</c>.
/// </summary>
public static class StandaloneDoctorHelper
{
    /// <summary>
    /// Verifies that a <c>dotnet publish</c> of the doctor produced a single-file executable.
    /// </summary>
    /// <remarks>
    /// Invariant: the doctor project publishes with <c>PublishSingleFile</c>. Without it the executable is
    /// only a host that loads <c>pyrevit-doctor.dll</c> from its own folder, and the release asset, which
    /// is the executable alone, would not start.
    /// </remarks>
    /// <exception cref="FileNotFoundException">The publish output has no doctor executable.</exception>
    /// <exception cref="InvalidOperationException">
    /// The publish output holds the doctor as a separate assembly next to the executable.
    /// </exception>
    public static void EnsureSingleFilePublish(string publishDirectory)
    {
        var executable = Path.Combine(publishDirectory, PyRevitPaths.DoctorExeName);
        if (!File.Exists(executable))
        {
            throw new FileNotFoundException("The doctor publish output has no executable.", executable);
        }

        var separateAssembly = Path.ChangeExtension(executable, ".dll");
        if (File.Exists(separateAssembly))
        {
            throw new InvalidOperationException(
                $"{PyRevitPaths.DoctorExeName} was not published as a single file: {separateAssembly} exists. "
                + "The release ships the executable on its own, so keep PublishSingleFile enabled in "
                + "pyRevitDoctor.csproj.");
        }
    }

    /// <summary>
    /// Copies the doctor executable from <paramref name="binDirectory"/> to <paramref name="distDirectory"/>,
    /// replacing an earlier copy.
    /// </summary>
    /// <returns>The path of the staged copy.</returns>
    /// <exception cref="FileNotFoundException"><paramref name="binDirectory"/> has no doctor executable.</exception>
    public static string StageForRelease(string binDirectory, string distDirectory)
    {
        var source = Path.Combine(binDirectory, PyRevitPaths.DoctorExeName);
        if (!File.Exists(source))
        {
            throw new FileNotFoundException(
                "The doctor executable is missing from bin/. Run the ci build or restore the CI bin artifact first.",
                source);
        }

        Directory.CreateDirectory(distDirectory);
        var destination = Path.Combine(distDirectory, PyRevitPaths.DoctorExeName);
        File.Copy(source, destination, overwrite: true);
        return destination;
    }
}
