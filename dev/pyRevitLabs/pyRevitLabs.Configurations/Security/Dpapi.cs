using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Text;

namespace pyRevitLabs.Configurations.Security;

/// <summary>
/// Thin wrapper over the Windows Data Protection API (<c>crypt32</c>'s
/// <c>CryptProtectData</c> / <c>CryptUnprotectData</c>), which is what
/// <c>System.Security.Cryptography.ProtectedData</c> calls.
/// </summary>
/// <remarks>
/// <para>
/// It calls the Win32 API directly rather than using
/// <c>ProtectedData</c> because that type lives in a different assembly on each
/// target - inbox <c>System.Security</c> on .NET Framework, a NuGet package on
/// .NET Core - and the package's assembly is not part of the .NET shared
/// framework. pyRevit stages its assemblies explicitly, so a managed reference
/// here means shipping one more file, and any build path that forgets it fails
/// at runtime with a <see cref="FileNotFoundException"/> while every unit test
/// still passes. <c>crypt32</c> is part of Windows, so there is nothing to ship
/// and nothing to forget.
/// </para>
/// <para>
/// The blobs produced are byte-compatible with
/// <c>ProtectedData.Protect</c> for the same inputs and flags, so a value
/// written by either is readable by the other. That matters because
/// <c>pyrevit.coreutils.credentials</c> seals the same way from Python, where no
/// assembly reference is involved at all.
/// </para>
/// <para>
/// Scope is the current Windows user: <c>CRYPTPROTECT_LOCAL_MACHINE</c> is
/// deliberately not passed, so a blob is bound to the calling user's profile and
/// is unreadable under another account, on another machine, and after a profile
/// rebuild without a backup.
/// </para>
/// <para><b>Two kinds of memory, two owners.</b> Buffers this type rents go
/// through <see cref="Rent"/> and <see cref="Return"/>, which pair
/// <c>Marshal.AllocHGlobal</c> with <c>Marshal.FreeHGlobal</c>.
/// Buffers the OS returns through an out-parameter are released with
/// <c>LocalFree</c>, because <c>LocalAlloc</c> is what produced them. The two
/// must never be mixed: <c>Marshal.ZeroFreeGlobalAllocUnicode</c> pairs with
/// <c>Marshal.StringToHGlobalUni</c> and writes <c>GlobalSize(p) * 2</c> bytes,
/// so used on an <c>AllocHGlobal</c> block it overruns the allocation by its own
/// length on every call.</para>
/// </remarks>
internal static class Dpapi {
    private const string Crypt32 = "crypt32.dll";
    private const string Kernel32 = "kernel32.dll";

    /// <summary>Refuse to show a UI on failure. Mandatory: a prompt would hang Revit.</summary>
    private const int CryptProtectUiForbidden = 0x1;

    [StructLayout(LayoutKind.Sequential)]
    private struct DataBlob {
        public int CbData;
        public IntPtr PbData;
    }

    [DllImport(Crypt32, SetLastError = true, CharSet = CharSet.Unicode, ExactSpelling = true)]
    private static extern bool CryptProtectData(
        ref DataBlob inputData,
        string? description,
        ref DataBlob optionalEntropy,
        IntPtr reserved,
        IntPtr promptStruct,
        int flags,
        out DataBlob outputData);

    [DllImport(Crypt32, SetLastError = true, CharSet = CharSet.Unicode, ExactSpelling = true)]
    private static extern bool CryptUnprotectData(
        ref DataBlob inputData,
        out IntPtr description,
        ref DataBlob optionalEntropy,
        IntPtr reserved,
        IntPtr promptStruct,
        int flags,
        out DataBlob outputData);

    [DllImport(Kernel32, SetLastError = true)]
    private static extern IntPtr LocalFree(IntPtr handle);

    /// <summary>
    /// Seals a UTF-8 string against the current Windows user.
    /// </summary>
    /// <param name="plaintext">Text to protect.</param>
    /// <param name="entropy">Additional entropy mixed into the seal.</param>
    /// <param name="description">
    /// Optional label stored inside the blob, or null to omit it. Omitting it
    /// keeps the blob byte-for-byte the shape <c>ProtectedData.Protect</c>
    /// produces, which is what lets a value written by either implementation be
    /// read by the other.
    /// </param>
    /// <returns>The sealed bytes.</returns>
    /// <exception cref="Win32Exception">The API call failed.</exception>
    public static byte[] Protect(string plaintext, byte[] entropy, string? description) {
        IntPtr plainBuffer = IntPtr.Zero;
        IntPtr entropyBuffer = IntPtr.Zero;
        IntPtr outBuffer = IntPtr.Zero;
        byte[] plainBytes = Encoding.UTF8.GetBytes(plaintext);
        try {
            plainBuffer = Rent(plainBytes);
            entropyBuffer = Rent(entropy);

            DataBlob plainBlob = Blob(plainBytes, plainBuffer);
            DataBlob entropyBlob = Blob(entropy, entropyBuffer);
            if (!CryptProtectData(
                    ref plainBlob, description, ref entropyBlob, IntPtr.Zero, IntPtr.Zero,
                    CryptProtectUiForbidden, out var output))
                throw new Win32Exception(
                    Marshal.GetLastWin32Error(), "CryptProtectData failed.");

            outBuffer = output.PbData;
            return CopyFromUnmanaged(output);
        }
        finally {
            // OS-owned first, then everything this type rented.
            if (outBuffer != IntPtr.Zero)
                LocalFree(outBuffer);
            Return(plainBuffer, plainBytes);
            Return(entropyBuffer, entropy);
            Array.Clear(plainBytes, 0, plainBytes.Length);
        }
    }

    /// <summary>
    /// Unseals bytes produced by <see cref="Protect"/>.
    /// </summary>
    /// <param name="sealedBytes">The sealed bytes.</param>
    /// <param name="entropy">The same entropy passed to <see cref="Protect"/>.</param>
    /// <param name="description">Receives the blob's label, or null.</param>
    /// <returns>The recovered UTF-8 text.</returns>
    /// <exception cref="Win32Exception">
    /// The API call failed, which for DPAPI means the blob was sealed by another
    /// user or machine, the profile changed, or the bytes were altered.
    /// </exception>
    public static string Unprotect(
        byte[] sealedBytes, byte[] entropy, out string? description) {
        IntPtr sealedBuffer = IntPtr.Zero;
        IntPtr entropyBuffer = IntPtr.Zero;
        IntPtr outBuffer = IntPtr.Zero;
        IntPtr descriptionBuffer = IntPtr.Zero;
        try {
            sealedBuffer = Rent(sealedBytes);
            entropyBuffer = Rent(entropy);

            DataBlob sealedBlob = Blob(sealedBytes, sealedBuffer);
            DataBlob entropyBlob = Blob(entropy, entropyBuffer);
            if (!CryptUnprotectData(
                    ref sealedBlob, out descriptionBuffer, ref entropyBlob, IntPtr.Zero,
                    IntPtr.Zero, CryptProtectUiForbidden, out var output))
                throw new Win32Exception(
                    Marshal.GetLastWin32Error(), "CryptUnprotectData failed.");

            description = descriptionBuffer == IntPtr.Zero
                ? null
                : Marshal.PtrToStringUni(descriptionBuffer);
            outBuffer = output.PbData;

            byte[] recovered = CopyFromUnmanaged(output);
            try {
                return Encoding.UTF8.GetString(recovered);
            }
            finally {
                Array.Clear(recovered, 0, recovered.Length);
            }
        }
        finally {
            if (descriptionBuffer != IntPtr.Zero)
                LocalFree(descriptionBuffer);
            if (outBuffer != IntPtr.Zero)
                LocalFree(outBuffer);
            Return(sealedBuffer, sealedBytes);
            Return(entropyBuffer, entropy);
        }
    }

    /// <summary>
    /// Copies bytes into a rented unmanaged block, paired with <see cref="Return"/>.
    /// </summary>
    private static IntPtr Rent(byte[] bytes) {
        IntPtr buffer = Marshal.AllocHGlobal(Math.Max(bytes.Length, 1));
        if (bytes.Length > 0)
            Marshal.Copy(bytes, 0, buffer, bytes.Length);
        return buffer;
    }

    /// <summary>
    /// Scrubs and frees a block from <see cref="Rent"/>, or does nothing for a
    /// null handle so the caller's <c>finally</c> needs no guard.
    /// </summary>
    private static void Return(IntPtr buffer, byte[] lengthSource) {
        if (buffer == IntPtr.Zero)
            return;

        for (int i = 0; i < lengthSource.Length; i++)
            Marshal.WriteByte(buffer, i, 0);
        Marshal.FreeHGlobal(buffer);
    }

    private static DataBlob Blob(byte[] lengthSource, IntPtr buffer) =>
        new() { CbData = lengthSource.Length, PbData = buffer };

    private static byte[] CopyFromUnmanaged(DataBlob blob) {
        var bytes = new byte[blob.CbData];
        if (bytes.Length > 0)
            Marshal.Copy(blob.PbData, bytes, 0, bytes.Length);
        return bytes;
    }
}
