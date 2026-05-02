from __future__ import annotations

import argparse
from pathlib import Path

from task_tracker_emulator.server import load_mcp_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local MCP task tracker emulator.")
    parser.add_argument("--state-file", type=Path, required=True)
    parser.add_argument("--snapshot-file", type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8020)
    args = parser.parse_args()

    mcp, store = load_mcp_server(
        state_file=args.state_file,
        snapshot_file=args.snapshot_file,
        host=args.host,
        port=args.port,
    )
    print(f"Loaded task tracker state: {args.state_file}", flush=True)
    print(f"Snapshot file: {store.snapshot_file}", flush=True)
    print(f"MCP endpoint: http://{args.host}:{args.port}/mcp", flush=True)
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
