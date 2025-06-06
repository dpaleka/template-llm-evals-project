from pathlib import Path


def path_repo_root() -> Path:
    """Get the path to the root of the repository."""
    current_file = Path(__file__).resolve()
    return current_file.parent.parent.parent


def path_data_root() -> Path:
    """Get the path to the data root directory."""
    return path_repo_root() / "data"


def path_test_outputs() -> Path:
    """Get the path to the test outputs directory."""
    return path_data_root() / "test_outputs"


def path_src_root() -> Path:
    """Get the path to the src root directory."""
    return path_repo_root() / "src"


def path_tests_root() -> Path:
    """Get the path to the tests root directory."""
    return path_repo_root() / "tests"
