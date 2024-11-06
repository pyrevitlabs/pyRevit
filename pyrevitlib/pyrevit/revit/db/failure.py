"""Revit failures handler."""
from pyrevit import HOST_APP, DB
from pyrevit import framework
from pyrevit import coreutils
from pyrevit.coreutils.logger import get_logger
from pyrevit.compat import get_elementid_value_func


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


# order is important. ordered from least destructive to most
# the resolver checks whether each one of these resolution types is
# applicable to the failure and applies if applicable
RESOLUTION_TYPES = [DB.FailureResolutionType.MoveElements,
                    DB.FailureResolutionType.CreateElements,
                    DB.FailureResolutionType.DetachElements,
                    DB.FailureResolutionType.FixElements,
                    DB.FailureResolutionType.UnlockConstraints,
                    DB.FailureResolutionType.SkipElements,
                    DB.FailureResolutionType.DeleteElements,
                    DB.FailureResolutionType.QuitEditMode,
                    DB.FailureResolutionType.SetValue,
                    DB.FailureResolutionType.SaveDocument]


# see FailureProcessingResult docs
# http://www.revitapidocs.com/2018.1/f147e6e6-4b2e-d61c-df9b-8b8e5ebe3fcb.htm
# explains usage of FailureProcessingResult options
class FailureSwallower(DB.IFailuresPreprocessor):
    """Swallows all failures."""
    def __init__(self, log_errors=True):
        self._logerror = log_errors
        self._failures_swallowed = []

    def _set_and_resolve(self, failuresAccessor, failure, res_type):
        failure_id = failure.GetFailureDefinitionId()
        failure_guid = getattr(failure_id, 'Guid', '')
        # mark as swallowed
        try:
            failure.SetCurrentResolutionType(res_type)
            failuresAccessor.ResolveFailure(failure)
            mlogger.debug('swallowed: %s', failure_guid)
            self._failures_swallowed.append(failure_id)
        except Exception as frex:
            mlogger.debug(
                'error setting resolution: %s | %s', res_type, frex
                )

    def get_swallowed_failures(self):
        failures = set()
        failure_reg = HOST_APP.app.GetFailureDefinitionRegistry()
        if failure_reg:
            for failure_id in self._failures_swallowed:
                failure_obj = failure_reg.FindFailureDefinition(failure_id)
                if failure_obj:
                    failures.add(failure_obj)
                else:
                    mlogger.debug(
                        'can not find failure definition for: %s', failure_id
                        )
        return failures

    def reset(self):
        """Reset swallowed errors."""
        self._failures_swallowed = []

    def preprocess_failures(self, failure_accessor):
        """Pythonic wrapper for `PreprocessFailures` interface method."""
        return self.PreprocessFailures(failure_accessor)

    def PreprocessFailures(self, failuresAccessor):
        """Required IFailuresPreprocessor interface method."""
        severity = failuresAccessor.GetSeverity()
        # log some info
        mlogger.debug('processing failure with severity: %s', severity)

        if severity == coreutils.get_enum_none(DB.FailureSeverity):
            mlogger.debug('clean document. returning with'
                          'FailureProcessingResult.Continue')
            return DB.FailureProcessingResult.Continue

        # log the failure messages
        failures = failuresAccessor.GetFailureMessages()
        mlogger.debug('processing %s failure messages.', len(failures))

        # go through failures and attempt resolution
        action_taken = False
        get_elementid_value = get_elementid_value_func()
        for failure in failures:

            failure_id = failure.GetFailureDefinitionId()
            failure_guid = getattr(failure_id, 'Guid', '')
            failure_severity = failure.GetSeverity()
            failure_desc = failure.GetDescriptionText()
            failure_has_res = failure.HasResolutions()

            # log failure info
            mlogger.debug('processing failure msg: %s', failure_guid)
            mlogger.debug('\tseverity: %s', failure_severity)
            mlogger.debug('\tdescription: %s', failure_desc)
            mlogger.debug('\telements: %s',
                          [get_elementid_value(x)
                           for x in failure.GetFailingElementIds()])
            mlogger.debug('\thas resolutions: %s', failure_has_res)

            # attempt resolution
            mlogger.debug('attempt resolving failure: %s', failure_guid)

            # if it's a warning and does not have any resolution
            # delete it! it might have a popup window
            if not failure_has_res \
                    and failure_severity == DB.FailureSeverity.Warning:
                failuresAccessor.DeleteWarning(failure)
                mlogger.debug(
                    'deleted warning with no acceptable resolution: %s',
                    failure_guid
                    )
                continue

            # find failure definition id
            # at this point the failure_has_res is True
            failure_def_accessor = get_failure_by_id(failure_id)
            default_res = failure_def_accessor.GetDefaultResolutionType()

            # iterate through resolution options, pick one and resolve
            for res_type in RESOLUTION_TYPES:
                if default_res == res_type:
                    mlogger.debug(
                        'using default failure resolution: %s', res_type)
                    self._set_and_resolve(failuresAccessor, failure, res_type)
                    action_taken = True
                    break
                elif failure.HasResolutionOfType(res_type):
                    mlogger.debug('setting failure resolution to: %s', res_type)
                    self._set_and_resolve(failuresAccessor, failure, res_type)
                    # marked as action taken
                    action_taken = True
                    break
                else:
                    mlogger.debug('invalid failure resolution: %s', res_type)

        # report back
        if action_taken:
            mlogger.debug('resolving failures with '
                          'FailureProcessingResult.ProceedWithCommit')
            return DB.FailureProcessingResult.ProceedWithCommit
        else:
            mlogger.debug('resolving failures with '
                          'FailureProcessingResult.Continue')
            return DB.FailureProcessingResult.Continue


def get_failure_by_guid(failure_guid):
    fdr = HOST_APP.app.GetFailureDefinitionRegistry()
    fgid = framework.Guid(failure_guid)
    fid = DB.FailureDefinitionId(fgid)
    return fdr.FindFailureDefinition(fid)


def get_failure_by_id(failure_id):
    fdr = HOST_APP.app.GetFailureDefinitionRegistry()
    return fdr.FindFailureDefinition(failure_id)
