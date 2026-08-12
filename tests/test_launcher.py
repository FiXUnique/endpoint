from pathlib import Path

from endpoint.launcher import build_parser, default_database_path


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
