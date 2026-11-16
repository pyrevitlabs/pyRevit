using System;
using System.Runtime.ExceptionServices;

using Autodesk.Revit.DB;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Runs a capture in a transaction group that is always rolled back, so nothing it changes
    /// stays in the model.
    /// </summary>
    internal static class AgentCaptureGroup {
        /// <summary>
        /// Changes the model with <paramref name="prepare"/> in one transaction, exports what it
        /// returns with <paramref name="export"/>, and rolls the whole group back.
        /// </summary>
        /// <remarks>
        /// Throws <c>capture_failed</c> unless the group starts and the transaction starts and
        /// commits; when the group did not start, no transaction is opened, and when the transaction
        /// did not start, <paramref name="prepare"/> does not run. A Revit
        /// <see cref="Autodesk.Revit.Exceptions.ApplicationException"/> becomes <c>capture_failed</c>
        /// with the text <paramref name="describeFailure"/> builds from its message; an
        /// <see cref="AgentException"/> from <paramref name="prepare"/> passes through.
        /// Invariant: once the group started, it is rolled back on every exit path.
        /// Warning: a rollback that does not return <c>RolledBack</c> or throws fails the capture with
        /// <c>rollback_incomplete</c>. When the capture already failed, that original exception is
        /// thrown instead with the same code and message, and the rollback problem is added to the error
        /// details as <c>rollback_failure</c> so the client sees it; any other exception type carries it
        /// only as <c>Data["rollback_failure"]</c>, which <see cref="RollbackFailureOf"/> reads for the request
        /// handler's <c>internal_error</c> details.
        /// </remarks>
        internal static string Run<TTarget>(Document doc, string transactionName, Func<TTarget> prepare,
            Func<TTarget, string> export, Func<string, string> describeFailure) {
            using (var group = new TransactionGroup(doc, "pyRevit Agent capture")) {
                if (group.Start() != TransactionStatus.Started)
                    throw new AgentException("capture_failed", describeFailure("Revit did not start the temporary capture group, so the view was not changed."));
                string result = null;
                ExceptionDispatchInfo failure = null;
                try {
                    result = Capture(doc, transactionName, prepare, export, describeFailure);
                }
                catch (Autodesk.Revit.Exceptions.ApplicationException ex) {
                    failure = ExceptionDispatchInfo.Capture(new AgentException("capture_failed", describeFailure(ex.Message)));
                }
                catch (Exception ex) {
                    failure = ExceptionDispatchInfo.Capture(ex);
                }
                var rollbackProblem = RollBack(group);
                if (failure == null && rollbackProblem != null)
                    throw new AgentException("rollback_incomplete", describeFailure(rollbackProblem));
                if (failure != null) {
                    if (rollbackProblem != null)
                        throw WithRollbackFailure(failure, rollbackProblem);
                    failure.Throw();
                }
                return result;
            }
        }

        /// <summary>
        /// The rollback problem <see cref="Run{TTarget}"/> attached to <paramref name="failure"/>, or
        /// <c>null</c> when it has none.
        /// </summary>
        internal static string RollbackFailureOf(Exception failure) {
            return failure.Data["rollback_failure"] as string;
        }

        private static Exception WithRollbackFailure(ExceptionDispatchInfo failure, string rollbackProblem) {
            if (!(failure.SourceException is AgentException original)) {
                failure.SourceException.Data["rollback_failure"] = rollbackProblem;
                return failure.SourceException;
            }
            var reported = new AgentException(original.Code, original.Message);
            reported.Details.Merge(original.Details);
            reported.Details["rollback_failure"] = rollbackProblem;
            return reported;
        }

        private static string Capture<TTarget>(Document doc, string transactionName, Func<TTarget> prepare,
            Func<TTarget, string> export, Func<string, string> describeFailure) {
            TTarget target;
            using (var transaction = new Transaction(doc, transactionName)) {
                var started = transaction.Start();
                if (started != TransactionStatus.Started)
                    throw new AgentException("capture_failed", describeFailure($"Revit did not start the temporary view change (status {started})."));
                target = prepare();
                var committed = transaction.Commit();
                if (committed != TransactionStatus.Committed)
                    throw new AgentException("capture_failed", describeFailure($"Revit did not commit the temporary view change (status {committed})."));
            }
            return export(target);
        }

        private static string RollBack(TransactionGroup group) {
            if (!group.HasStarted() || group.HasEnded())
                return null;
            try {
                var status = group.RollBack();
                return status == TransactionStatus.RolledBack
                    ? null
                    : $"Revit did not confirm the rollback of the temporary capture group (status {status}).";
            }
            catch (Exception ex) {
                return $"Revit could not roll back the temporary capture group: {ex.Message}";
            }
        }
    }
}
