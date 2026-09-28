"""Phase 0 test client for the pyRevit agent host.

Talks JSON-RPC over the host's named pipe, the same way the future
``pyrevit mcp`` server will. Standard library only; run it with any
Python 3 on the machine running Revit.

Examples:
    python agent_client.py instances
    python agent_client.py ping
    python agent_client.py context
    python agent_client.py engines
    python agent_client.py run scenarios/01_query_walls.py
    python agent_client.py run scenarios/03_set_comments.py --mode dry_run
"""

import argparse
import glob
import json
import os
import sys
import time

INSTANCES_DIR = os.path.join(
    os.environ.get("APPDATA", ""), "pyRevit", "agent", "instances"
)

CONNECT_TIMEOUT_S = 10

ENGINE_PROBE = "import sys\nresult = {'version': sys.version.split()[0]}\n"


def list_instances():
    """Return the registered host instances, newest first."""
    instances = []
    for path in glob.glob(os.path.join(INSTANCES_DIR, "*.json")):
        with open(path, encoding="utf-8") as handle:
            instance = json.load(handle)
        instance["file"] = path
        instances.append(instance)
    return sorted(instances, key=lambda item: item.get("started", ""), reverse=True)


def pick_pipe(pid):
    """Return the pipe name for ``pid``, or the newest registered instance."""
    instances = list_instances()
    if pid is not None:
        instances = [item for item in instances if item["pid"] == pid]
    if not instances:
        sys.exit("No running pyRevit agent host found in " + INSTANCES_DIR)
    return instances[0]["pipe"]


def call(pipe_name, method, params=None):
    """Send one JSON-RPC request and return the decoded response."""
    request = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    with _open_pipe(pipe_name) as pipe:
        pipe.write((json.dumps(request) + "\n").encode("utf-8"))
        return json.loads(pipe.readline().decode("utf-8"))


def _open_pipe(pipe_name):
    """Open the host pipe, waiting while it is busy.

    The host serves one connection at a time and re-creates the pipe after
    each one, so a call right after another can find it busy or briefly gone.
    """
    deadline = time.time() + CONNECT_TIMEOUT_S
    while True:
        try:
            return open("\\\\.\\pipe\\" + pipe_name, "r+b", buffering=0)
        except OSError:
            if time.time() > deadline:
                raise
            time.sleep(0.05)


def check_engines(pipe_name):
    """Run a probe on every engine get_context lists and check it keeps its word.

    An engine reported available must run the probe with status ok, on the
    implementation it names, at the Python version it advertises. An engine
    reported unavailable must refuse the run with ``engine_unavailable``.

    Returns:
        (bool): True when every engine behaved as advertised.
    """
    context = call(pipe_name, "get_context")["result"]
    all_passed = True
    for name, engine in sorted(context["scripting"]["engines"].items()):
        response = call(
            pipe_name,
            "run",
            {
                "script": ENGINE_PROBE,
                "mode": "query",
                "engine": name,
                "title": "engine probe",
            },
        )
        if engine["available"]:
            passed, detail = _check_available(engine, response)
        else:
            error = response.get("error") or {}
            error_type = (error.get("data") or {}).get("type")
            passed = error_type == "engine_unavailable"
            detail = "refused: " + str(error_type)
        all_passed = all_passed and passed
        print(
            "{:<11} {:<4} available={!s:<5} {}".format(
                name, "PASS" if passed else "FAIL", engine["available"], detail
            )
        )
    return all_passed


def _check_available(engine, response):
    run = response.get("result")
    if run is None:
        return False, "request failed: " + json.dumps(response.get("error"))
    if run["status"] != "ok":
        return False, "status {}: {}".format(run["status"], json.dumps(run["error"]))
    implementation = (run["engine"]["implementation"] or "").lower()
    ran = (run["result"] or {}).get("version")
    advertised = engine["python"]
    if implementation != engine["implementation"].lower():
        return False, "ran on {}, advertised {}".format(
            implementation, engine["implementation"]
        )
    if advertised and not ran.startswith(advertised):
        return False, "ran Python {}, advertised {}".format(ran, advertised)
    return True, "ran Python {}".format(ran)


def _main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--pid", type=int, help="target a specific Revit process")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("instances")
    commands.add_parser("ping")
    commands.add_parser("context")
    commands.add_parser("engines")
    run_parser = commands.add_parser("run")
    run_parser.add_argument("script")
    run_parser.add_argument(
        "--mode", default="query", choices=["query", "dry_run", "modify"]
    )
    run_parser.add_argument(
        "--engine", default="ironpython", choices=["ironpython", "cpython"]
    )
    run_parser.add_argument("--title")
    run_parser.add_argument(
        "--timeout", type=float, help="seconds before the host stops the script"
    )
    run_parser.add_argument(
        "--inputs", default="{}", help="JSON object passed to the script as `inputs`"
    )
    args = parser.parse_args()

    if args.command == "instances":
        print(json.dumps(list_instances(), indent=2))
        return

    pipe_name = pick_pipe(args.pid)
    if args.command == "ping":
        response = call(pipe_name, "ping")
    elif args.command == "context":
        response = call(pipe_name, "get_context")
    elif args.command == "engines":
        sys.exit(0 if check_engines(pipe_name) else 1)
    else:
        with open(args.script, encoding="utf-8") as handle:
            script = handle.read()
        params = {
            "script": script,
            "mode": args.mode,
            "engine": args.engine,
            "title": args.title or os.path.basename(args.script),
            "inputs": json.loads(args.inputs),
        }
        if args.timeout is not None:
            params["timeout_s"] = args.timeout
        response = call(pipe_name, "run", params)
    print(json.dumps(response, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _main()
