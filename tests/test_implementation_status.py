from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_status_review_separates_implemented_work_from_external_evidence() -> None:
    status = (ROOT / "docs/IMPLEMENTATION_STATUS.md").read_text(encoding="utf-8")

    assert "All 36 states and union territories" in status
    assert "Public indexed search is disabled for every jurisdiction by default" in status
    assert "English is the only publishable catalogue" in status
    assert "Pending External Evidence" in status
    assert "must not be fabricated or auto-approved" in status
    assert "Production rehearsal without voter data" in status
    assert "One real roll onboarding pilot" in status
    assert "Autonomous Stop Conditions" in status
