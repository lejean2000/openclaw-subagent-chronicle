#!/usr/bin/env python3
"""
AI Diary Entry Generator

Generates diary entries from session logs or interactive prompts.
"""

import argparse
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_FILE = SKILL_DIR / "config.json"
DEFAULT_DIARY_PATH = "memory/diary/"
TEMPLATE_PATH = SKILL_DIR / "templates" / "daily.md"

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
    # Try common locations
    candidates = [
        Path.cwd(),
        Path.home() / "clawd",
        Path("/root/clawd"),
    ]
    for path in candidates:
        if (path / "memory").exists():
            return path
    return Path.cwd()

def get_diary_path(config):
    """Get full path to diary directory"""
    workspace = get_workspace_root()
    diary_path = workspace / config.get("diary_path", DEFAULT_DIARY_PATH)
    diary_path.mkdir(parents=True, exist_ok=True)
    return diary_path

def load_session_log(date_str, workspace):
    """Load session log for a specific date"""
    memory_dir = workspace / "memory"
    session_file = memory_dir / f"{date_str}.md"
    
    if session_file.exists():
        with open(session_file) as f:
            return f.read()
    return None

def extract_topics(content):
    """Extract project/topic mentions from content"""
    topics = []
    # Look for headers
    headers = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
    for header in headers:
        # Clean up header
        clean = re.sub(r'[^\w\s-]', '', header).strip()
        if clean and len(clean) > 2:
            topics.append(clean)
    return list(set(topics))[:10]

def detect_sentiment(content):
    """Simple sentiment detection"""
    positive = ['success', 'fixed', 'shipped', 'working', 'great', 'nice', '✅', '🎉', 'LIVE']
    negative = ['bug', 'error', 'failed', 'broken', 'issue', '❌', 'problem', 'frustrated']
    
    content_lower = content.lower()
    pos_count = sum(1 for word in positive if word.lower() in content_lower)
    neg_count = sum(1 for word in negative if word.lower() in content_lower)
    
    if pos_count > neg_count * 2:
        return "energized"
    elif neg_count > pos_count * 2:
        return "frustrated"
    elif pos_count > neg_count:
        return "satisfied"
    elif neg_count > pos_count:
        return "challenged"
    return "focused"

def generate_from_session(date_str, workspace):
    """Generate diary entry from session log"""
    content = load_session_log(date_str, workspace)
    
    if not content:
        print(f"No session log found for {date_str}")
        return None
    
    topics = extract_topics(content)
    sentiment = detect_sentiment(content)
    
    # Build basic entry structure
    entry = {
        "date": date_str,
        "title": "",
        "summary": "",
        "projects": "\n".join(f"- {t}" for t in topics) if topics else "- (review session log)",
        "wins": "- ",
        "frustrations": "- ",
        "learnings": "- ",
        "emotional_state": sentiment.capitalize(),
        "interactions": "- ",
        "quotes": "",      # Optional: Quote Hall of Fame
        "curiosity": "",   # Optional: Curiosity Backlog
        "decisions": "",   # Optional: Decision Archaeology
        "relationship": "", # Optional: Relationship Evolution
        "tomorrow": "- "
    }
    
    # Try to generate a title
    if topics:
        entry["title"] = topics[0] + " Day"
    else:
        weekday = datetime.strptime(date_str, "%Y-%m-%d").strftime("%A")
        entry["title"] = f"{weekday}"
    
    return entry

def load_template():
    """Load the daily template"""
    if TEMPLATE_PATH.exists():
        with open(TEMPLATE_PATH) as f:
            return f.read()
    # Fallback template
    return """# {{date}} — {{title}}

## Summary
{{summary}}

## Projects Worked On
{{projects}}

## Wins 🎉
{{wins}}

## Frustrations 😤
{{frustrations}}

## Learnings 📚
{{learnings}}

## Emotional State
{{emotional_state}}

## Notable Interactions
{{interactions}}

## Tomorrow's Focus
{{tomorrow}}
"""

def render_template(template, entry):
    """Render template with entry data, handling conditionals"""
    result = template
    
    # Handle {{#if key}}...{{/if}} conditionals
    conditional_pattern = r'\{\{#if\s+(\w+)\}\}(.*?)\{\{/if\}\}'
    
    def replace_conditional(match):
        key = match.group(1)
        content = match.group(2)
        value = entry.get(key, "")
        # Include content only if value is non-empty
        if value and str(value).strip():
            # Replace the placeholder within the conditional content
            return content.replace("{{" + key + "}}", str(value))
        return ""  # Remove entire block if empty
    
    result = re.sub(conditional_pattern, replace_conditional, result, flags=re.DOTALL)
    
    # Clean up multiple blank lines
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    # Handle regular {{key}} placeholders
    for key, value in entry.items():
        placeholder = "{{" + key + "}}"
        result = result.replace(placeholder, str(value))
    
    return result

def interactive_mode(date_str):
    """Generate entry interactively"""
    print(f"\n📓 AI Diary Entry for {date_str}\n")
    print("Answer each prompt. Press Enter to skip.\n")
    
    entry = {"date": date_str}
    
    prompts = [
        ("title", "Day title (e.g., 'Feature Launch Day'): "),
        ("summary", "1-2 sentence summary of the day: "),
        ("projects", "Projects worked on (one per line, blank to finish):\n> "),
        ("wins", "Wins today (one per line, blank to finish):\n> "),
        ("frustrations", "Frustrations (one per line, blank to finish):\n> "),
        ("learnings", "What did you learn? (one per line, blank to finish):\n> "),
        ("emotional_state", "How did the day feel? "),
        ("interactions", "Notable interactions with your human: "),
        ("tomorrow", "Tomorrow's focus: ")
    ]
    
    for key, prompt in prompts:
        if key in ["projects", "wins", "frustrations", "learnings"]:
            # Multi-line input
            lines = []
            print(prompt, end="")
            while True:
                line = input()
                if not line:
                    break
                lines.append(f"- {line}")
                print("> ", end="")
            entry[key] = "\n".join(lines) if lines else "- "
        else:
            entry[key] = input(prompt) or ""
    
    return entry

def save_entry(entry, diary_path, dry_run=False):
    """Save entry to diary"""
    template = load_template()
    content = render_template(template, entry)
    
    output_file = diary_path / f"{entry['date']}.md"
    
    if dry_run:
        print("\n--- DRY RUN: Would save to", output_file)
        print("-" * 50)
        print(content)
        print("-" * 50)
        return None
    
    with open(output_file, 'w') as f:
        f.write(content)
    
    print(f"✓ Saved diary entry to {output_file}")
    return output_file

def main():
    parser = argparse.ArgumentParser(description="Generate AI Diary entries")
    parser.add_argument("--today", action="store_true", help="Generate for today")
    parser.add_argument("--date", help="Generate for specific date (YYYY-MM-DD)")
    parser.add_argument("--since", help="Start date for range")
    parser.add_argument("--until", help="End date for range")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    config = load_config()
    workspace = get_workspace_root()
    diary_path = get_diary_path(config)
    
    if args.verbose:
        print(f"Workspace: {workspace}")
        print(f"Diary path: {diary_path}")
    
    # Determine date
    if args.today:
        date_str = datetime.now().strftime("%Y-%m-%d")
    elif args.date:
        date_str = args.date
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Generate entry
    if args.interactive:
        entry = interactive_mode(date_str)
    else:
        entry = generate_from_session(date_str, workspace)
        if not entry:
            print("Falling back to interactive mode...")
            entry = interactive_mode(date_str)
    
    if entry:
        save_entry(entry, diary_path, dry_run=args.dry_run)
    else:
        print("No entry generated.")

if __name__ == "__main__":
    main()
