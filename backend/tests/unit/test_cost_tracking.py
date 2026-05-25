"""
Cost Tracking — токени і бюджет під контролем.
gpt-4o-mini: $0.15/1M input, $0.60/1M output
text-embedding-3-small: $0.02/1M tokens
"""

import pytest


class TestTokenEstimation:
    def test_tiktoken_counts_tokens(self):
        try:
            import tiktoken

            enc = tiktoken.get_encoding("cl100k_base")
            text = "Договір оренди приміщення від 1 лютого 2024 року."
            n = len(enc.encode(text))
            assert 5 <= n <= 40, f"Несподівана кількість токенів: {n}"
        except ImportError:
            pytest.skip("tiktoken не встановлений")

    def test_context_fits_model_limit(self):
        try:
            import tiktoken

            enc = tiktoken.get_encoding("cl100k_base")
            MAX = 128_000 - 2_000  # gpt-4o-mini ліміт мінус відповідь
            context = "Текст документа. " * 500  # ~8500 слів
            n = len(enc.encode(context))
            assert n < MAX, f"Context {n} токенів перевищує ліміт {MAX}"
        except ImportError:
            pytest.skip("tiktoken не встановлений")


class TestCostBudget:
    INPUT_COST = 0.15  # $ per 1M tokens (gpt-4o-mini)
    OUTPUT_COST = 0.60
    EMBED_COST = 0.02  # $ per 1M tokens (text-embedding-3-small)

    def _chat_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (
            input_tokens / 1_000_000 * self.INPUT_COST
            + output_tokens / 1_000_000 * self.OUTPUT_COST
        )

    def test_single_request_under_1_cent(self):
        """Один chat запит < $0.001"""
        cost = self._chat_cost(2_000, 500)
        assert cost < 0.001, f"Один запит ${cost:.6f} — занадто дорого"

    def test_1000_requests_under_1_dollar(self):
        """1000 запитів/місяць < $1.00"""
        monthly = self._chat_cost(2_000, 500) * 1_000
        assert monthly < 1.0, f"1k запитів/міс = ${monthly:.4f}"

    def test_single_document_embedding_cheap(self):
        """Індексація 1 документа < $0.001"""
        tokens = 6_500  # ~5000 слів PDF
        cost = tokens / 1_000_000 * self.EMBED_COST
        assert cost < 0.001, f"Embed документа ${cost:.6f}"

    def test_categorization_per_doc_cheap(self):
        """Авто-категоризація через gpt-4o-mini < $0.0005 за документ"""
        # 600 input + 120 output токенів
        cost = self._chat_cost(600, 120)
        assert cost < 0.0005, f"Категоризація ${cost:.6f}"

    def test_100_docs_embedding_under_10_cents(self):
        """100 документів для пілоту < $0.10 на індексацію"""
        cost_per_doc = 6_500 / 1_000_000 * self.EMBED_COST
        total = cost_per_doc * 100
        assert total < 0.10, f"100 docs embed = ${total:.4f}"

    def test_monthly_pilot_budget(self):
        """
        Повний місяць пілоту (100 docs + 500 запитів + категоризація):
        має вкладатись у $1.
        """
        embed_100_docs = (6_500 / 1_000_000 * self.EMBED_COST) * 100
        chat_500_req = self._chat_cost(2_000, 500) * 500
        categorize_100 = self._chat_cost(600, 120) * 100
        total = embed_100_docs + chat_500_req + categorize_100
        assert total < 1.0, (
            f"Пілот (100 docs + 500 чатів + категоризація) = ${total:.4f}\n"
            f"  Embed:    ${embed_100_docs:.4f}\n"
            f"  Chat:     ${chat_500_req:.4f}\n"
            f"  Categorize: ${categorize_100:.4f}"
        )
