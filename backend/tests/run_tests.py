"""
DocMind OS — Test Runner (7 blocks)
Запуск: cd backend && python -m tests.run_tests
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent

BLOCKS: list[tuple[str, str, str]] = [
    ("Smoke", "SMOKE — Базова перевірка", "tests/smoke/"),
    ("Unit", "UNIT — Prompt Builder + Schemas", "tests/unit/"),
    ("RAG", "RAG — Якість відповідей", "tests/rag/"),
    ("Integration", "INTEGRATION — Pipeline (queue, ingest, lifecycle)", "tests/integration/"),
    ("AI Quality", "AI QUALITY — Hallucination, faithfulness, prompts", "tests/ai_quality/"),
    ("Cost", "COST — Token pricing & quota tracking", "tests/cost/"),
    ("API", "API — HTTP endpoints (auth, docs, chat)", "tests/test_auth.py tests/test_chat.py tests/test_documents.py tests/test_health.py"),
]


def run(label: str, path: str, extra_args: list[str] | None = None) -> bool:
    """Запускає pytest для конкретного набору тестів."""
    print(f"\n{'=' * 55}")
    print(f"  {label}")
    print(f"{'=' * 55}")

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        *path.split(),
        "-v",
        "--tb=short",
        "--no-header",
        *(extra_args or []),
    ]
    result = subprocess.run(cmd, cwd=BACKEND_ROOT)
    return result.returncode == 0


def main() -> None:
    start = datetime.now()
    print("\nDocMind OS — Запуск тестів (7 блоків)")
    print(f"   {start.strftime('%d.%m.%Y %H:%M')}\n")

    results = {name: run(label, path) for name, label, path in BLOCKS}

    duration = (datetime.now() - start).total_seconds()

    print(f"\n{'=' * 55}")
    print(f"  ПІДСУМОК  ({duration:.1f}s)")
    print(f"{'=' * 55}")

    all_passed = True
    for name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        icon = "OK" if passed else "FAIL"
        print(f"  [{icon}] {status}  {name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("  Всі 7 блоків пройшли — система готова до демо клієнту!")
    else:
        print("  Є проблеми — виправ перед показом клієнту.")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
