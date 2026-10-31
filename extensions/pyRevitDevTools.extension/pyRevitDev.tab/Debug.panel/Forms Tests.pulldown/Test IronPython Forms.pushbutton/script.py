"""Run IronPython forms acceptance against a rollback-only Revit fixture."""

from pyrevit import forms, script
from pyrevit.unittests import forms_acceptance


def _details(result):
    entries = []
    for name, error in result["failures"] + result["errors"]:
        entries.append("{}\n{}".format(name, error))
    return "\n\n".join(entries)


output = script.get_output()
result = forms_acceptance.run()
summary = "IronPython forms acceptance: {}/{} cases passed.".format(
    result["run"] - len(result["failures"]) - len(result["errors"]),
    result["run"],
)
print(summary)
print("Engine: {}".format(result["python"]))

if result["passed"]:
    forms.alert(summary, title="IronPython Forms", warn_icon=False)
else:
    forms.alert(
        summary,
        title="IronPython Forms Failed",
        expanded=_details(result),
        icon="error",
    )
    output.print_md("## {}".format(summary))
    output.print_md("```\n{}\n```".format(_details(result)))
