"""Tests for PronunciationAgent schemas and output parsing."""

import pytest

from backend.agents.pronunciation.schemas import PronunciationInput, PronunciationOutput


def test_pronunciation_input_validation():
    data = {"text": "Hello world", "languages": ["zh", "en"]}
    input_model = PronunciationInput.model_validate(data)
    assert input_model.text == "Hello world"
    assert input_model.languages == ["zh", "en"]


def test_pronunciation_input_default_languages():
    input_model = PronunciationInput(text="Test")
    assert input_model.languages == ["zh", "en", "ja"]


def test_pronunciation_output_json_parse():
    raw = '{"zh": {"text": "你好", "pinyin": "ni3 hao3"}, "en": {"text": "Hello", "phonetic": "/həˈloʊ/"}}'
    output = PronunciationOutput.from_llm_response(raw, languages=["zh", "en"])
    assert output.translations["zh"]["pinyin"] == "ni3 hao3"
    assert output.translations["en"]["phonetic"] == "/həˈloʊ/"


def test_pronunciation_output_fallback_on_invalid_json():
    raw = "Not valid JSON at all"
    output = PronunciationOutput.from_llm_response(raw, languages=["zh"])
    assert "zh" in output.translations


def test_pronunciation_output_partial_lang_match():
    raw = '{"zh": {"text": "你好", "pinyin": "ni3"}}'
    output = PronunciationOutput.from_llm_response(raw, languages=["zh", "ja"])
    assert "zh" in output.translations
    assert "ja" in output.translations  # present but with fallback value
