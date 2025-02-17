using System;
using System.Diagnostics;
using System.Linq;

namespace PyRevitLabs.PyRevit.Runtime {
    public static class DynamoDetector {
        private const string DYNAMO_PROCESS_NAME = "Dynamo";
        private const string DYNAMO_ENV_VAR = "DYNAMO_PATH";
        
        public static bool IsRunningInDynamoContext() {
            // Check if running inside Dynamo process
            var currentProcess = Process.GetCurrentProcess();
            var parentProcess = ParentProcessUtilities.GetParentProcess(currentProcess.Id);
            return parentProcess != null && 
                   parentProcess.ProcessName.Contains(DYNAMO_PROCESS_NAME);
        }

        public static bool IsDynamoInstalled() {
            return !string.IsNullOrEmpty(Environment.GetEnvironmentVariable(DYNAMO_ENV_VAR));
        }
    }
}