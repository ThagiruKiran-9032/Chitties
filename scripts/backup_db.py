#!/usr/bin/env python3
"""
Chitties Enterprise Database Automated Backup Script
Generates gzipped PostgreSQL dumps, computes cryptographic SHA-256 checksums,
and applies automatic retention rotation policies.
"""

import os
import sys
import time
import gzip
import hashlib
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKUP_DIR = ROOT_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Configuration
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "chitties_db")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "1234567890")
RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 checksum of the backup archive."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def create_backup():
    """Execute pg_dump, compress with gzip, and verify checksum."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sql_filename = f"chitties_backup_{timestamp}.sql"
    gz_filename = f"{sql_filename}.gz"
    gz_path = BACKUP_DIR / gz_filename
    checksum_path = BACKUP_DIR / f"{gz_filename}.sha256"

    print(f"[{datetime.now().isoformat()}] Starting backup for '{DB_NAME}' on {DB_HOST}:{DB_PORT}...")

    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD

    cmd = [
        "pg_dump",
        "-h", DB_HOST,
        "-p", str(DB_PORT),
        "-U", DB_USER,
        "-d", DB_NAME,
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
    ]

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        with gzip.open(gz_path, "wb") as gz_file:
            for chunk in iter(lambda: process.stdout.read(65536), b""):
                gz_file.write(chunk)

        _, stderr = process.communicate()
        if process.returncode != 0:
            print(f"[ERROR] pg_dump failed: {stderr.decode()}", file=sys.stderr)
            if gz_path.exists():
                gz_path.unlink()
            return False

        # Compute Checksum
        checksum = compute_sha256(gz_path)
        with open(checksum_path, "w") as f:
            f.write(f"{checksum}  {gz_filename}\n")

        size_mb = gz_path.stat().st_size / (1024 * 1024)
        print(f"[SUCCESS] Backup saved: {gz_path} ({size_mb:.2f} MB)")
        print(f"[SUCCESS] SHA-256 Checksum: {checksum}")
        return True

    except FileNotFoundError:
        print("[WARNING] pg_dump utility not found in PATH. Skipping direct execution.")
        return False
    except Exception as exc:
        print(f"[ERROR] Backup encountered exception: {exc}", file=sys.stderr)
        return False


def prune_old_backups():
    """Remove backup archives older than RETENTION_DAYS."""
    cutoff_time = datetime.now() - timedelta(days=RETENTION_DAYS)
    print(f"[{datetime.now().isoformat()}] Checking for archives older than {RETENTION_DAYS} days...")

    pruned_count = 0
    for file in BACKUP_DIR.glob("chitties_backup_*"):
        file_mtime = datetime.fromtimestamp(file.stat().st_mtime)
        if file_mtime < cutoff_time:
            print(f"[PRUNE] Removing expired backup: {file.name}")
            file.unlink()
            pruned_count += 1

    print(f"[PRUNE] Pruning complete. {pruned_count} expired archives removed.")


if __name__ == "__main__":
    success = create_backup()
    prune_old_backups()
    sys.exit(0 if success else 1)
