"""Run database migrations using Alembic.

Wrapper script that ensures the database is up-to-date before
starting the application.

Usage:
    python scripts/migrate.py              # upgrade to latest
    python scripts/migrate.py --revision abc123  # upgrade to specific revision
    python scripts/migrate.py --downgrade -1     # downgrade one step
"""

import argparse
import subprocess
import sys


def run_migration(revision: str = "head", downgrade: bool = False) -> int:
    """Execute alembic upgrade or downgrade.

    Args:
        revision: Target revision (default: "head" for latest).
        downgrade: If True, run downgrade instead of upgrade.

    Returns:
        Exit code from the alembic command.
    """
    command = "downgrade" if downgrade else "upgrade"
    cmd = ["alembic", command, revision]

    print(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"Migration {command} to {revision} completed successfully.")
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"Migration failed with exit code {e.returncode}", file=sys.stderr)
        return e.returncode
    except FileNotFoundError:
        print(
            "Error: alembic not found. Install it with: pip install alembic",
            file=sys.stderr,
        )
        return 1


def main():
    parser = argparse.ArgumentParser(description="Run Kairos Trading database migrations")
    parser.add_argument(
        "--revision",
        default="head",
        help="Target revision (default: head)",
    )
    parser.add_argument(
        "--downgrade",
        action="store_true",
        help="Downgrade instead of upgrade",
    )
    args = parser.parse_args()

    sys.exit(run_migration(revision=args.revision, downgrade=args.downgrade))


if __name__ == "__main__":
    main()
