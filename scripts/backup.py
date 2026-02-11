"""Database backup script using pg_dump.

Creates timestamped PostgreSQL backups and manages retention.

Usage:
    python scripts/backup.py                         # backup with defaults
    python scripts/backup.py --output /backups       # custom output dir
    python scripts/backup.py --keep 7                # keep last 7 backups
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


# Default configuration
DEFAULT_OUTPUT_DIR = "./backups"
DEFAULT_KEEP = 30  # Keep last 30 backups
DEFAULT_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://kairos:kairos@localhost:5432/kairos",
)


def parse_db_url(url: str) -> dict[str, str]:
    """Parse a PostgreSQL connection URL into components.

    Args:
        url: PostgreSQL URL (postgresql://user:pass@host:port/dbname)

    Returns:
        Dict with keys: user, password, host, port, dbname.
    """
    # Remove scheme
    rest = url.replace("postgresql://", "").replace("postgres://", "")

    # Split user:pass@host:port/dbname
    user_pass, host_db = rest.split("@", 1)
    user, password = user_pass.split(":", 1) if ":" in user_pass else (user_pass, "")
    host_port, dbname = host_db.split("/", 1)
    host, port = host_port.split(":", 1) if ":" in host_port else (host_port, "5432")

    return {
        "user": user,
        "password": password,
        "host": host,
        "port": port,
        "dbname": dbname,
    }


def create_backup(db_url: str, output_dir: str) -> str | None:
    """Run pg_dump and save to a timestamped file.

    Args:
        db_url: PostgreSQL connection URL.
        output_dir: Directory to save the backup file.

    Returns:
        Path to the backup file, or None on failure.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    db = parse_db_url(db_url)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"kairos_{db['dbname']}_{timestamp}.sql.gz"
    filepath = output_path / filename

    env = os.environ.copy()
    env["PGPASSWORD"] = db["password"]

    cmd = [
        "pg_dump",
        "-h", db["host"],
        "-p", db["port"],
        "-U", db["user"],
        "-d", db["dbname"],
        "--format=custom",
        f"--file={filepath}",
    ]

    print(f"Backing up {db['dbname']} to {filepath}...")

    try:
        subprocess.run(cmd, env=env, check=True, capture_output=True)
        size_mb = filepath.stat().st_size / (1024 * 1024)
        print(f"Backup created: {filepath} ({size_mb:.2f} MB)")
        return str(filepath)
    except subprocess.CalledProcessError as e:
        print(f"Backup failed: {e.stderr.decode()}", file=sys.stderr)
        return None
    except FileNotFoundError:
        print(
            "Error: pg_dump not found. Install PostgreSQL client tools.",
            file=sys.stderr,
        )
        return None


def cleanup_old_backups(output_dir: str, keep: int) -> int:
    """Remove old backups, keeping only the most recent *keep* files.

    Args:
        output_dir: Directory containing backup files.
        keep: Number of recent backups to keep.

    Returns:
        Number of files removed.
    """
    output_path = Path(output_dir)
    backups = sorted(
        output_path.glob("kairos_*.sql*"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    to_remove = backups[keep:]
    for f in to_remove:
        f.unlink()
        print(f"  Removed old backup: {f.name}")

    return len(to_remove)


def main():
    parser = argparse.ArgumentParser(description="Backup Kairos Trading database")
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=DEFAULT_KEEP,
        help=f"Number of backups to retain (default: {DEFAULT_KEEP})",
    )
    parser.add_argument(
        "--db-url",
        default=DEFAULT_DB_URL,
        help="PostgreSQL connection URL (default: from DATABASE_URL env)",
    )
    args = parser.parse_args()

    backup_path = create_backup(args.db_url, args.output)
    if backup_path is None:
        sys.exit(1)

    removed = cleanup_old_backups(args.output, args.keep)
    if removed > 0:
        print(f"Cleaned up {removed} old backup(s).")

    print("Backup complete.")


if __name__ == "__main__":
    main()
