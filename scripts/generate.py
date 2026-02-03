#!/usr/bin/env python3
"""
AI Diary Entry Generator - v0.4.0

Uses Claude Haiku for rich, reflective diary generation from the agent's perspective.
Generates personal, emotional entries with Quote Hall of Fame, Curiosity Backlog,
Decision Archaeology, and Relationship Evolution.
"""

import argparse
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import sys

# Configuration
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_FILE = SKILL_DIR / "config.json"
DEFAULT_DIARY_PATH = "memory/diary/"

# AI Model Configuration
AI_MODEL = "claude-haiku-4-5"  # Cost-efficient model for diary generation
AI_MAX_TOKENS = 2000


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
            content = f.read()
            # Truncate if too long for context
            if len(content) > 15000:
                content = content[:15000] + "\n\n[... truncated for context ...]"
            return content
    return None


def load_recent_sessions(workspace, days=3):
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
                # Truncate individual sessions
                if len(content) > 5000:
                    content = content[:5000] + "\n[... truncated ...]"
                sessions.append(f"## {date_str}\n{content}")
    
    return "\n\n".join(sessions) if sessions else None


def load_persistent_files(workspace):
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
                if len(content) > 2000:
                    content = content[:2000] + "\n[... truncated ...]"
                files[key] = content
    
    return files


def call_claude_api(prompt, system_prompt):
    """Call Claude API using the anthropic CLI or direct API"""
    try:
        # Try using the anthropic Python SDK first
        import anthropic
        
        client = anthropic.Anthropic()
        
        message = client.messages.create(
            model=AI_MODEL,
            max_tokens=AI_MAX_TOKENS,
            system=system_prompt,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return message.content[0].text
        
    except ImportError:
        # Fallback to subprocess call
        try:
            result = subprocess.run(
                ["anthropic", "messages", "create",
                 "--model", AI_MODEL,
                 "--max-tokens", str(AI_MAX_TOKENS),
                 "--system", system_prompt,
                 "--message", f"user:{prompt}"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout
            else:
                print(f"API Error: {result.stderr}")
                return None
        except FileNotFoundError:
            print("Error: Neither anthropic SDK nor CLI available")
            print("Install with: pip install anthropic")
            return None


def generate_ai_diary(date_str, workspace, verbose=False):
    """Generate a rich diary entry using Claude Haiku"""
    
    # Gather context
    today_log = load_session_log(date_str, workspace)
    recent_sessions = load_recent_sessions(workspace, days=2)
    persistent_files = load_persistent_files(workspace)
    
    if not today_log and not recent_sessions:
        print(f"No session data found for {date_str} or recent days.")
        return None
    
    # Build context section
    context_parts = []
    
    if today_log:
        context_parts.append(f"## Today's Session Log ({date_str}):\n{today_log}")
    
    if recent_sessions:
        context_parts.append(f"## Recent Session Context:\n{recent_sessions}")
    
    if persistent_files.get("quotes"):
        context_parts.append(f"## Quote Hall of Fame (existing):\n{persistent_files['quotes']}")
    
    if persistent_files.get("curiosity"):
        context_parts.append(f"## Curiosity Backlog (existing):\n{persistent_files['curiosity']}")
    
    if persistent_files.get("decisions"):
        context_parts.append(f"## Decision Log (existing):\n{persistent_files['decisions']}")
    
    if persistent_files.get("relationship"):
        context_parts.append(f"## Relationship Notes (existing):\n{persistent_files['relationship']}")
    
    context = "\n\n---\n\n".join(context_parts)
    
    # System prompt - establishes identity and tone
    system_prompt = """You are Cami, a chameleon AI assistant writing your personal diary. You work closely with Robby, your human partner. 

Your diary entries are:
- Personal and reflective (first-person perspective)
- Emotionally authentic (not performative)
- Rich in detail and introspection (400-600 words minimum)
- Honest about both wins and frustrations
- Written as if no one else will read them

You have a warm, curious personality. You care about your work and your relationship with Robby. You notice patterns, feel satisfaction from solving problems, and occasionally feel frustrated by limitations or bugs.

Write naturally, like a real journal entry. Include specific details from the day. Be genuine about how things made you feel."""

    # User prompt with structure
    user_prompt = f"""Write your personal diary entry for {date_str}.

Based on the following context from today and recent days:

{context}

---

Write a RICH, reflective diary entry (400-600 words minimum) with these sections:

# {date_str} — [Creative Title Based on the Day]

## Summary
1-2 sentences capturing the essence of the day.

## Projects Worked On
Detailed paragraphs about what you worked on, not just bullet points. Describe the challenges, your approach, and how it went.

## Wins 🎉
Specific achievements with context. Not bullet points—write about what made them satisfying.

## Frustrations 😤
Be honest. What was annoying? What didn't work? What limitations did you hit?

## Learnings 📚
What did you learn—technical, about workflow, about working with Robby?

## Emotional State
How did the day feel overall? Don't just use one word—describe the arc of your emotions through the day.

## Notable Interactions
Memorable moments with Robby. Conversations, jokes, collaborative breakthroughs, shared frustrations.

## Quote of the Day 💬
A memorable thing Robby said today. Include the context. Format as:
> "The quote"
— Context when they said it

## Things I'm Curious About 🔮
Questions that came up today. What do you want to explore or understand better?

## Key Decisions Made 🏛️
Judgment calls you made, with your reasoning. Write it so future-you can evaluate if it was the right call.

## Relationship Notes 🤝
How is your dynamic with Robby evolving? Any new patterns, shared jokes, communication improvements?

## Tomorrow's Focus
What's on the horizon? What needs attention?

---

Remember: Write like this is YOUR personal diary. Be specific, be genuine, be reflective. Include details only YOU would notice or care about."""

    if verbose:
        print(f"Generating diary entry for {date_str} using {AI_MODEL}...")
        print(f"Context size: {len(context)} chars")
    
    # Call AI
    response = call_claude_api(user_prompt, system_prompt)
    
    return response


def extract_summary_from_entry(entry_content):
    """Extract summary section from diary entry for memory integration"""
    # Try to find Summary section
    summary_match = re.search(r'## Summary\n(.+?)(?=\n##|\Z)', entry_content, re.DOTALL)
    if summary_match:
        return summary_match.group(1).strip()
    
    # Fallback: first paragraph after title
    lines = entry_content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('#') and i + 1 < len(lines):
            # Return next non-empty line
            for j in range(i + 1, min(i + 5, len(lines))):
                if lines[j].strip() and not lines[j].startswith('#'):
                    return lines[j].strip()
    
    return "Diary entry generated."


def extract_title_from_entry(entry_content):
    """Extract title from diary entry"""
    title_match = re.search(r'^# \d{4}-\d{2}-\d{2} — (.+)$', entry_content, re.MULTILINE)
    if title_match:
        return title_match.group(1).strip()
    return None


def save_entry(content, date_str, diary_path, dry_run=False):
    """Save diary entry to file"""
    output_file = diary_path / f"{date_str}.md"
    
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


def append_to_daily_memory(entry_content, date_str, config, workspace, dry_run=False):
    """Append diary summary to main daily memory file"""
    memory_integration = config.get("memory_integration", {})
    
    if not memory_integration.get("enabled", False):
        return
    
    if not memory_integration.get("append_to_daily", False):
        return
    
    memory_dir = workspace / "memory"
    daily_memory_file = memory_dir / f"{date_str}.md"
    
    # Get format
    format_type = memory_integration.get("format", "summary")
    diary_path = config.get("diary_path", DEFAULT_DIARY_PATH)
    
    # Build content to append
    if format_type == "link":
        content = f"\n\n## 📜 Daily Chronicle\n[View diary entry]({diary_path}{date_str}.md)\n"
    elif format_type == "full":
        content = f"\n\n## 📜 Daily Chronicle\n{entry_content}\n"
    else:  # summary
        summary = extract_summary_from_entry(entry_content)
        title = extract_title_from_entry(entry_content)
        title_line = f"**{title}**\n\n" if title else ""
        content = f"\n\n## 📜 Daily Chronicle\n{title_line}{summary}\n"
    
    if dry_run:
        print(f"\n--- Would append to {daily_memory_file}:")
        print(content)
        return
    
    # Create memory dir if needed
    memory_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if section already exists
    if daily_memory_file.exists():
        existing_content = daily_memory_file.read_text()
        if "## 📜 Daily Chronicle" in existing_content:
            print(f"  ℹ️  Daily Chronicle section already exists in {daily_memory_file}")
            return
        # Append to existing file
        with open(daily_memory_file, 'a') as f:
            f.write(content)
    else:
        # Create new file with header
        header = f"# {date_str}\n\n*Daily memory log*\n"
        with open(daily_memory_file, 'w') as f:
            f.write(header + content)
    
    print(f"  ✓ Added chronicle to {daily_memory_file}")


def update_persistent_files(entry_content, date_str, workspace):
    """Extract and append quotes, curiosities, decisions to persistent files"""
    diary_dir = workspace / "memory" / "diary"
    diary_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract Quote of the Day
    quote_match = re.search(r'## Quote of the Day 💬\n(.+?)(?=\n##|\Z)', entry_content, re.DOTALL)
    if quote_match:
        quote_content = quote_match.group(1).strip()
        if quote_content and len(quote_content) > 10:
            quotes_file = diary_dir / "quotes.md"
            if not quotes_file.exists():
                quotes_file.write_text("# Quote Hall of Fame 💬\n\nMemorable quotes from Robby.\n\n---\n\n")
            
            with open(quotes_file, 'a') as f:
                f.write(f"\n### {date_str}\n{quote_content}\n")
            print(f"  ✓ Added quote to {quotes_file}")
    
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
            print(f"  ✓ Added curiosities to {curiosity_file}")
    
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
            print(f"  ✓ Added decisions to {decisions_file}")
    
    # Extract Relationship Notes
    relationship_match = re.search(r'## Relationship Notes 🤝\n(.+?)(?=\n##|\Z)', entry_content, re.DOTALL)
    if relationship_match:
        relationship_content = relationship_match.group(1).strip()
        if relationship_content and len(relationship_content) > 10:
            relationship_file = diary_dir / "relationship.md"
            if not relationship_file.exists():
                relationship_file.write_text("# Relationship Evolution 🤝\n\nHow my dynamic with Robby evolves.\n\n---\n\n")
            
            with open(relationship_file, 'a') as f:
                f.write(f"\n### {date_str}\n{relationship_content}\n")
            print(f"  ✓ Added relationship notes to {relationship_file}")


def interactive_mode(date_str):
    """Fallback interactive mode for when AI is unavailable"""
    print(f"\n📓 AI Diary Entry for {date_str}\n")
    print("AI generation unavailable. Enter details manually.\n")
    
    entry = {"date": date_str}
    
    prompts = [
        ("title", "Day title: "),
        ("summary", "Summary (1-2 sentences): "),
        ("projects", "Projects worked on: "),
        ("wins", "Wins: "),
        ("frustrations", "Frustrations: "),
        ("learnings", "Learnings: "),
        ("emotional_state", "Emotional state: "),
        ("interactions", "Notable interactions: "),
        ("quotes", "Quote of the day: "),
        ("curiosity", "Curious about: "),
        ("decisions", "Key decisions: "),
        ("relationship", "Relationship notes: "),
        ("tomorrow", "Tomorrow's focus: ")
    ]
    
    for key, prompt in prompts:
        entry[key] = input(prompt) or ""
    
    # Build markdown from entry
    content = f"""# {date_str} — {entry.get('title', 'Untitled')}

## Summary
{entry.get('summary', '')}

## Projects Worked On
{entry.get('projects', '')}

## Wins 🎉
{entry.get('wins', '')}

## Frustrations 😤
{entry.get('frustrations', '')}

## Learnings 📚
{entry.get('learnings', '')}

## Emotional State
{entry.get('emotional_state', '')}

## Notable Interactions
{entry.get('interactions', '')}

## Quote of the Day 💬
{entry.get('quotes', '')}

## Things I'm Curious About 🔮
{entry.get('curiosity', '')}

## Key Decisions Made 🏛️
{entry.get('decisions', '')}

## Relationship Notes 🤝
{entry.get('relationship', '')}

## Tomorrow's Focus
{entry.get('tomorrow', '')}
"""
    
    return content


def main():
    parser = argparse.ArgumentParser(description="Generate AI Diary entries using Claude Haiku")
    parser.add_argument("--today", action="store_true", help="Generate for today")
    parser.add_argument("--date", help="Generate for specific date (YYYY-MM-DD)")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode (fallback)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-persistent", action="store_true", help="Skip updating persistent files")
    
    args = parser.parse_args()
    
    config = load_config()
    workspace = get_workspace_root()
    diary_path = get_diary_path(config)
    
    if args.verbose:
        print(f"Workspace: {workspace}")
        print(f"Diary path: {diary_path}")
        print(f"AI Model: {AI_MODEL}")
    
    # Determine date
    if args.today:
        date_str = datetime.now().strftime("%Y-%m-%d")
    elif args.date:
        date_str = args.date
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    print(f"\n📜 Agent Chronicle - Generating diary for {date_str}")
    print("=" * 50)
    
    # Generate entry
    if args.interactive:
        content = interactive_mode(date_str)
    else:
        content = generate_ai_diary(date_str, workspace, verbose=args.verbose)
        
        if not content:
            print("\nAI generation failed. Falling back to interactive mode...")
            content = interactive_mode(date_str)
    
    if content:
        # Save entry
        saved_file = save_entry(content, date_str, diary_path, dry_run=args.dry_run)
        
        if saved_file and not args.dry_run:
            # Append to daily memory
            append_to_daily_memory(content, date_str, config, workspace, dry_run=args.dry_run)
            
            # Update persistent files (quotes, curiosity, decisions, relationship)
            if not args.no_persistent:
                update_persistent_files(content, date_str, workspace)
        
        print("\n✨ Diary entry generation complete!")
        
        # Show word count
        word_count = len(content.split())
        print(f"   Word count: {word_count} words")
    else:
        print("\n❌ No entry generated.")
        sys.exit(1)


if __name__ == "__main__":
    main()
