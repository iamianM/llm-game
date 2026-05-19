"""Paradise Hearts display translation tests."""

from __future__ import annotations

from src.api.display import display


def test_display_translates_protected_terms() -> None:
    assert display("recoupling") == "Pairing Ceremony"
    assert display("snog_marry_pie") == "Kiss Wed Pass"
    assert display("casa_amor") == "Flush of Hearts"
    assert display("casa_amor_return_reveal") == "Sunset Bay Return"
    assert display("opening") == "First Spark"
    assert display("intros") == "Day-1 Introductions"
    assert display("main") == "Sunset Bay"
    assert display("bombshell") == "Heart Throb"
