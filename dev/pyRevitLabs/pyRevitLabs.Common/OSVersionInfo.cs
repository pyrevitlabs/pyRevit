﻿using System;

namespace pyRevitLabs.Common
{
    // https://code.msdn.microsoft.com/windowsapps/How-to-determine-the-263b1850
    public class OSVersionInfo {

        public string FullName {
            get {
                return "Microsoft " + Name + " " + "[Version " + Major + "." + Minor + "." + Build + "]";
            }
        }

        public string Name { get; set; }
        public int Minor { get; set; }
        public int Major { get; set; }
        public int Build { get; set; }

        private OSVersionInfo() { }

        // Init OSVersionInfo object by current windows environment 
        public static OSVersionInfo GetOSVersionInfo() {
            OperatingSystem osVersionObj = Environment.OSVersion;

            OSVersionInfo osVersionInfo = new OSVersionInfo() {
                Name = GetOSName(osVersionObj),
                Major = osVersionObj.Version.Major,
                Minor = osVersionObj.Version.Minor,
                Build = osVersionObj.Version.Build
            };

            return osVersionInfo;
        }

        // Get current windows name 
        static string GetOSName(OperatingSystem osInfo) {
            string osName = "unknown";

            switch (osInfo.Platform) {
                //for old windows kernel 
                case PlatformID.Win32Windows:
                    osName = ForWin32Windows(osInfo);
                    break;
                //fow NT kernel 
                case PlatformID.Win32NT:
                    osName = ForWin32NT(osInfo);
                    break;
            }

            return osName;
        }

        // for old windows kernel 
        // this function is the child function for method GetOSName 
        static string ForWin32Windows(OperatingSystem osInfo) {
            string osVersion = "Unknown";

            //Code to determine specific version of Windows 95,  
            //Windows 98, Windows 98 Second Edition, or Windows Me. 
            switch (osInfo.Version.Minor) {
                case 0:
                    osVersion = "Windows 95";
                    break;
                case 10:
                    switch (osInfo.Version.Revision.ToString()) {
                        case "2222A":
                            osVersion = "Windows 98 Second Edition";
                            break;
                        default:
                            osVersion = "Windows 98";
                            break;
                    }
                    break;
                case 90:
                    osVersion = "Windows Me";
                    break;
            }

            return osVersion;
        }

        // fow NT kernel 
        // this function is the child function for method GetOSName 
        static string ForWin32NT(OperatingSystem osInfo) {
            string osVersion = "Unknown";

            //Code to determine specific version of Windows NT 3.51,  
            //Windows NT 4.0, Windows 2000, or Windows XP. 
            switch (osInfo.Version.Major) {
                case 3:
                    osVersion = "Windows NT 3.51";
                    break;
                case 4:
                    osVersion = "Windows NT 4.0";
                    break;
                case 5:
                    switch (osInfo.Version.Minor) {
                        case 0:
                            osVersion = "Windows 2000";
                            break;
                        case 1:
                            osVersion = "Windows XP";
                            break;
                        case 2:
                            osVersion = "Windows 2003";
                            break;
                    }
                    break;
                case 6:
                    switch (osInfo.Version.Minor) {
                        case 0:
                            osVersion = "Windows Vista";
                            break;
                        case 1:
                            osVersion = "Windows 7";
                            break;
                        case 2:
                            osVersion = "Windows 8";
                            break;
                        case 3:
                            osVersion = "Windows 8.1";
                            break;
                    }
                    break;
                case 10:
                    osVersion = "Windows 10";
                    break;
            }

            return osVersion;
        }
    }
}
