import socket
from pathlib import Path

from endpoint.launcher import available_port, build_parser, default_database_path


def test_launcher_defaults_to_localhost_and_bounded_port():
    args = build_parser().parse_args([])
    assert args.host == "127.0.0.1"
    assert args.port == 8765
    assert args.no_browser is False


def test_default_database_path_is_user_scoped():
    path = default_database_path()
    assert isinstance(path, Path)
    assert path.name == "endpoint.db"
    assert str(path).startswith(str(Path.home())) or "LOCALAPPDATA" in str(path).upper()


def test_launcher_uses_next_port_when_requested_port_is_occupied():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        occupied_port = listener.getsockname()[1]

        selected_port = available_port("127.0.0.1", occupied_port, attempts=2)

    assert selected_port == occupied_port + 1
