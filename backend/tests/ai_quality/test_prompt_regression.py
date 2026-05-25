"""Prompt regression — stable signatures and required instructions."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.services.prompt_builder import build_system_prompt
from app.utils.ai_quality import prompt_signature


@pytest.mark.ai_quality
class TestPromptRegression:
    def test_default_prompt_signature_stable(self):
        prompt = build_system_prompt(None)
        assert prompt_signature(prompt) == "4889b541e313bc60"

    def test_legal_profile_signature_stable(self, legal_profile_l5):
        prompt = build_system_prompt(legal_profile_l5)
        assert prompt_signature(prompt) == "97410a60f5f83165"

    @pytest.mark.parametrize(
        "domain,required_phrase",
        [
            ("education", "навчальний"),
            ("legal", "юридичний"),
            ("business", "бізнес"),
            ("technical", "технічний"),
            ("medical", "медичний"),
            ("general", "універсальний"),
        ],
    )
    def test_domain_prompts_contain_core_instruction(self, domain, required_phrase):
        from app.schemas.profile import ProfilePreferences, ProfileRead

        profile = ProfileRead(
            id=uuid4(),
            user_id=uuid4(),
            name=f"{domain} profile",
            complexity_level=3,
            domain=domain,
            is_active=True,
            preferences=ProfilePreferences(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        prompt = build_system_prompt(profile).lower()
        assert required_phrase in prompt

    @pytest.mark.parametrize("level", [1, 3, 5])
    def test_complexity_prompt_hashes_are_stable(self, level):
        from app.schemas.profile import ProfilePreferences, ProfileRead

        profile = ProfileRead(
            id=uuid4(),
            user_id=uuid4(),
            name=f"Level {level}",
            complexity_level=level,
            domain="general",
            is_active=True,
            preferences=ProfilePreferences(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        expected = {
            1: "4c1f01ba1ba36536",
            3: "0b347204f97002d7",
            5: "d07cb0475b98d720",
        }
        assert prompt_signature(build_system_prompt(profile)) == expected[level]

    def test_all_profiles_include_anti_hallucination_clause(self, legal_profile_l5):
        prompt = build_system_prompt(legal_profile_l5).lower()
        assert "документ" in prompt
        assert "україн" in prompt
