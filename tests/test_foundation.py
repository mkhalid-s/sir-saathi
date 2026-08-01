from pathlib import Path

from scripts.check_sensitive import is_reviewed_non_secret_assignment

ROOT = Path(__file__).resolve().parents[1]


def test_public_data_policy_files_exist() -> None:
    assert (ROOT / ".gitignore").is_file()
    assert (ROOT / "data" / "README.md").is_file()
    assert (ROOT / "scripts" / "check_sensitive.py").is_file()


def test_sensitive_scanner_allows_only_exact_reviewed_public_binary_assets() -> None:
    scanner = (ROOT / "scripts/check_sensitive.py").read_text(encoding="utf-8")
    for name in ["apple-touch-icon.png", "icon-192.png", "icon-512.png", "icon-maskable-512.png"]:
        assert f'"apps/web/public/icons/{name}"' in scanner
    assert "rel_path not in PUBLIC_BINARY_ASSETS" in scanner


def test_sensitive_scanner_allows_only_the_exact_oidc_workflow_permission() -> None:
    workflow = ".github/workflows/release-artifact.yml"
    permission = "id-" + "token"
    assert is_reviewed_non_secret_assignment(workflow, f"  {permission}: write") is True
    assert is_reviewed_non_secret_assignment(workflow, f"  {permission}: secret-value") is False
    assert is_reviewed_non_secret_assignment("docs/example.yml", f"{permission}: write") is False
    assert is_reviewed_non_secret_assignment(workflow, f"api-{permission}: write") is False


def test_sensitive_scanner_allows_only_the_exact_disposable_ci_database_password() -> None:
    key = "POSTGRES_" + "PASSWORD"
    workflow = ".github/workflows/ci.yml"
    assert is_reviewed_non_secret_assignment(workflow, f"  {key}: sir-saathi-ci-only") is True
    assert is_reviewed_non_secret_assignment(workflow, f"  {key}: production-value") is False
    assert is_reviewed_non_secret_assignment("docs/example.yml", f"{key}: sir-saathi-ci-only") is False


def test_raw_data_paths_are_ignored() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "data/**" in gitignore
    assert "!data/README.md" in gitignore
    assert "samples/**/*.pdf" in gitignore
