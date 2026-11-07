using System;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    internal enum AgentRunMode {
        Query,
        DryRun,
        Modify,
    }

    /// <remarks>
    /// Ordered from strictest to loosest; <see cref="AgentRunDecision.Stricter"/> relies on it.
    /// </remarks>
    internal enum AgentPolicy {
        ReadOnly,
        Ask,
        Auto,
    }

    internal enum AgentRunVerdict {
        TransactionLeftOpen,
        ScriptFailed,
        OtherDocumentChanged,
        NoDocument,
        QueryRolledBack,
        QueryModifiedModel,
        NoChanges,
        DryRunRolledBack,
        PolicyReadOnly,
        AutoCommit,
        AskUser,
        UserApproved,
        UserDiscarded,
    }

    internal sealed class AgentRunFacts {
        public AgentRunMode Mode { get; set; }
        public bool HasDocument { get; set; }
        public bool TransactionLeftOpen { get; set; }
        public bool ScriptFailed { get; set; }
        public bool ChangedOtherOpenDocument { get; set; }
        public bool HasChanges { get; set; }
        public AgentPolicy Policy { get; set; }
    }

    /// <summary>
    /// The agent policy in force for the Revit session, which only loosens with the user's
    /// confirmation.
    /// </summary>
    /// <remarks>
    /// Invariant: every stricter policy the host acts on is recorded through
    /// <see cref="Start"/> or <see cref="Tighten"/>, so loosening from it later is always
    /// confirmed. The first policy recorded is trusted. A declined policy isn't asked about
    /// again until the config names a different one. Not thread-safe; the host uses it on the
    /// Revit main thread only.
    /// </remarks>
    internal sealed class AgentPolicyInForce {
        private AgentPolicy? inForce;
        private AgentPolicy? declined;

        /// <summary>
        /// Records <paramref name="configured"/> when it is at least as strict as the policy in
        /// force, and returns the policy in force.
        /// </summary>
        public AgentPolicy Tighten(AgentPolicy configured) {
            if (inForce == null || AgentRunDecision.Stricter(configured, inForce.Value) == configured) {
                inForce = configured;
                declined = null;
            }
            return inForce.Value;
        }

        /// <summary>
        /// The policy a run starts under. A looser <paramref name="configured"/> policy is
        /// adopted only when <paramref name="confirmLoosening"/>, called with the policy in force
        /// and the configured one, returns true.
        /// </summary>
        public AgentPolicy Start(AgentPolicy configured, Func<AgentPolicy, AgentPolicy, bool> confirmLoosening) {
            var current = Tighten(configured);
            if (current == configured || configured == declined)
                return current;
            if (!confirmLoosening(current, configured)) {
                declined = configured;
                return current;
            }
            inForce = configured;
            declined = null;
            return configured;
        }
    }

    /// <summary>
    /// Decides what happens to a finished agent run: roll back, commit, or ask the user.
    /// Pure logic with no Revit dependency; <see cref="AgentRunService"/> carries out the verdict.
    /// </summary>
    /// <remarks>
    /// Invariant: the checks are ordered by precedence. A left-open transaction, a script
    /// failure or a change to another open document always rolls back before mode or policy
    /// is considered, and only a modify run with changes can reach a commit.
    /// </remarks>
    internal static class AgentRunDecision {
        public static AgentPolicy Stricter(AgentPolicy first, AgentPolicy second) {
            return first <= second ? first : second;
        }

        public static AgentRunVerdict Decide(AgentRunFacts facts) {
            if (facts.TransactionLeftOpen)
                return AgentRunVerdict.TransactionLeftOpen;
            if (facts.ScriptFailed)
                return AgentRunVerdict.ScriptFailed;
            if (facts.ChangedOtherOpenDocument)
                return AgentRunVerdict.OtherDocumentChanged;
            if (!facts.HasDocument)
                return AgentRunVerdict.NoDocument;
            if (facts.Mode == AgentRunMode.Query)
                return facts.HasChanges ? AgentRunVerdict.QueryModifiedModel : AgentRunVerdict.QueryRolledBack;
            if (!facts.HasChanges)
                return AgentRunVerdict.NoChanges;
            if (facts.Mode == AgentRunMode.DryRun)
                return AgentRunVerdict.DryRunRolledBack;
            switch (facts.Policy) {
                case AgentPolicy.ReadOnly: return AgentRunVerdict.PolicyReadOnly;
                case AgentPolicy.Auto: return AgentRunVerdict.AutoCommit;
                default: return AgentRunVerdict.AskUser;
            }
        }

        public static string Status(AgentRunVerdict verdict) {
            switch (verdict) {
                case AgentRunVerdict.TransactionLeftOpen:
                case AgentRunVerdict.ScriptFailed:
                case AgentRunVerdict.OtherDocumentChanged:
                case AgentRunVerdict.QueryModifiedModel:
                    return "error";
                case AgentRunVerdict.PolicyReadOnly:
                case AgentRunVerdict.UserDiscarded:
                    return "rejected";
                default:
                    return "ok";
            }
        }

        public static string Decision(AgentRunVerdict verdict) {
            switch (verdict) {
                case AgentRunVerdict.NoDocument: return "no_document";
                case AgentRunVerdict.NoChanges: return "no_changes";
                case AgentRunVerdict.AutoCommit:
                case AgentRunVerdict.UserApproved: return "committed";
                case AgentRunVerdict.UserDiscarded: return "discarded";
                default: return "rolled_back";
            }
        }

        public static string Approval(AgentRunVerdict verdict) {
            switch (verdict) {
                case AgentRunVerdict.AutoCommit: return "auto";
                case AgentRunVerdict.UserApproved:
                case AgentRunVerdict.UserDiscarded: return "user";
                default: return null;
            }
        }
    }
}
