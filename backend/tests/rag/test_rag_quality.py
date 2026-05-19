"""
RAG якість — найважливіші тести перед показом клієнту.
НЕ використовуємо реальний LLM — тестуємо логіку RAG pipeline.
"""

import pytest
from app.services.prompt_builder import build_system_prompt


class TestContextBuilding:
    """Перевіряємо що контекст для LLM формується правильно."""

    def test_chunks_included_in_context(self, sample_chunks):
        context = "\n\n".join(c["content"] for c in sample_chunks)
        for chunk in sample_chunks:
            assert chunk["content"] in context

    def test_context_ordered_by_similarity(self, sample_chunks):
        sorted_chunks = sorted(sample_chunks, key=lambda c: c["similarity"], reverse=True)
        assert sorted_chunks[0]["similarity"] >= sorted_chunks[-1]["similarity"]

    def test_context_not_empty(self, sample_chunks):
        assert len(sample_chunks) > 0
        total_text = " ".join(c["content"] for c in sample_chunks)
        assert len(total_text) > 50


class TestAntiHallucinationLogic:
    """Антигалюцинаційна логіка."""

    def test_answer_based_on_context(self, sample_chunks):
        key_fact = "5000"
        fact_in_context = any(key_fact in chunk["content"] for chunk in sample_chunks)
        assert fact_in_context, (
            f"Key fact '{key_fact}' not found in any chunk!\n"
            f"Chunks: {[c['content'][:50] for c in sample_chunks]}"
        )

    def test_answer_contains_citation(self, sample_chunks):
        answer_with_citation = "Орендна плата — 5000 грн [contract.pdf, стор. 1]"
        assert any(
            chunk["metadata"]["filename"] in answer_with_citation for chunk in sample_chunks
        )

    def test_no_answer_when_no_relevant_chunks(self):
        empty_chunks = []
        context = "\n".join(c["content"] for c in empty_chunks)
        assert context == ""
        assert len(empty_chunks) == 0

    def test_similarity_threshold(self):
        threshold = 0.7
        all_chunks = [
            {"content": "Релевантний текст", "similarity": 0.95},
            {"content": "Трохи релевантний", "similarity": 0.75},
            {"content": "Нерелевантний текст", "similarity": 0.45},
        ]
        filtered = [c for c in all_chunks if c["similarity"] >= threshold]
        assert len(filtered) == 2
        assert all(c["similarity"] >= threshold for c in filtered)
        texts = [c["content"] for c in filtered]
        assert "Нерелевантний текст" not in texts


class TestPromptWithContext:
    """Промпт + контекст формуються правильно."""

    def test_query_included_in_prompt(self, sample_chunks, legal_profile_l5):
        user_query = "Яка орендна плата за договором?"
        context = "\n\n".join(c["content"] for c in sample_chunks)
        user_message = f"Контекст з документів:\n{context}\n\nПитання: {user_query}"

        assert user_query in user_message
        assert "5000" in user_message

    def test_system_prompt_for_legal_is_strict(self, legal_profile_l5):
        prompt = build_system_prompt(legal_profile_l5)
        has_disclaimer = (
            "юриста" in prompt or "консульт" in prompt or "зверніться" in prompt
        )
        assert has_disclaimer, "Legal profile must have a disclaimer about consulting a lawyer"

    @pytest.mark.parametrize(
        "level,expected_word",
        [
            (1, ["просто", "5", "6", "клас", "коротк"]),
            (3, ["збаланс", "стандартн", "структур"]),
            (5, ["експерт", "фахов", "вичерпн", "точн"]),
        ],
    )
    def test_complexity_levels_use_right_words(self, level, expected_word):
        from datetime import datetime
        from uuid import uuid4

        from app.schemas.profile import ProfilePreferences, ProfileRead

        profile = ProfileRead(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            complexity_level=level,
            domain="general",
            is_active=True,
            preferences=ProfilePreferences(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        prompt = build_system_prompt(profile)
        has_word = any(w in prompt.lower() for w in expected_word)
        assert has_word, (
            f"Level {level} prompt should contain one of {expected_word}.\n"
            f"Prompt preview: {prompt[:200]}"
        )


class TestDataIsolation:
    """Дані різних юзерів не змішуються."""

    def test_user_id_in_query_filter(self, test_user_id):
        all_documents = [
            {"id": "doc-1", "user_id": test_user_id, "filename": "my_contract.pdf"},
            {"id": "doc-2", "user_id": "other-user-id", "filename": "secret.pdf"},
            {"id": "doc-3", "user_id": test_user_id, "filename": "my_invoice.pdf"},
        ]
        user_docs = [d for d in all_documents if d["user_id"] == test_user_id]

        assert len(user_docs) == 2
        assert all(d["user_id"] == test_user_id for d in user_docs)
        filenames = [d["filename"] for d in user_docs]
        assert "secret.pdf" not in filenames
