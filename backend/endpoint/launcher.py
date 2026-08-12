from __future__ import annotations

import argparse
import os
import platform
import socket
import threading
import webbrowser
from pathlib import Path


def default_database_path() -> Path:
    system = platform.system()
    if system == "Windows":
        root = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return root / "Endpoint" / "endpoint.db"
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Endpoint" / "endpoint.db"
    root = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return root / "endpoint" / "endpoint.db"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="endpoint",
        description="Run the Endpoint on-chain investigation application.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Listening address")
    parser.add_argument("--port", default=8765, type=int, help="Listening port")
    parser.add_argument("--rpc-url", help="Solana JSON-RPC URL")
    parser.add_argument("--data-dir", type=Path, help="Directory for investigation snapshots")
    parser.add_argument(
        "--no-browser", action="store_true", help="Do not open the UI automatically"
    )
    return parser


def available_port(host: str, requested_port: int, attempts: int = 20) -> int:
    """Return the requested local port or the next available one."""
    for port in range(requested_port, requested_port + attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
                candidate.bind((host, port))
        except OSError:
            continue
        return port
    raise RuntimeError(
        f"No available port found between {requested_port} and "
        f"{requested_port + attempts - 1}."
    )


def main() -> None:
    args = build_parser().parse_args()
    database_path = (args.data_dir / "endpoint.db") if args.data_dir else default_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    os.environ["DATABASE_PATH"] = str(database_path)
    if args.rpc_url:
        os.environ["SOLANA_RPC_URL"] = args.rpc_url

    port = available_port(args.host, args.port)
    url = f"http://{args.host}:{port}"
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    import uvicorn

    if port != args.port:
        print(
            f"Port {args.port} is already in use (possibly by an older Endpoint). "
            f"Starting this version on port {port} instead."
        )
    print(f"Endpoint {url}")
    print(f"Investigation data: {database_path}")
    print("Press Ctrl+C to stop.")
    uvicorn.run("endpoint.main:app", host=args.host, port=port, log_level="info")


if __name__ == "__main__":
    main()
