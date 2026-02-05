#!/usr/bin/env python3
"""
Subagent Chronicle - Context Collector v1.0.0

Collects session logs and persistent files for diary generation.
Outputs formatted context to stdout for consumption by the main agent.
"""

import argparse
import json
import os
from datetime import datetime, timedelta
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
        "template": "daily"
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
    return workspace / config.get("diary_path", DEFAULT_DIARY_PATH)


def load_session_log(date_str, workspace, max_chars=15000):
    """Load session log for a specific date"""
    memory_dir = workspace / "memory"
    session_file = memory_dir / f"{date_str}.md"
    
    if session_file.exists():
        with open(session_file) as f:
            content = f.read()
            if len(content) > max_chars:
                content = content[:max_chars] + "\n\n[... truncated for context ...]"
            return content
    return None


def load_recent_sessions(workspace, days=3, max_per_session=5000):
    """Load recent session logs for context"""
    memory_dir = workspace / "memory"
    sessions = []
    
    for i in range(days):
        date = datetime.now() - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        session_file = memory_dir / f"{date_str}.md"
        
        if session_file.exists():
            with open(session_file) as f:
                content = f.read()
                if len(content) > max_per_session:
                    content = content[:max_per_session] + "\n[... truncated ...]"
                sessions.append(f"## Session: {date_str}\n{content}")
    
    return "\n\n".join(sessions) if sessions else None


def load_persistent_files(workspace, max_chars=2000):
    """Load Quote Hall of Fame, Curiosity Backlog, etc. for context"""
    diary_dir = workspace / "memory" / "diary"
    files = {}
    
    persistent_files = [
        ("quotes", "quotes.md"),
        ("curiosity", "curiosity.md"),
        ("decisions", "decisions.md"),
        ("relationship", "relationship.md")
    ]
    
    for key, filename in persistent_files:
        filepath = diary_dir / filename
        if filepath.exists():
            with open(filepath) as f:
                content = f.read()
                if len(content) > max_chars:
                    content = content[:max_chars] + "\n[... truncated ...]"
                files[key] = content
    
    return files


def collect_context(date_str, workspace, config):
    """Collect all context for diary generation"""
    today_log = load_session_log(date_str, workspace)
    recent_sessions = load_recent_sessions(workspace, days=2)
    persistent = load_persistent_files(workspace)
    
    # Build context output
    output_parts = [f"# Context for Diary Entry: {date_str}\n"]
    
    output_parts.append("## Configuration")
    output_parts.append(f"Privacy Level: {config.get('privacy_level', 'private')}")
    output_parts.append(f"Template: {config.get('template', 'daily')}")
    output_parts.append("")
    
    if today_log:
        output_parts.append(f"## Today's Session Log ({date_str})")
        output_parts.append(today_log)
        output_parts.append("")
    
    if recent_sessions:
        output_parts.append("## Recent Session Context")
        output_parts.append(recent_sessions)
        output_parts.append("")
    
    if persistent.get("quotes"):
        output_parts.append("## Quote Hall of Fame (Existing)")
        output_parts.append(persistent["quotes"])
        output_parts.append("")
    
    if persistent.get("curiosity"):
        output_parts.append("## Curiosity Backlog (Existing)")
        output_parts.append(persistent["curiosity"])
        output_parts.append("")
    
    if persistent.get("decisions"):
        output_parts.append("## Decision Log (Existing)")
        output_parts.append(persistent["decisions"])
        output_parts.append("")
    
    if persistent.get("relationship"):
        output_parts.append("## Relationship Notes (Existing)")
        output_parts.append(persistent["relationship"])
        output_parts.append("")
    
    return "\n".join(output_parts)


def main():
    parser = argparse.ArgumentParser(description="Collect context for diary generation")
    parser.add_argument("--today", action="store_true", help="Collect for today")
    parser.add_argument("--yesterday", action="store_true", help="Collect for yesterday")
    parser.add_argument("--date", help="Collect for specific date (YYYY-MM-DD)")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    
    args = parser.parse_args()
    
    config = load_config()
    workspace = get_workspace_root()
    
    # Determine date
    if args.today:
        date_str = datetime.now().strftime("%Y-%m-%d")
    elif args.yesterday:
        date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    elif args.date:
        date_str = args.date
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    context = collect_context(date_str, workspace, config)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(context)
        print(f"Context written to {args.output}", file=sys.stderr)
    else:
        print(context)


if __name__ == "__main__":
    import sys
    main()
