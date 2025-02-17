using System;
using System.Diagnostics;
using System.Runtime.InteropServices;

namespace PyRevitLabs.PyRevit.Runtime {
    internal static class ParentProcessUtilities {
        // Win32 API imports
        [DllImport("kernel32.dll")]
        static extern IntPtr OpenProcess(ProcessAccessFlags access, bool inheritHandle, int procId);
        
        [DllImport("kernel32.dll")]
        static extern bool CloseHandle(IntPtr handle);

        [Flags]
        enum ProcessAccessFlags : uint {
            QueryLimitedInformation = 0x00001000
        }

        [DllImport("ntdll.dll")]
        static extern int NtQueryInformationProcess(
            IntPtr processHandle, 
            int processInformationClass,
            ref PROCESS_BASIC_INFORMATION processInformation,
            int processInformationLength,
            out int returnLength);

        [StructLayout(LayoutKind.Sequential)]
        struct PROCESS_BASIC_INFORMATION {
            public IntPtr Reserved1;
            public IntPtr PebBaseAddress;
            public IntPtr Reserved2_0;
            public IntPtr Reserved2_1;
            public IntPtr UniqueProcessId;
            public IntPtr InheritedFromUniqueProcessId;
        }

        public static Process GetParentProcess(int pid) {
            try {
                var handle = OpenProcess(ProcessAccessFlags.QueryLimitedInformation, false, pid);
                if (handle == IntPtr.Zero) return null;

                try {
                    var pbi = new PROCESS_BASIC_INFORMATION();
                    int returnLength;
                    int status = NtQueryInformationProcess(handle, 0, ref pbi, Marshal.SizeOf(pbi), out returnLength);
                    if (status != 0) return null;

                    int parentPid = pbi.InheritedFromUniqueProcessId.ToInt32();
                    return Process.GetProcessById(parentPid);
                }
                finally {
                    CloseHandle(handle);
                }
            }
            catch {
                return null;
            }
        }
    }
}