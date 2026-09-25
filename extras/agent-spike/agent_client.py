"""Phase 0 test client for the pyRevit agent host.

Talks JSON-RPC over the host's named pipe, the same way the future
``pyrevit mcp`` server will. Standard library only; run it with any
Python 3 on the machine running Revit.

Examples:
    python agent_client.py instances
    python agent_client.py ping
    python agent_client.py context
    python agent_client.py run scenarios/01_query_walls.py
    python agent_client.py run scenarios/03_set_comments.py --mode dry_run
"""

import argparse
import glob
import json
import os
import sys

INSTANCES_DIR = os.path.join(
    os.environ.get("APPDATA", ""), "pyRevit", "agent", "instances"
)


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
    with open("\\\\.\\pipe\\" + pipe_name, "r+b", buffering=0) as pipe:
        pipe.write((json.dumps(request) + "\n").encode("utf-8"))
        return json.loads(pipe.readline().decode("utf-8"))


def _main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--pid", type=int, help="target a specific Revit process")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("instances")
    commands.add_parser("ping")
    commands.add_parser("context")
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
    else:
        with open(args.script, encoding="utf-8") as handle:
            script = handle.read()
        response = call(
            pipe_name,
            "run",
            {
                "script": script,
                "mode": args.mode,
                "engine": args.engine,
                "title": args.title or os.path.basename(args.script),
                "inputs": json.loads(args.inputs),
            },
        )
    print(json.dumps(response, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _main()
