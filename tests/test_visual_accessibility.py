from pathlib import Path

from scripts.check_visual_accessibility import audit_stylesheet, contrast_ratio


ROOT = Path(__file__).resolve().parents[1]


def test_contrast_ratio_uses_wcag_relative_luminance() -> None:
    assert contrast_ratio("#000", "#fff") == 21
    assert round(contrast_ratio("#0284c7", "#ffffff"), 2) == 4.10


def test_visual_audit_fails_closed_on_low_contrast_or_missing_selector() -> None:
    css = (ROOT / "apps/web/src/styles/global.css").read_text(encoding="utf-8")
    low_contrast = css.replace("--color-control-border: #64748b", "--color-control-border: #cbd5e1")
    report = audit_stylesheet(low_contrast)
    assert report["passed"] is False
    assert "contrast.non_text.control_boundary.below_3" in report["blockers"]

    missing_focus = audit_stylesheet(css.replace(":focus-visible {", ":focus-visible-removed {", 1))
    assert missing_focus["passed"] is False
    assert "selector.:focus-visible.missing" in missing_focus["blockers"]


def test_repository_shared_styles_pass_visual_accessibility_audit() -> None:
    css = (ROOT / "apps/web/src/styles/global.css").read_text(encoding="utf-8")
    report = audit_stylesheet(css)
    assert report["audited_pair_count"] == 17
    assert report["blockers"] == []
    assert report["ratios"]["non_text.control_boundary"] >= 3
    assert report["ratios"]["text.subtle_canvas"] >= 4.5
