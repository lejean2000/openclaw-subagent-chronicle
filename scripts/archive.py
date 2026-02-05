#!/usr/bin/env python3
"""
Subagent Chronicle - Entry Archiver v1.0.0

Archives existing diary entries before regeneration.
Prevents contamination of new entries by old versions.
"""

import argparse
import os
import shutil
from datetime import datetime
from pathlib import Path

# Configuration
DEFAULT_DIARY_PATH = "memory/diary/"
ARCHIVE_SUBDIR = "archive"


def get_workspace_root():
    """Find the workspace root (where memory/ lives)"""
    env_workspace = os.getenv("OPENCLAW_WORKSPACE") or os.getenv("AGENT_WORKSPACE")
    if env_workspace:
        env_path = Path(env_workspace)
        if (env_path / "memory").exists():
            return env_path
    
    candidates = [
        Path.cwd(),
        Path.home() / ".openclaw" / "workspace",
        Path.home() / "clawd",
    ]
    for path in candidates:
        if (path / "memory").exists():
            return path
    return Path.cwd()


def archive_entry(date_str, diary_path=None):
    """
    Archive an existing diary entry before regeneration.
    Returns True if an entry was archived, False if no entry existed.
    """
    workspace = get_workspace_root()
    diary_dir = workspace / (diary_path or DEFAULT_DIARY_PATH)
    
    entry_file = diary_dir / f"{date_str}.md"
    
    if not entry_file.exists():
        return False, f"No existing entry for {date_str}"
    
    # Create archive directory
    archive_dir = diary_dir / ARCHIVE_SUBDIR
    archive_dir.mkdir(exist_ok=True)
    
    # Generate archive filename with timestamp
    timestamp = datetime.now().strftime("%H%M%S")
    archive_name = f"{date_str}-{timestamp}.md"
    archive_path = archive_dir / archive_name
    
    # Move the existing entry to archive
    shutil.move(str(entry_file), str(archive_path))
    
    return True, f"Archived {entry_file.name} → {archive_path}"


def main():
    parser = argparse.ArgumentParser(
        description="Archive existing diary entry before regeneration"
    )
    parser.add_argument("--today", action="store_true", help="Archive today's entry")
    parser.add_argument("--yesterday", action="store_true", help="Archive yesterday's entry")
    parser.add_argument("--date", help="Archive specific date (YYYY-MM-DD)")
    parser.add_argument(
        "--diary-path",
        default=DEFAULT_DIARY_PATH,
        help=f"Path to diary directory (default: {DEFAULT_DIARY_PATH})"
    )
    
    args = parser.parse_args()
    
    # Determine date
    if args.today:
        date_str = datetime.now().strftime("%Y-%m-%d")
    elif args.yesterday:
        date_str = (datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    elif args.date:
        date_str = args.date
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    archived, message = archive_entry(date_str, args.diary_path)
    print(message)
    
    # Return exit code 0 whether archived or not (non-existence is not an error)
    return 0


if __name__ == "__main__":
    exit(main())
