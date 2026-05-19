"""
Тести Pydantic схем — перевіряємо валідацію вхідних даних.
"""

import pytest
from pydantic import ValidationError

from app.schemas.profile import ProfileCreate, ProfilePreferences, ProfileUpdate


class TestProfileCreate:
    def test_valid_minimal(self):
        p = ProfileCreate(name="Test")
        assert p.name == "Test"
        assert p.complexity_level == 3
        assert p.domain == "general"

    def test_valid_full(self):
        p = ProfileCreate(
            name="Юрист",
            complexity_level=5,
            domain="legal",
            preferences=ProfilePreferences(response_style="detailed"),
        )
        assert p.domain == "legal"
        assert p.complexity_level == 5

    def test_invalid_complexity_too_high(self):
        with pytest.raises(ValidationError) as exc:
            ProfileCreate(name="Test", complexity_level=6)
        assert "complexity_level" in str(exc.value)

    def test_invalid_complexity_too_low(self):
        with pytest.raises(ValidationError):
            ProfileCreate(name="Test", complexity_level=0)

    def test_invalid_domain(self):
        with pytest.raises(ValidationError) as exc:
            ProfileCreate(name="Test", domain="unknown_domain")
        assert "domain" in str(exc.value)

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            ProfileCreate(name="")

    def test_all_valid_domains(self):
        valid = ["general", "education", "legal", "business", "technical", "medical"]
        for d in valid:
            p = ProfileCreate(name="Test", domain=d)
            assert p.domain == d


class TestProfilePreferences:
    def test_defaults(self):
        p = ProfilePreferences()
        assert p.response_style == "balanced"
        assert p.language == "uk"
        assert p.forbidden_topics == []
        assert 0.0 <= p.temperature <= 1.0

    def test_temperature_bounds(self):
        with pytest.raises(ValidationError):
            ProfilePreferences(temperature=1.5)
        with pytest.raises(ValidationError):
            ProfilePreferences(temperature=-0.1)

    def test_forbidden_topics_list(self):
        p = ProfilePreferences(forbidden_topics=["політика", "реклама"])
        assert len(p.forbidden_topics) == 2
