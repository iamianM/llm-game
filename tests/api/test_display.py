"""Paradise Hearts display translation tests."""

from __future__ import annotations

from src.api.display import display, translate_text


def test_display_translates_protected_terms() -> None:
    assert display("recoupling") == "Pairing Ceremony"
    assert display("snog_marry_pie") == "Kiss Wed Pass"
    assert display("casa_amor") == "Flush of Hearts"
    assert display("casa_amor_return_reveal") == "Sunset Bay Return"
    assert display("opening") == "First Spark"
    assert display("intros") == "Day-1 Introductions"
    assert display("main") == "Sunset Bay"
    assert display("bombshell") == "Heart Throb"


def test_translate_text_hides_engine_enum_values() -> None:
    text = translate_text("Casa Amor return reveal: player chose return_with_original.")

    assert "return_with_original" not in text
    assert "Casa Amor" not in text
    assert text == "Sunset Bay return: player chose return with your original couple."
