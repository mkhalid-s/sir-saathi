import base64
import hashlib
from pathlib import Path

from scripts.check_csp import audit_directory, audit_html

ROOT = Path(__file__).resolve().parents[1]


def hash_source(content: str) -> str:
    digest = base64.b64encode(hashlib.sha256(content.encode()).digest()).decode()
    return f"'sha256-{digest}'"


def valid_page(script: str = "window.safe = true;") -> str:
    style = "body{color:#123}"
    policy = ";".join([
        "default-src 'none'", "base-uri 'none'", "object-src 'none'", "form-action 'self'",
        "img-src 'self' data:", "font-src 'self'",
        "connect-src 'self' https://challenges.cloudflare.com",
        "frame-src https://challenges.cloudflare.com", "worker-src 'self'", "manifest-src 'self'",
        f"script-src 'self' https://challenges.cloudflare.com {hash_source(script)}",
        f"style-src 'self' {hash_source(style)}",
    ])
    return f'<html><head><meta http-equiv="content-security-policy" content="{policy}"><style>{style}</style><script>{script}</script></head></html>'


def test_csp_audit_accepts_hash_bound_inline_content() -> None:
    issues, scripts, styles = audit_html(valid_page())
    assert issues == []
    assert len(scripts) == 1
    assert len(styles) == 1


def test_csp_audit_rejects_tampering_unsafe_sources_and_inline_attributes() -> None:
    tampered = valid_page().replace("window.safe = true;", "window.safe = false;")
    unsafe = valid_page().replace("script-src 'self'", "script-src 'self' 'unsafe-inline'").replace("<html>", '<html style="color:red" onload="bad()">')
    assert any("inline script hash" in issue for issue in audit_html(tampered)[0])
    issues = audit_html(unsafe)[0]
    assert any("unsafe source" in issue for issue in issues)
    assert any("inline style or event-handler" in issue for issue in issues)


def test_generated_nationwide_site_has_valid_hash_only_csp() -> None:
    report = audit_directory(ROOT / "apps/web/dist")
    assert report["page_count"] == 41
    assert report["inline_script_hash_count"] >= 1
    assert report["inline_style_hash_count"] >= 1
    assert report["passed"] is True
