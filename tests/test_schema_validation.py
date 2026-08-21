"""
Definition of Done: "Vision model produces structured output validated
against a schema; invalid responses are never trusted." These tests prove
ImageTags actually enforces that -- not just that it exists.
"""

import pytest
from pydantic import ValidationError

from app.schemas.image_tags import ImageTags, LOW_CONFIDENCE_THRESHOLD


def test_valid_tags_parse():
    raw = '{"subject": "red fox", "category": "animal", "attributes": ["orange fur", "wild"], "caption": "A red fox in a forest", "confidence": 0.94}'
    tags = ImageTags.model_validate_json(raw)
    assert tags.subject == "red fox"
    assert tags.confidence == 0.94
    assert tags.is_low_confidence is False


def test_missing_required_field_rejected():
    # No "confidence" -- must not silently default, must fail loudly.
    raw = '{"subject": "red fox", "category": "animal", "attributes": [], "caption": "A fox"}'
    with pytest.raises(ValidationError):
        ImageTags.model_validate_json(raw)


def test_confidence_out_of_range_rejected():
    raw = '{"subject": "red fox", "category": "animal", "attributes": [], "caption": "A fox", "confidence": 1.5}'
    with pytest.raises(ValidationError):
        ImageTags.model_validate_json(raw)


def test_confidence_negative_rejected():
    raw = '{"subject": "red fox", "category": "animal", "attributes": [], "caption": "A fox", "confidence": -0.1}'
    with pytest.raises(ValidationError):
        ImageTags.model_validate_json(raw)


def test_malformed_json_rejected():
    # Model wandered into prose instead of JSON -- must never be trusted.
    raw = "Sure! This looks like a red fox standing in a forest."
    with pytest.raises(ValidationError):
        ImageTags.model_validate_json(raw)


def test_empty_subject_rejected():
    raw = '{"subject": "", "category": "animal", "attributes": [], "caption": "A fox", "confidence": 0.9}'
    with pytest.raises(ValidationError):
        ImageTags.model_validate_json(raw)


def test_low_confidence_flagged_not_guessed():
    just_below = LOW_CONFIDENCE_THRESHOLD - 0.01
    raw = f'{{"subject": "something", "category": "animal", "attributes": [], "caption": "unclear", "confidence": {just_below}}}'
    tags = ImageTags.model_validate_json(raw)
    # Still parses (it's schema-valid) but must be flagged downstream.
    assert tags.is_low_confidence is True


def test_confidence_at_threshold_not_flagged():
    raw = f'{{"subject": "red fox", "category": "animal", "attributes": [], "caption": "A fox", "confidence": {LOW_CONFIDENCE_THRESHOLD}}}'
    tags = ImageTags.model_validate_json(raw)
    assert tags.is_low_confidence is False
