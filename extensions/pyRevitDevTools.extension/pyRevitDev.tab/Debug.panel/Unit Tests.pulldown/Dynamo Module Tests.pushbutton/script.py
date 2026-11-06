"""Assert installed Dynamo starts and evaluates a fresh DesignScript token."""

import json

from pyrevit.unittests.test_dynamo_execution import assert_dynamo_execution

print(json.dumps(assert_dynamo_execution(), indent=2))
