from pathlib import Path

from scripts.check_accessibility import audit_directory, audit_html


def test_accessibility_audit_accepts_a_structurally_accessible_page() -> None:
    html = """
    <html lang="en" dir="ltr"><head><title>Guide</title></head><body>
      <a class="skip-link" href="#main-content">Skip</a>
      <main id="main-content"><h1>Guide</h1>
        <label>Name <input id="name" aria-describedby="help"></label><p id="help">Help</p>
      </main>
    </body></html>
    """
    assert audit_html(html) == []


def test_accessibility_audit_reports_broken_references_and_unlabelled_controls() -> None:
    html = """
    <html><head><title></title></head><body><main id="duplicate"><main id="duplicate">
      <h1>One</h1><h1>Two</h1><input aria-describedby="missing">
    </main></main></body></html>
    """
    issues = audit_html(html)
    assert any("html lang is missing" in issue for issue in issues)
    assert any("expected exactly one main" in issue for issue in issues)
    assert any("duplicate id duplicate" in issue for issue in issues)
    assert any("references missing id missing" in issue for issue in issues)
    assert any("control has no accessible label" in issue for issue in issues)


def test_generated_nationwide_site_passes_structural_audit() -> None:
    dist = Path(__file__).resolve().parents[1] / "apps" / "web" / "dist"
    if not (dist / "404.html").exists():
        return
    report = audit_directory(dist)
    assert report["page_count"] == 43
    assert report["issues"] == []
