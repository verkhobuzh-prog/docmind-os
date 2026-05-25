"""Faithfulness scoring tests for RAG answers."""

import pytest

from app.utils.ai_quality import citation_accuracy, faithfulness_score


@pytest.mark.ai_quality
class TestFaithfulnessScoring:
    def test_high_score_when_answer_uses_context(self, sample_chunks):
        context = [chunk["content"] for chunk in sample_chunks]
        answer = (
            "Орендар сплачує орендну плату 5000 грн щомісяця. "
            "Договір укладається терміном на 12 місяців."
        )
        score = faithfulness_score(answer, context)
        assert score >= 0.6

    def test_low_score_when_answer_adds_unsupported_facts(self, sample_chunks):
        context = [chunk["content"] for chunk in sample_chunks]
        answer = (
            "Орендна плата 5000 грн. Додатково орендар отримує безкоштовний "
            "паркінг і щомісячний бонус 10000 грн."
        )
        score = faithfulness_score(answer, context)
        assert score < 0.7

    def test_citation_accuracy_perfect_when_all_citations_valid(self):
        answer = "Платіж 5000 грн [contract.pdf, стор. 1] і пеня 0.1% [contract.pdf, стор. 2]"
        score = citation_accuracy(answer, ["contract.pdf"])
        assert score == 1.0

    def test_citation_accuracy_zero_without_brackets(self):
        answer = "Орендна плата 5000 грн згідно contract.pdf"
        score = citation_accuracy(answer, ["contract.pdf"])
        assert score == 0.0

    def test_faithfulness_alert_threshold(self, sample_chunks):
        context = [chunk["content"] for chunk in sample_chunks]
        weak_answer = "Компанія гарантує безкоштовне страхування та премію 50000 грн."
        assert faithfulness_score(weak_answer, context) < 0.7
