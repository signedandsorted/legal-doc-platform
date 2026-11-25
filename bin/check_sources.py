#!/usr/bin/env python3
"""Read the official pages and record any change. Does not edit the drafts.

    python bin/check_sources.py

The desk also runs this once a day while it is open. A change waits for a person.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.source_watch import run_check


def main() -> int:
    result = run_check()
    print(f"Checked {result.get('checked_at')}")
    found = result.get("found") or []
    failed = result.get("failed") or []
    if not found and not failed:
        print("No change on the pages that could be read.")
    for item in found:
        print(f"CHANGED {item['title']} {item['url']}")
    for item in failed:
        print(f"UNREAD {item['title']}: {item['error']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
