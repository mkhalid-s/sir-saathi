from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_public_data_policy_files_exist() -> None:
    assert (ROOT / ".gitignore").is_file()
    assert (ROOT / "data" / "README.md").is_file()
    assert (ROOT / "scripts" / "check_sensitive.py").is_file()


def test_raw_data_paths_are_ignored() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "data/**" in gitignore
    assert "!data/README.md" in gitignore
    assert "samples/**/*.pdf" in gitignore
