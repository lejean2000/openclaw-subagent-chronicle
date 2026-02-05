#!/usr/bin/env python3
"""
Subagent Chronicle - Context Collector v1.0.1

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


def get_agents_dir(workspace):
    """Find the agents directory containing session logs"""
    # Try common locations
    candidates = [
        workspace / ".openclaw" / "agents" / "main" / "sessions",
        workspace / "agents" / "main" / "sessions",
        Path.home() / ".openclaw" / "agents" / "main" / "sessions",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def get_diary_path(config, workspace):
    """Get full path to diary directory"""
    return workspace / config.get("diary_path", DEFAULT_DIARY_PATH)


def parse_jsonl_session(session_file, max_chars=15000):
    """Parse a JSONL session file and extract human-readable content"""
    content_parts = []
    
    try:
        with open(session_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    
                    # Handle different entry types
                    entry_type = entry.get("type")
                    
                    if entry_type == "message":
                        msg = entry.get("message", {})
                        role = msg.get("role", "")
                        content = msg.get("content", "")
                        
                        # Extract user messages
                        if role == "user":
                            if isinstance(content, list):
                                for item in content:
                                    if isinstance(item, dict) and item.get("type") == "text":
                                        text = item.get("text", "")
                                        # Skip system/greeting messages
                                        if not text.startswith("A new session was started"):
                                            content_parts.append(f"User: {text}")
                            elif isinstance(content, str):
                                if not content.startswith("A new session was started"):
                                    content_parts.append(f"User: {content}")
                        
                        # Extract assistant messages
                        elif role == "assistant":
                            if isinstance(content, list):
                                for item in content:
                                    if isinstance(item, dict) and item.get("type") == "text":
                                        content_parts.append(f"Assistant: {item.get('text', '')}")
                            elif isinstance(content, str):
                                content_parts.append(f"Assistant: {content}")
                            
                            # Handle tool calls
                            if "tool_calls" in msg:
                                for tc in msg.get("tool_calls", []):
                                    fn = tc.get("function", {})
                                    content_parts.append(f"[Tool: {fn.get('name', 'unknown')}] {fn.get('arguments', '')}")
                    
                    elif entry_type == "tool_result":
                        result = entry.get("result", {})
                        result_text = result.get("text", "") if isinstance(result, dict) else str(result)
                        if result_text:
                            content_parts.append(f"[Tool Result]: {result_text[:500]}")
                    
                    elif entry_type == "tool_error":
                        error = entry.get("error", "")
                        if error:
                            content_parts.append(f"[Tool Error]: {error}")
                            
                except json.JSONDecodeError:
                    continue
                
                # Check if we've hit the limit
                current_len = sum(len(p) for p in content_parts)
                if current_len > max_chars:
                    content_parts.append("\n[... truncated for context ...]")
                    break
    except Exception as e:
        return f"[Error reading session: {e}]"
    
    result = "\n\n".join(content_parts)
    return result if result else "[No content extracted]"


def load_session_log(date_str, workspace, max_chars=15000):
    """Load session logs for a specific date from agents/main/sessions"""
    agents_dir = get_agents_dir(workspace)
    
    if not agents_dir:
        return None
    
    # Parse target date
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    
    # Find all session files modified on the target date
    sessions = []
    for session_file in agents_dir.glob("*.jsonl"):
        # Skip lock files
        if session_file.suffix == ".lock" or str(session_file).endswith(".lock"):
            continue
        
        # Get file modification time
        mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
        if mtime.date() == target_date:
            content = parse_jsonl_session(session_file, max_chars=max_chars // 3)
            if content:
                sessions.append(f"### Session: {session_file.stem}\n{content}")
    
    if not sessions:
        return None
    
    return "\n\n".join(sessions)


def load_recent_sessions(workspace, days=3, max_per_session=5000):
    """Load recent session logs for context"""
    agents_dir = get_agents_dir(workspace)
    
    if not agents_dir:
        return None
    
    sessions = []
    cutoff = datetime.now() - timedelta(days=days)
    
    for session_file in agents_dir.glob("*.jsonl"):
        if str(session_file).endswith(".lock"):
            continue
        
        mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
        if mtime >= cutoff:
            content = parse_jsonl_session(session_file, max_chars=max_per_session)
            if content:
                date_str = mtime.strftime("%Y-%m-%d")
                sessions.append(f"## Session: {session_file.stem} ({date_str})\n{content}")
    
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
        output_parts.append(f"## Today's Sessions ({date_str})")
        output_parts.append(today_log)
        output_parts.append("")
    else:
        output_parts.append(f"## Today's Sessions ({date_str})")
        output_parts.append("*No sessions recorded for this date*")
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
