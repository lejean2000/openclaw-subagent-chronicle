#!/usr/bin/env python3
"""
Subagent Chronicle - Entry Saver v1.0.0

Saves a diary entry to file and extracts persistent data (quotes, curiosities, etc.)
Reads entry from stdin or --file argument.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Configuration
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_FILE = SKILL_DIR / "config.json"
DEFAULT_DIARY_PATH = "memory/diary/"


def load_config():
    """Load configuration from config.json"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {
        "diary_path": DEFAULT_DIARY_PATH,
        "privacy_level": "private",
        "memory_integration": {
            "enabled": True,
            "append_to_daily": True,
            "format": "summary"
        }
    }


def get_workspace_root():
    """Find the workspace root (where memory/ lives)"""
    env_workspace = os.getenv("OPENCLAW_WORKSPACE") or os.getenv("AGENT_WORKSPACE")
    if env_workspace:
        env_path = Path(env_workspace)
        if (env_path / "memory").exists():
            return env_path
    
    candidates = [
        Path.cwd(),
        Path.home() / "clawd",
        Path.home() / ".openclaw" / "workspace",
    ]
    for path in candidates:
        if (path / "memory").exists():
            return path
    return Path.cwd()


def get_diary_path(config, workspace):
    """Get full path to diary directory"""
    diary_path = workspace / config.get("diary_path", DEFAULT_DIARY_PATH)
    diary_path.mkdir(parents=True, exist_ok=True)
    return diary_path


def extract_summary(entry_content):
    """Extract summary section from diary entry"""
    summary_match = re.search(r'## Summary\n(.+?)(?=\n##|\Z)', entry_content, re.DOTALL)
    if summary_match:
        return summary_match.group(1).strip()
    
    # Fallback: first paragraph after title
    lines = entry_content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('# ') and i + 1 < len(lines):
            for j in range(i + 1, min(i + 5, len(lines))):
                if lines[j].strip() and not lines[j].startswith('#'):
                    return lines[j].strip()
    
    return "Diary entry generated."


def extract_title(entry_content):
    """Extract title from diary entry"""
    title_match = re.search(r'^# \d{4}-\d{2}-\d{2} — (.+)$', entry_content, re.MULTILINE)
    if title_match:
        return title_match.group(1).strip()
    return None


def save_entry(entry_content, date_str, diary_path):
    """Save diary entry to file"""
    output_file = diary_dir / f"{date_str}.md"
    
    with open(output_file, 'w') as f:
        f.write(entry_content)
    
    return output_file


def update_persistent_files(entry_content, date_str, diary_dir):
    """Extract and append quotes, curiosities, decisions to persistent files"""
    diary_dir.mkdir(parents=True, exist_ok=True)
    updates = []
    
    # Extract Quote of the Day
    quote_match = re.search(r'## Quote of the Day 💬\n(.+?)(?=\n##|\Z)', entry_content, re.DOTALL)
    if quote_match:
        quote_content = quote_match.group(1).strip()
        if quote_content and len(quote_content) > 10:
            quotes_file = diary_dir / "quotes.md"
            if not quotes_file.exists():
                quotes_file.write_text("# Quote Hall of Fame 💬\n\nMemorable quotes from my human.\n\n---\n\n")
            
            with open(quotes_file, 'a') as f:
                f.write(f"\n### {date_str}\n{quote_content}\n")
            updates.append(f"Quote → {quotes_file.name}")
    
    # Extract Curiosities
    curiosity_match = re.search(r'## Things I\'m Curious About 🔮\n(.+?)(?=\n##|\Z)', entry_content, re.DOTALL)
    if curiosity_match:
        curiosity_content = curiosity_match.group(1).strip()
        if curiosity_content and len(curiosity_content) > 10:
            curiosity_file = diary_dir / "curiosity.md"
            if not curiosity_file.exists():
                curiosity_file.write_text("# Curiosity Backlog 🔮\n\nThings I want to explore.\n\n---\n\n## Active\n\n")
            
            with open(curiosity_file, 'a') as f:
                f.write(f"\n### {date_str}\n{curiosity_content}\n")
            updates.append(f"Curiosity → {curiosity_file.name}")
    
    # Extract Decisions
    decisions_match = re.search(r'## Key Decisions Made 🏛️\n(.+?)(?=\n##|\Z)', entry_content, re.DOTALL)
    if decisions_match:
        decisions_content = decisions_match.group(1).strip()
        if decisions_content and len(decisions_content) > 10:
            decisions_file = diary_dir / "decisions.md"
            if not decisions_file.exists():
                decisions_file.write_text("# Decision Archaeology 🏛️\n\nJudgment calls worth remembering.\n\n---\n\n")
            
            with open(decisions_file, 'a') as f:
                f.write(f"\n### {date_str}\n{decisions_content}\n")
            updates.append(f"Decision → {decisions_file.name}")
    
    # Extract Relationship Notes
    relationship_match = re.search(r'## Relationship Notes 🤝\n(.+?)(?=\n##|\Z)', entry_content, re.DOTALL)
    if relationship_match:
        relationship_content = relationship_match.group(1).strip()
        if relationship_content and len(relationship_content) > 10:
            relationship_file = diary_dir / "relationship.md"
            if not relationship_file.exists():
                relationship_file.write_text("# Relationship Evolution 🤝\n\nHow my dynamic with my human evolves.\n\n---\n\n")
            
            with open(relationship_file, 'a') as f:
                f.write(f"\n### {date_str}\n{relationship_content}\n")
            updates.append(f"Relationship → {relationship_file.name}")
    
    return updates


def append_to_daily_memory(entry_content, date_str, config, workspace):
    """Append diary summary to main daily memory file"""
    memory_integration = config.get("memory_integration", {})
    
    if not memory_integration.get("enabled", False):
        return False
    
    if not memory_integration.get("append_to_daily", False):
        return False
    
    memory_dir = workspace / "memory"
    daily_memory_file = memory_dir / f"{date_str}.md"
    
    format_type = memory_integration.get("format", "summary")
    diary_path = config.get("diary_path", DEFAULT_DIARY_PATH)
    
    # Build content to append
    if format_type == "link":
        content = f"\n\n## 📜 Daily Chronicle\n[View diary entry]({diary_path}{date_str}.md)\n"
    elif format_type == "full":
        content = f"\n\n## 📜 Daily Chronicle\n{entry_content}\n"
    else:  # summary
        summary = extract_summary(entry_content)
        title = extract_title(entry_content)
        title_line = f"**{title}**\n\n" if title else ""
        content = f"\n\n## 📜 Daily Chronicle\n{title_line}{summary}\n"
    
    # Create memory dir if needed
    memory_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if section already exists
    if daily_memory_file.exists():
        existing_content = daily_memory_file.read_text()
        if "## 📜 Daily Chronicle" in existing_content:
            return False  # Already exists
        # Append to existing file
        with open(daily_memory_file, 'a') as f:
            f.write(content)
    else:
        # Create new file with header
        header = f"# {date_str}\n\n*Daily memory log*\n"
        with open(daily_memory_file, 'w') as f:
            f.write(header + content)
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Save a diary entry")
    parser.add_argument("--today", action="store_true", help="Use today's date")
    parser.add_argument("--yesterday", action="store_true", help="Use yesterday's date")
    parser.add_argument("--date", help="Date for entry (YYYY-MM-DD)")
    parser.add_argument("--file", "-f", help="Read entry from file (default: stdin)")
    parser.add_argument("--no-persistent", action="store_true", help="Skip updating persistent files")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    
    args = parser.parse_args()
    
    # Read entry content
    if args.file:
        with open(args.file) as f:
            entry_content = f.read()
    else:
        entry_content = sys.stdin.read()
    
    if not entry_content.strip():
        print("Error: No entry content provided", file=sys.stderr)
        sys.exit(1)
    
    # Determine date
    if args.today:
        date_str = datetime.now().strftime("%Y-%m-%d")
    elif args.yesterday:
        date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    elif args.date:
        date_str = args.date
    else:
        # Try to extract from entry title
        title_match = re.search(r'^# (\d{4}-\d{2}-\d{2})', entry_content, re.MULTILINE)
        if title_match:
            date_str = title_match.group(1)
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")
    
    config = load_config()
    workspace = get_workspace_root()
    diary_dir = get_diary_path(config, workspace)
    
    if args.dry_run:
        print(f"DRY RUN: Would save entry for {date_str}")
        print(f"  Destination: {diary_dir / f'{date_str}.md'}")
        print(f"  Word count: {len(entry_content.split())}")
        if not args.no_persistent:
            updates = update_persistent_files(entry_content, date_str, diary_dir)
            print(f"  Would update: {', '.join(updates) if updates else 'nothing'}")
        sys.exit(0)
    
    # Save entry
    output_file = diary_dir / f"{date_str}.md"
    with open(output_file, 'w') as f:
        f.write(entry_content)
    
    print(f"✓ Saved diary entry to {output_file}")
    
    # Update persistent files
    if not args.no_persistent:
        updates = update_persistent_files(entry_content, date_str, diary_dir)
        if updates:
            for update in updates:
                print(f"  ✓ Updated {update}")
    
    # Append to daily memory
    if append_to_daily_memory(entry_content, date_str, config, workspace):
        print(f"  ✓ Added chronicle to memory/{date_str}.md")
    
    # Show word count
    word_count = len(entry_content.split())
    print(f"\n  Word count: {word_count} words")


if __name__ == "__main__":
    main()
