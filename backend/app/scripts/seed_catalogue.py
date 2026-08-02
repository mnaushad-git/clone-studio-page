"""Load the canonical catalogue JSON files into PostgreSQL.

Usage (from the backend/ virtualenv, migrations already applied):
    python -m app.scripts.seed_catalogue --dry-run
    python -m app.scripts.seed_catalogue --apply
"""

from __future__ import annotations

import argparse
import sys

from app.core.database import session_scope
from app.services.catalogue.seed_service import CatalogueSeedService, SeedResult


def _print_summary(result: SeedResult) -> None:
    print(f"Catalogue seed: {result.status}")
    print(f"  started_at:   {result.started_at.isoformat()}")
    print(f"  completed_at: {result.completed_at.isoformat()}")
    print(
        f"  created={result.created_count} updated={result.updated_count} "
        f"skipped={result.skipped_count} failed={result.failed_count}"
    )
    if result.counts_by_entity:
        print("  by entity:")
        for entity, counts in sorted(result.counts_by_entity.items()):
            print(
                f"    {entity}: created={counts['created']} updated={counts['updated']} "
                f"skipped={counts['skipped']}"
            )
    if result.error_summary:
        print(f"  error: {result.error_summary}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--dry-run", action="store_true", help="Validate and compute changes without writing."
    )
    mode.add_argument("--apply", action="store_true", help="Write the changes to the database.")
    args = parser.parse_args(argv)

    with session_scope() as session:
        service = CatalogueSeedService(session)
        result = service.run(dry_run=args.dry_run)
        # Always commit: this persists the catalogue_seed_runs audit row in every case,
        # and the actual catalogue writes too when status is SUCCESS (the seed service's
        # internal savepoint already rolled those back for DRY_RUN/FAILED outcomes).
        session.commit()

    _print_summary(result)
    return 0 if result.status in ("SUCCESS", "DRY_RUN") else 1


if __name__ == "__main__":
    sys.exit(main())
