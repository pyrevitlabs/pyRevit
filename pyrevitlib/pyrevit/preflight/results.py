"""Structured results of preflight checks.

A check reports what it found as findings, each with a rule, a status, a severity
and the ids of the elements involved, next to whatever it prints. The results of
one run can be written as JSON, JSON Lines or CSV, so model quality can be stored,
compared between runs and aggregated across models in tools such as Excel or
Power BI.

Deliberately free of pyrevit and Revit imports so a plain CPython test can load it
without a Revit host. Targets IronPython 2.7 as well as CPython 3, since 2.7 is the
default engine.
"""

import io
import json
import os
import time

SCHEMA_VERSION = 1

PATH_ENV_VAR = "PYREVIT_PREFLIGHT_RESULTS_PATH"

STATUS_PASS = "pass"
STATUS_FAIL = "fail"
FINDING_STATUSES = (STATUS_PASS, STATUS_FAIL)

STATUS_NOT_REPORTED = "not_reported"

SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_ERROR = "error"
SEVERITIES = (SEVERITY_INFO, SEVERITY_WARNING, SEVERITY_ERROR)

CSV_COLUMNS = (
    "started",
    "document_title",
    "document_path",
    "check_id",
    "check",
    "check_status",
    "rule",
    "status",
    "severity",
    "message",
    "element_id",
)

_CSV_SPECIAL_CHARS = (",", '"', "\r", "\n")

_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

_TEXT_TYPES = (type(""), type(b""), type(""))


def _to_text(value):
    """Coerces a value to text without depending on a str/unicode split absent in py2."""
    try:
        return unicode(value)  # noqa: F821  (IronPython 2 / Python 2)
    except NameError:
        return str(value)


def _utc_timestamp(epoch_seconds):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch_seconds))


def _require_text(value, field_name):
    if value is None or not _to_text(value).strip():
        raise ValueError("Preflight finding '%s' must not be empty." % field_name)
    return _to_text(value)


def element_id_value(element_id):
    """The integer value of an element id, on every supported Revit version.

    Accepts a plain integer, a Revit ``ElementId`` or an element. Revit 2024 and
    newer expose the id as ``ElementId.Value`` (64 bit); older versions only have
    ``ElementId.IntegerValue``.

    Invariant:
        An object with an ``Id`` is read through that ``Id`` before its own
        ``Value``: some elements, such as dimensions, have a ``Value`` that is
        not their id.

    Args:
        element_id (int | ElementId | Element): the id, or an element carrying one.

    Returns:
        int: the id value.

    Raises:
        TypeError: when no id can be read, or when given a boolean.
    """
    if isinstance(element_id, bool):
        raise TypeError("A boolean is not an element id.")
    if isinstance(element_id, _TEXT_TYPES):
        raise TypeError("Text is not an element id: %r." % (element_id,))
    if isinstance(element_id, int):
        return int(element_id)
    nested_id = getattr(element_id, "Id", None)
    if nested_id is not None and nested_id is not element_id:
        return element_id_value(nested_id)
    for attribute in ("Value", "IntegerValue"):
        value = getattr(element_id, attribute, None)
        if value is not None and not isinstance(value, bool):
            try:
                return int(value)
            except (TypeError, ValueError):
                pass
    try:
        return int(element_id)
    except (TypeError, ValueError):
        raise TypeError("Cannot read an element id from %r." % (element_id,))


def _element_id_values(element_ids):
    values = []
    seen = set()
    for element_id in element_ids or ():
        value = element_id_value(element_id)
        if value not in seen:
            seen.add(value)
            values.append(value)
    return values


class Finding(object):
    """One result of one rule of a preflight check.

    Invariant:
        ``rule`` and ``message`` are non-blank text, ``status`` is one of
        ``FINDING_STATUSES``, ``severity`` one of ``SEVERITIES``, ``element_ids``
        holds unique integers in reporting order, and ``data`` is JSON
        serializable. Invalid values raise when the finding is created, so a
        broken check fails while it runs rather than when results are written.

    Args:
        rule (str): stable id of the rule, such as ``"schedules.not-on-sheet"``.
            It is not translated, so results stay comparable across locales.
        message (str): what was found, for a person reading the result.
        status (str): ``STATUS_FAIL`` (default) or ``STATUS_PASS``.
        severity (str): ``SEVERITY_WARNING`` (default), ``SEVERITY_INFO`` or
            ``SEVERITY_ERROR``.
        element_ids (Iterable): ids, ``ElementId`` objects or elements.
        data (dict): optional extra values, such as a measured count.

    Raises:
        ValueError: for blank text, an unknown status or severity, or data that
            is not a JSON serializable dict.
        TypeError: for an element id that cannot be read.
    """

    def __init__(
        self,
        rule,
        message,
        status=STATUS_FAIL,
        severity=SEVERITY_WARNING,
        element_ids=None,
        data=None,
    ):
        if status not in FINDING_STATUSES:
            raise ValueError(
                "Unknown preflight finding status %r, expected one of %s."
                % (status, ", ".join(FINDING_STATUSES))
            )
        if severity not in SEVERITIES:
            raise ValueError(
                "Unknown preflight finding severity %r, expected one of %s."
                % (severity, ", ".join(SEVERITIES))
            )
        if data is not None:
            if not isinstance(data, dict):
                raise ValueError("Preflight finding data must be a dict.")
            try:
                json.dumps(data, sort_keys=True)
            except (TypeError, ValueError) as serialize_error:
                raise ValueError(
                    "Preflight finding data is not JSON serializable: %s"
                    % serialize_error
                )
        self.rule = _require_text(rule, "rule")
        self.message = _require_text(message, "message")
        self.status = status
        self.severity = severity
        self.element_ids = _element_id_values(element_ids)
        self.data = dict(data) if data else {}

    @property
    def failed(self):
        """bool: True when the finding reports a problem."""
        return self.status == STATUS_FAIL

    def to_dict(self):
        """The finding as JSON-ready values."""
        return {
            "rule": self.rule,
            "status": self.status,
            "severity": self.severity,
            "message": self.message,
            "element_ids": list(self.element_ids),
            "data": dict(self.data),
        }


class CheckResult(object):
    """Findings of one preflight check run on one document.

    Note:
        A run with no findings has the status ``STATUS_NOT_REPORTED``, never
        ``STATUS_PASS``: checks written before findings existed report nothing,
        and must not read as clean. A check that finds nothing wrong reports a
        ``STATUS_PASS`` finding.

    Args:
        check (str): display name of the check; it may be translated.
        check_id (str): stable id of the check, used to compare runs.
        extension (str): name of the extension that provides the check.
        document_title (str): title of the checked document.
        document_path (str): path of the checked document, empty when unsaved.
        started (float): start time in epoch seconds. Defaults to now.
    """

    def __init__(
        self,
        check,
        check_id=None,
        extension=None,
        document_title=None,
        document_path=None,
        started=None,
    ):
        self.check = _to_text(check)
        self.check_id = _to_text(check_id or check)
        self.extension = _to_text(extension or "")
        self.document_title = _to_text(document_title or "")
        self.document_path = _to_text(document_path or "")
        self.started = time.time() if started is None else started
        self.duration = 0.0
        self.findings = []

    def add(self, finding):
        """Appends a finding.

        Args:
            finding (Finding): the finding to append.

        Raises:
            TypeError: when given anything other than a ``Finding``.
        """
        if not isinstance(finding, Finding):
            raise TypeError("Expected a preflight Finding, got %r." % (finding,))
        self.findings.append(finding)

    def finish(self, findings=(), ended=None):
        """Adds the run's findings and records its duration.

        Args:
            findings (Iterable[Finding]): findings the check reported.
            ended (float): end time in epoch seconds. Defaults to now.
        """
        for finding in findings:
            self.add(finding)
        ended = time.time() if ended is None else ended
        self.duration = max(0.0, ended - self.started)

    @property
    def status(self):
        """str: ``fail``, ``pass``, or ``not_reported`` when there are no findings."""
        if not self.findings:
            return STATUS_NOT_REPORTED
        if any(finding.failed for finding in self.findings):
            return STATUS_FAIL
        return STATUS_PASS

    def summary(self):
        """Counts of findings by status and severity of failures, and of distinct elements.

        Returns:
            dict: ``findings``, ``passed``, ``failed``, ``elements`` and
            ``failed_by_severity`` with one count per severity.
        """
        failed = [finding for finding in self.findings if finding.failed]
        elements = set()
        for finding in self.findings:
            elements.update(finding.element_ids)
        return {
            "findings": len(self.findings),
            "passed": len(self.findings) - len(failed),
            "failed": len(failed),
            "elements": len(elements),
            "failed_by_severity": dict(
                (severity, len([f for f in failed if f.severity == severity]))
                for severity in SEVERITIES
            ),
        }

    def to_dict(self):
        """The result as JSON-ready values, in schema ``SCHEMA_VERSION``."""
        return {
            "schema_version": SCHEMA_VERSION,
            "check": self.check,
            "check_id": self.check_id,
            "extension": self.extension,
            "document": {"title": self.document_title, "path": self.document_path},
            "started": _utc_timestamp(self.started),
            "duration_s": round(self.duration, 3),
            "status": self.status,
            "summary": self.summary(),
            "findings": [finding.to_dict() for finding in self.findings],
        }

    def to_json(self, indent=None):
        """The result as a JSON document.

        Non-ASCII text is escaped, so the output is the same on every engine.

        Args:
            indent (int): indentation; None writes a single line.

        Returns:
            str: JSON text.
        """
        separators = (",", ": ") if indent else (",", ":")
        return _to_text(
            json.dumps(
                self.to_dict(),
                indent=indent,
                separators=separators,
                sort_keys=True,
                ensure_ascii=True,
            )
        )

    def csv_rows(self):
        """The result as rows matching ``CSV_COLUMNS``.

        A finding gets one row per element id, or a single row with an empty
        ``element_id`` when it names no element.

        Returns:
            list[list[str]]: rows of text values.
        """
        common = [
            _utc_timestamp(self.started),
            self.document_title,
            self.document_path,
            self.check_id,
            self.check,
            self.status,
        ]
        rows = []
        for finding in self.findings:
            prefix = common + [
                finding.rule,
                finding.status,
                finding.severity,
                finding.message,
            ]
            for element_id in finding.element_ids or [None]:
                element_text = "" if element_id is None else _to_text(element_id)
                rows.append(prefix + [element_text])
        return rows


def report_path():
    """The configured results path, or None when writing results is off.

    Returns:
        str: path from `PATH_ENV_VAR`, or None.
    """
    path = os.environ.get(PATH_ENV_VAR)
    if not path or not path.strip():
        return None
    return path.strip()


def _is_integer_text(text):
    try:
        int(text)
    except ValueError:
        return False
    return True


def _csv_field(value):
    text = _to_text(value)
    if text.startswith(_CSV_FORMULA_PREFIXES) and not _is_integer_text(text):
        text = "'" + text
    if any(char in text for char in _CSV_SPECIAL_CHARS):
        return '"' + text.replace('"', '""') + '"'
    return text


def _csv_line(values):
    return ",".join(_csv_field(value) for value in values) + "\r\n"


def _ensure_parent(path):
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)


def _is_empty_file(path):
    return not os.path.isfile(path) or os.path.getsize(path) == 0


def write(result, path=None):
    """Writes a check result, choosing the format from the file extension.

    - ``.json`` replaces the file with this result, indented.
    - ``.jsonl`` appends this result as one line, so a file can collect many runs.
    - ``.csv`` appends one row per finding and element, writing the header and a
      UTF-8 byte order mark first when the file is new or empty, so Excel reads
      non-ASCII names correctly. Text starting with ``=``, ``+``, ``-``, ``@``,
      a tab or a carriage return gets a leading apostrophe, so a spreadsheet
      shows it as text instead of running it as a formula.

    Parent folders are created as needed. The output is built before the file
    is opened, so a result that cannot be serialized leaves an existing file
    untouched.

    Warning:
        Appending is not safe across processes. Give concurrent runs, such as
        several Revit sessions checking models at once, their own files.

    Args:
        result (CheckResult): the result to write.
        path (str): destination file. Defaults to `PATH_ENV_VAR`; when that is
            unset nothing is written and None is returned.

    Returns:
        str: the path written, or None when writing results is off.

    Raises:
        ValueError: for a file extension other than .json, .jsonl or .csv.
    """
    if path is None:
        path = report_path()
    if path is None:
        return None

    extension = os.path.splitext(path)[1].lower()
    if extension not in (".json", ".jsonl", ".csv"):
        raise ValueError(
            "Preflight results path must end in .json, .jsonl or .csv: %s" % path
        )

    mode = "a"
    encoding = "utf-8"
    if extension == ".json":
        mode = "w"
        content = result.to_json(indent=2) + _to_text("\n")
    elif extension == ".jsonl":
        content = result.to_json() + _to_text("\n")
    else:
        lines = [_csv_line(row) for row in result.csv_rows()]
        if _is_empty_file(path):
            encoding = "utf-8-sig"
            lines.insert(0, _csv_line(CSV_COLUMNS))
        content = _to_text("").join(lines)

    _ensure_parent(path)
    with io.open(path, mode, encoding=encoding, newline="") as results_file:
        results_file.write(content)

    return path
