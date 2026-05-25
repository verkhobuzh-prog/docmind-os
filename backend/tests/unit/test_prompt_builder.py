"""
Unit тести для build_system_prompt.
Перевіряємо що промпт правильно адаптується під профіль.
"""

import pytest
from app.services.prompt_builder import build_system_prompt


class TestNoProfile:
    """Поведінка без профілю — базовий промпт."""

    def test_returns_string(self):
        prompt = build_system_prompt(None)
        assert isinstance(prompt, str)
        assert len(prompt) > 50

    def test_mentions_dochub(self):
        prompt = build_system_prompt(None)
        assert "Doc-Hub" in prompt

    def test_instructs_to_cite_sources(self):
        """Без профілю теж має вказувати посилатись на документи."""
        prompt = build_system_prompt(None)
        assert any(word in prompt.lower() for word in ["документ", "джерел", "source"])


class TestEducationProfiles:
    """Профілі для освіти — ключовий сегмент."""

    def test_level1_uses_simple_language(self, education_profile_l1):
        prompt = build_system_prompt(education_profile_l1)
        assert any(word in prompt for word in ["5", "6", "клас", "просто", "коротк"])

    def test_level5_uses_expert_language(self, education_profile_l5):
        prompt = build_system_prompt(education_profile_l5)
        assert any(word in prompt for word in ["експерт", "фахов", "термінолог", "вичерпн"])

    def test_levels_are_different(self, education_profile_l1, education_profile_l5):
        prompt_l1 = build_system_prompt(education_profile_l1)
        prompt_l5 = build_system_prompt(education_profile_l5)
        assert prompt_l1 != prompt_l5

    def test_education_domain_instruction(self, education_profile_l1):
        prompt = build_system_prompt(education_profile_l1)
        assert any(
            word in prompt.lower()
            for word in ["навчальн", "пояснюй", "приклад", "покроково"]
        )

    def test_profile_name_in_prompt(self, education_profile_l1):
        prompt = build_system_prompt(education_profile_l1)
        assert education_profile_l1.name in prompt


class TestLegalProfile:
    """Юридичний профіль — критичний для першого клієнта."""

    def test_legal_domain_instruction(self, legal_profile_l5):
        prompt = build_system_prompt(legal_profile_l5)
        assert any(
            word in prompt.lower()
            for word in ["юридичн", "зобов'язан", "ризик", "юрист", "аналітик"]
        )

    def test_legal_has_disclaimer(self, legal_profile_l5):
        prompt = build_system_prompt(legal_profile_l5)
        assert any(word in prompt for word in ["юриста", "зверніться", "консульт"])

    def test_legal_level5_is_expert(self, legal_profile_l5):
        prompt = build_system_prompt(legal_profile_l5)
        assert any(word in prompt for word in ["точн", "фахов", "термінолог", "експерт"])


class TestBusinessProfile:
    """Бізнес профіль."""

    def test_business_domain_instruction(self, business_profile_l3):
        prompt = build_system_prompt(business_profile_l3)
        assert any(
            word in prompt.lower()
            for word in ["бізнес", "практичн", "аналітик", "висновк", "цифр"]
        )

    def test_balanced_style(self, business_profile_l3):
        prompt = build_system_prompt(business_profile_l3)
        assert any(word in prompt.lower() for word in ["збаланс", "достатн"])


class TestResponseStyles:
    """Стилі відповідей."""

    def test_concise_style(self, education_profile_l1):
        prompt = build_system_prompt(education_profile_l1)
        assert any(word in prompt.lower() for word in ["стисло", "коротко", "3", "5", "речень"])

    def test_forbidden_topics(self):
        from datetime import datetime
        from uuid import uuid4

        from app.schemas.profile import ProfilePreferences, ProfileRead

        profile = ProfileRead(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            complexity_level=3,
            domain="general",
            is_active=True,
            preferences=ProfilePreferences(forbidden_topics=["політика", "релігія"]),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        prompt = build_system_prompt(profile)
        assert "політика" in prompt
        assert "релігія" in prompt


class TestAntiHallucination:
    """Промпт має захищати від галюцинацій."""

    def test_prompt_instructs_to_use_documents_only(self, legal_profile_l5):
        prompt = build_system_prompt(legal_profile_l5).lower()
        assert any(
            phrase in prompt
            for phrase in [
                "лише на надані документи",
                "тільки на документи",
                "посилайся лише",
                "only from documents",
            ]
        ), f"Anti-hallucination instruction missing in prompt:\n{prompt[:300]}"

    def test_prompt_instructs_to_admit_missing_info(self, legal_profile_l5):
        prompt = build_system_prompt(legal_profile_l5).lower()
        assert any(
            phrase in prompt
            for phrase in [
                "відсутня в наданих документах",
                "не знайдено в документах",
                "not found in documents",
                "інформація відсутня",
            ]
        ), f"Missing-info instruction missing in prompt:\n{prompt[:300]}"

    @pytest.mark.parametrize(
        "domain",
        ["education", "legal", "business", "technical", "medical", "general"],
    )
    def test_all_domains_have_anti_hallucination(self, domain):
        from datetime import datetime
        from uuid import uuid4

        from app.schemas.profile import ProfilePreferences, ProfileRead

        profile = ProfileRead(
            id=uuid4(),
            user_id=uuid4(),
            name=f"Test {domain}",
            complexity_level=3,
            domain=domain,
            is_active=True,
            preferences=ProfilePreferences(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        prompt = build_system_prompt(profile).lower()
        has_protection = any(
            phrase in prompt
            for phrase in [
                "лише на надані документи",
                "тільки на документи",
                "посилайся лише",
                "відсутня в наданих документах",
            ]
        )
        assert has_protection, (
            f"Domain '{domain}' lacks anti-hallucination protection!\n"
            f"Prompt preview:\n{prompt[:200]}"
        )
