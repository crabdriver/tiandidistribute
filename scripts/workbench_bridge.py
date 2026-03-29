#!/usr/bin/env python3

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tiandi_engine.results.publish_records import append_publish_record_at_path  # noqa: E402
from tiandi_engine.workbench.bridge import handle_bridge_command  # noqa: E402


def append_publish_record(result):
    append_publish_record_at_path(ROOT_DIR / "publish_records.csv", result)


def main():
    payload = json.load(sys.stdin)
    if payload.get("command") == "run_publish_job_stream":
        from tiandi_engine.workbench.bridge import run_publish_job

        result = run_publish_job(
            ROOT_DIR,
            payload["plan"],
            append_record=append_publish_record,
            event_sink=lambda event: (json.dump(event, sys.stdout, ensure_ascii=False), sys.stdout.write("\n"), sys.stdout.flush()),
        )
        json.dump({"type": "command_result", "payload": result}, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        return
    response = handle_bridge_command(ROOT_DIR, payload, append_record=append_publish_record)
    json.dump(response, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
