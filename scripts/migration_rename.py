#!/usr/bin/env python3
"""
migration_rename.py — Скрипт для виправлення конфлікту міграцій.

═══════════════════════════════════════════════════════════════════════
ВЕКТОР АТАКИ: Duplicate migration prefix 003_* / 004_*
═══════════════════════════════════════════════════════════════════════

Проблема:
─────────
  Дублікати числових префіксів → недетермінований порядок на Docker init
  (docker-entrypoint-initdb.d/*.sql алфавітно).

Рішення:
────────
  Детермінований числовий префікс + migration manifest для CI.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

MIGRATIONS_DIR = Path("infra/supabase/migrations")

# (prefix, old_name, new_name) — new_name=None означає "очікується вже так"
MIGRATION_ORDER: list[tuple[str, str | None, str]] = [
    ("001", "001_documents.sql", "001_documents.sql"),
    ("002", "002_document_chunks.sql", "002_document_chunks.sql"),
    ("003", "003_knowledge_graph_metadata.sql", "003_knowledge_graph_metadata.sql"),
    ("003", "003_knowledge_graph.sql", "003_knowledge_graph_metadata.sql"),
    ("004", "003_profiles.sql", "004_profiles.sql"),
    ("004", "004_profiles.sql", "004_profiles.sql"),
    ("005", "004_rls_hardening.sql", "005_rls_hardening.sql"),
    ("006", "005_pilot_invites_and_catalog.sql", "006_pilot_invites_and_catalog.sql"),
    ("007", "006_document_state_machine.sql", "007_document_state_machine.sql"),
]

IGNORED_PATTERNS = {".DS_Store", "__pycache__", ".gitkeep", "MIGRATION_MANIFEST.txt"}


def compute_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


def list_migrations(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(
        p
        for p in directory.iterdir()
        if p.suffix == ".sql" and p.name not in IGNORED_PATTERNS
    )


def check_for_duplicates(migrations: list[Path]) -> list[tuple[str, list[Path]]]:
    prefix_map: dict[str, list[Path]] = {}
    for migration in migrations:
        prefix = migration.name.split("_")[0] if "_" in migration.name else migration.stem
        if prefix.isdigit():
            prefix_map.setdefault(prefix, []).append(migration)
    return [(prefix, files) for prefix, files in prefix_map.items() if len(files) > 1]


def generate_manifest(migrations: list[Path]) -> str:
    lines = [
        "# DocMind OS Migration Manifest",
        f"# Generated: {datetime.now(timezone.utc).isoformat()}",
        "# Format: prefix|filename|sha256_prefix",
        "#",
        "# CI: compare this file against actual migrations directory.",
        "",
    ]
    for migration in migrations:
        prefix = migration.name.split("_")[0] if "_" in migration.name else "000"
        checksum = compute_checksum(migration) if migration.exists() else "missing"
        lines.append(f"{prefix}|{migration.name}|{checksum}")
    return "\n".join(lines) + "\n"


def _planned_renames(migrations_dir: Path) -> list[tuple[Path, Path]]:
    pending: list[tuple[Path, Path]] = []
    for _prefix, old_name, new_name in MIGRATION_ORDER:
        if not old_name or old_name == new_name:
            continue
        old_path = migrations_dir / old_name
        new_path = migrations_dir / new_name
        if old_path.exists() and not new_path.exists():
            pending.append((old_path, new_path))
    pending.sort(key=lambda pair: int(pair[1].name.split("_")[0]), reverse=True)
    return pending


def dry_run_rename(migrations_dir: Path) -> None:
    migrations = list_migrations(migrations_dir)
    duplicates = check_for_duplicates(migrations)

    print(f"\n{'=' * 60}")
    print("Migration Audit Report")
    print(f"{'=' * 60}")
    print(f"Directory : {migrations_dir}")
    print(f"Files     : {len(migrations)}")
    print()

    if not duplicates:
        print("OK  No duplicate prefixes found.")
    else:
        print(f"FAIL  Found {len(duplicates)} duplicate prefix(es):\n")
        for prefix, files in duplicates:
            print(f"  Prefix '{prefix}':")
            for file in files:
                print(f"    - {file.name}")

    print("\nCurrent order:")
    for migration in migrations:
        prefix = migration.name.split("_")[0] if "_" in migration.name else "???"
        marker = "OK" if migration.exists() else "MISSING"
        print(f"  {prefix}  {migration.name}  {marker}")

    print("\nSuggested renames:")
    pending = _planned_renames(migrations_dir)
    if not pending:
        print("  (none needed)")
    else:
        for old_path, new_path in pending:
            print(f"  {old_path.name}  ->  {new_path.name}")

    print()


def perform_rename(migrations_dir: Path, *, backup: bool = True) -> None:
    if not migrations_dir.exists():
        print(f"FAIL  Directory not found: {migrations_dir}")
        sys.exit(1)

    if backup:
        backup_dir = (
            migrations_dir.parent
            / f"migrations_backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        )
        shutil.copytree(migrations_dir, backup_dir, ignore=shutil.ignore_patterns("MIGRATION_MANIFEST.txt"))
        print(f"OK  Backup created: {backup_dir}")

    renamed = 0
    for old_path, new_path in _planned_renames(migrations_dir):
        old_path.rename(new_path)
        print(f"OK  Renamed: {old_path.name} -> {new_path.name}")
        renamed += 1

    print(f"\nOK  {renamed} file(s) renamed.")

    migrations = list_migrations(migrations_dir)
    duplicates = check_for_duplicates(migrations)
    if duplicates:
        print(f"FAIL  Still have duplicates after rename: {duplicates}")
        sys.exit(1)
    print("OK  No duplicate prefixes after rename.")

    manifest_path = migrations_dir / "MIGRATION_MANIFEST.txt"
    manifest_path.write_text(generate_manifest(migrations), encoding="utf-8")
    print(f"OK  Manifest written: {manifest_path}")


def ci_check(migrations_dir: Path) -> None:
    migrations = list_migrations(migrations_dir)
    duplicates = check_for_duplicates(migrations)
    errors: list[str] = []

    if duplicates:
        for prefix, files in duplicates:
            errors.append(
                f"Duplicate migration prefix '{prefix}': "
                + ", ".join(file.name for file in files)
            )

    sorted_names = sorted(m.name for m in migrations)
    actual_names = [m.name for m in migrations]
    if actual_names != sorted_names:
        errors.append(
            "Migration files are not in alphabetical order. "
            f"Expected: {sorted_names}, got: {actual_names}"
        )

    manifest_path = migrations_dir / "MIGRATION_MANIFEST.txt"
    if manifest_path.exists():
        expected = generate_manifest(migrations)
        actual = manifest_path.read_text(encoding="utf-8")
        expected_lines = [line for line in expected.splitlines() if line and not line.startswith("#")]
        actual_lines = [line for line in actual.splitlines() if line and not line.startswith("#")]
        if expected_lines != actual_lines:
            errors.append("MIGRATION_MANIFEST.txt is out of date. Run: python scripts/migration_rename.py rename")

    if errors:
        print("FAIL  Migration CI checks FAILED:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    print(f"OK  Migration CI checks passed ({len(migrations)} files, no duplicates).")


def main() -> None:
    parser = argparse.ArgumentParser(description="DocMind OS migration management tool")
    parser.add_argument(
        "command",
        choices=["check", "rename", "ci"],
        help="check: audit; rename: apply renames; ci: CI validation",
    )
    parser.add_argument(
        "--dir",
        default="infra/supabase/migrations",
        help="Path to migrations directory",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt for rename",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not create backup before rename",
    )
    args = parser.parse_args()
    migrations_dir = Path(args.dir)

    if args.command == "check":
        dry_run_rename(migrations_dir)
    elif args.command == "rename":
        if not args.yes:
            print("WARNING  This will RENAME migration files. Ensure git is clean first.")
            confirm = input("Type 'yes' to proceed: ")
            if confirm.strip().lower() != "yes":
                print("Aborted.")
                return
        perform_rename(migrations_dir, backup=not args.no_backup)
    elif args.command == "ci":
        ci_check(migrations_dir)


if __name__ == "__main__":
    main()
